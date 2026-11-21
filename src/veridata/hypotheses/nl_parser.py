"""Natural-language to structured Hypothesis parser with offline fuzzy fallback (Phase 2 Section 7)."""

from __future__ import annotations

import difflib
import logging
import re
from pathlib import Path
from typing import Literal

import pandas as pd

from veridata.agent.llm import LLMClient
from veridata.config import PipelineConfig
from veridata.contracts.hypothesis import (
    Direction,
    FeasibilityReport,
    Hypothesis,
    NLHypothesisParse,
    NLParseOutcome,
    RelationshipType,
)
from veridata.errors import LLMError, LLMUnavailable
from veridata.hypotheses.dedupe import make_hypothesis_id
from veridata.hypotheses.enumerate import filter_eligible_columns, map_pair_to_relationship
from veridata.hypotheses.feasibility import assess_feasibility
from veridata.hypotheses.safe_profile import build_safe_profile, format_safe_profile_block
from veridata.schemas import ColumnSchemaEntry, DataProfile, SemanticType

logger = logging.getLogger("veridata.hypotheses.nl_parser")

NL_PROMPT_VERSION = "nl_parser_v1"
DEFAULT_NL_PROMPT_PATH = (
    Path(__file__).resolve().parents[3] / "configs" / "prompts" / f"{NL_PROMPT_VERSION}.txt"
)

_CAUSAL_REQUEST_RE = re.compile(
    r"\b(causes?|causing|caused\s+by|causal|make\s+\w+\s+(higher|lower|more|less)|"
    r"directly\s+causes?|prove\s+that|proof\s+that)\b",
    re.IGNORECASE,
)
_ML_OR_TS_REQUEST_RE = re.compile(
    r"\b(predict|forecast|train\s+a\s+model|machine\s+learning|classify|"
    r"random\s+forest|neural\s+network|time\s+series|over\s+time|monthly\s+trend|"
    r"seasonal|seasonality)\b",
    re.IGNORECASE,
)

_GREATER_RE = re.compile(
    r"\b(higher|more|greater|larger|increase|increases|positively|bigger|above|longer)\b",
    re.IGNORECASE,
)
_LESS_RE = re.compile(
    r"\b(lower|less|fewer|smaller|decrease|decreases|negatively|below|shorter|drop)\b",
    re.IGNORECASE,
)
_GENERIC_LEVELS: frozenset[str] = frozenset(
    {"yes", "no", "y", "n", "true", "false", "0", "1", "other", "none", "unknown", "missing"}
)
_STOPWORDS: frozenset[str] = frozenset(
    {
        "a",
        "an",
        "the",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "do",
        "does",
        "did",
        "have",
        "has",
        "had",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "by",
        "with",
        "from",
        "and",
        "or",
        "between",
        "among",
        "across",
        "whether",
        "if",
        "test",
        "check",
        "compare",
        "show",
        "find",
        "see",
        "there",
        "their",
        "they",
        "than",
        "more",
        "less",
        "higher",
        "lower",
        "greater",
        "smaller",
        "associated",
        "association",
        "related",
        "relationship",
        "correlated",
        "correlation",
        "differ",
        "different",
        "difference",
        "depend",
        "depends",
        "dependent",
        "pay",
        "get",
        "score",
        "scores",
        "rate",
        "rates",
        "level",
        "levels",
        "type",
        "types",
        "people",
        "customers",
        "patients",
        "students",
        "clients",
        "who",
        "what",
        "how",
        "many",
        "much",
        "significantly",
        "statistically",
    }
)


def _split_identifier(name: str) -> list[str]:
    """Split camelCase, PascalCase, snake_case, and dotted column names into lowercase tokens."""
    step1 = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", name)
    step2 = re.sub(r"[^a-zA-Z0-9]+", " ", step1)
    return [t.lower() for t in step2.split() if t]


def _light_stem(token: str) -> str:
    """Minimal suffix stripping so plurals/derivatives match column names (smokers -> smoker)."""
    t = token.lower()
    if len(t) > 5 and t.endswith("ers"):
        return t[:-2]
    if len(t) > 4 and t.endswith("ies"):
        return t[:-3] + "y"
    if len(t) > 4 and t.endswith("es") and not t.endswith(("ses", "ges", "ces")):
        return t[:-2]
    if len(t) > 3 and t.endswith("s") and not t.endswith("ss"):
        return t[:-1]
    return t


def _tokenize_sentence(text: str) -> list[str]:
    return [t.lower() for t in re.findall(r"[A-Za-z0-9_]+", text)]


def _check_unsupported_request(text: str) -> str | None:
    if _CAUSAL_REQUEST_RE.search(text):
        return (
            "Causal questions are not supported; VeriData evaluates statistical "
            "associations only (Principle P5)."
        )
    if _ML_OR_TS_REQUEST_RE.search(text):
        return (
            "Prediction, modeling, and time-series forecasting requests are not supported "
            "as pairwise hypothesis tests."
        )
    return None


def _derive_direction(
    phrase: Literal["greater", "less", "associated", "different", "unspecified"],
    relationship: RelationshipType,
) -> Direction:
    if relationship in {RelationshipType.NUM_NUM, RelationshipType.NUM_NUM_NONLINEAR}:
        if phrase == "greater":
            return Direction.POSITIVE
        if phrase == "less":
            return Direction.NEGATIVE
        return Direction.ANY
    if relationship == RelationshipType.NUM_BINARY:
        if phrase == "greater":
            return Direction.A_GREATER
        if phrase == "less":
            return Direction.B_GREATER
        return Direction.ANY
    return Direction.ANY


def _infer_direction_phrase_from_text(
    text: str,
) -> Literal["greater", "less", "associated", "different", "unspecified"]:
    has_greater = bool(_GREATER_RE.search(text))
    has_less = bool(_LESS_RE.search(text))
    if has_greater and not has_less:
        return "greater"
    if has_less and not has_greater:
        return "less"
    if re.search(r"\b(differ|different|difference)\b", text, re.IGNORECASE):
        return "different"
    if re.search(r"\b(associated|related|correlated|correlation|relationship)\b", text, re.IGNORECASE):
        return "associated"
    return "unspecified"


def _build_user_hypothesis(
    *,
    col_a: str,
    col_b: str,
    df: pd.DataFrame,
    schema: dict[str, ColumnSchemaEntry],
    config: PipelineConfig,
    direction_phrase: Literal["greater", "less", "associated", "different", "unspecified"],
    level_of_interest: str | None = None,
    created_stage: Literal["batch", "chat"] = "chat",
) -> NLParseOutcome:
    if col_a == col_b:
        return NLParseOutcome(
            status="ambiguous",
            candidates=[col_a],
            clarification_question=(
                f"Only one distinct column ('{col_a}') was identified. "
                "Which second column should be tested with it?"
            ),
            reason="same column specified twice",
        )

    entry_a = schema[col_a]
    entry_b = schema[col_b]
    if SemanticType.DATETIME in (entry_a.semantic_type, entry_b.semantic_type):
        return NLParseOutcome(
            status="unsupported",
            reason="Datetime columns are not testable in this version.",
        )

    mapped = map_pair_to_relationship(col_a, entry_a, col_b, entry_b, config)
    if mapped is None:
        return NLParseOutcome(
            status="unsupported",
            reason=(
                f"Column pair ('{col_a}', '{col_b}') has unsupported or incompatible "
                "semantic types for pairwise testing."
            ),
        )

    oriented_a, oriented_b, rel = mapped
    direction = _derive_direction(direction_phrase, rel)
    hid = make_hypothesis_id(rel, oriented_a, oriented_b)

    rationale = (
        f"User-requested association test between {oriented_a} and {oriented_b}"
        + (f" focusing on level {level_of_interest}" if level_of_interest else "")
        + "."
    )

    placeholder = FeasibilityReport(feasible=True, reasons=[], n_pairwise_complete=0)
    hyp = Hypothesis(
        id=hid,
        column_a=oriented_a,
        column_b=oriented_b,
        relationship=rel,
        expected_direction=direction,
        source="user",
        rationale=rationale,
        feasibility=placeholder,
        created_stage=created_stage,
        status="proposed",
    )
    feas = assess_feasibility(hyp, df, schema, config)
    hyp = hyp.model_copy(
        update={
            "feasibility": feas,
            "status": "proposed" if feas.feasible else "skipped_infeasible",
        }
    )
    return NLParseOutcome(status="ok", hypothesis=hyp)


def _fuzzy_match_columns(
    text: str,
    df: pd.DataFrame,
    schema: dict[str, ColumnSchemaEntry],
    eligible_cols: list[str],
) -> tuple[list[tuple[str, float]], list[str]]:
    """Score schema columns against user text via normalized token & level matching."""
    text_lower = text.lower()
    raw_tokens = _tokenize_sentence(text)
    stemmed_tokens = [_light_stem(t) for t in raw_tokens]
    content_tokens = [t for t in raw_tokens if t not in _STOPWORDS and len(t) >= 2]
    content_stems = [_light_stem(t) for t in content_tokens]

    # Track datetime columns explicitly so mentions of date columns return unsupported
    datetime_hits: list[str] = []
    for col, entry in schema.items():
        if entry.semantic_type == SemanticType.DATETIME:
            col_words = _split_identifier(col)
            if col.lower() in text_lower or any(w in content_tokens for w in col_words if len(w) >= 4):
                datetime_hits.append(col)

    scored: dict[str, float] = {}

    for col in eligible_cols:
        best = 0.0
        col_lower = col.lower()
        col_words = _split_identifier(col)
        col_stems = [_light_stem(w) for w in col_words]
        col_phrase = " ".join(col_words)

        # 1. Exact column name or spaced phrase inside text (word boundary)
        if re.search(rf"\b{re.escape(col_lower)}\b", text_lower):
            best = max(best, 1.0)
        elif len(col_words) >= 2 and re.search(rf"\b{re.escape(col_phrase)}\b", text_lower):
            best = max(best, 0.98)
        elif len(col_words) >= 2 and all(
            any(
                ws == ts or (len(ws) >= 4 and difflib.SequenceMatcher(None, ws, ts).ratio() >= 0.85)
                for ts in stemmed_tokens
            )
            for ws in col_stems
        ):
            best = max(best, 0.95)
        else:
            # 2. Single-token / partial fuzzy match
            if len(col_words) == 1:
                w = col_words[0]
                ws = col_stems[0]
                for tok, ts in zip(content_tokens, content_stems):
                    if tok == w or ts == ws:
                        best = max(best, 0.95)
                    elif len(w) >= 4 and len(tok) >= 4:
                        ratio = difflib.SequenceMatcher(None, w, tok).ratio()
                        if ratio >= 0.80:
                            best = max(best, round(0.90 * ratio, 4))
            else:
                # Multi-word column: check how many distinctive column words appear
                matched_words = 0
                for w, ws in zip(col_words, col_stems):
                    if len(w) < 3:
                        continue
                    if any(
                        tok == w
                        or ts == ws
                        or (len(w) >= 4 and difflib.SequenceMatcher(None, w, tok).ratio() >= 0.82)
                        for tok, ts in zip(content_tokens, content_stems)
                    ):
                        matched_words += 1
                if matched_words > 0:
                    coverage = matched_words / len(col_words)
                    if coverage >= 0.5:
                        best = max(best, round(0.75 + 0.15 * coverage, 4))

        # 3. Categorical level value matching (non-generic labels only)
        entry = schema[col]
        if (
            best < 0.90
            and col in df.columns
            and entry.semantic_type
            in {
                SemanticType.BINARY,
                SemanticType.CATEGORICAL_NOMINAL,
                SemanticType.CATEGORICAL_ORDINAL,
            }
        ):
            unique_vals = [str(v).strip() for v in df[col].dropna().unique()[:25]]
            for val in unique_vals:
                val_lower = val.lower()
                if val_lower in _GENERIC_LEVELS or len(val_lower) < 3:
                    continue
                if re.search(rf"\b{re.escape(val_lower)}\b", text_lower):
                    best = max(best, 0.88)
                    break
                val_words = _split_identifier(val)
                if len(val_words) >= 2 and re.search(
                    rf"\b{re.escape(' '.join(val_words))}\b", text_lower
                ):
                    best = max(best, 0.88)
                    break

        if best >= 0.72:
            scored[col] = best

    ranked = sorted(scored.items(), key=lambda kv: (-kv[1], kv[0]))
    return ranked, sorted(datetime_hits)


def _load_nl_prompt(prompt_path: Path = DEFAULT_NL_PROMPT_PATH) -> str:
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8").strip()
    return (
        "Convert the user's question into an NLHypothesisParse JSON object using ONLY "
        "the column aliases inside <dataset_profile>...</dataset_profile>."
    )


def parse_nl_hypothesis(
    text: str,
    df: pd.DataFrame,
    schema: dict[str, ColumnSchemaEntry],
    llm: LLMClient | None,
    config: PipelineConfig,
    *,
    profile: DataProfile | None = None,
    created_stage: Literal["batch", "chat"] = "chat",
    prompt_path: Path = DEFAULT_NL_PROMPT_PATH,
) -> NLParseOutcome:
    """Convert a natural-language question into a structured, validated Hypothesis (Section 7)."""
    cleaned_text = text.strip()
    if not cleaned_text:
        return NLParseOutcome(
            status="no_columns_found",
            clarification_question="Please enter a question referencing two columns in the dataset.",
            reason="empty input",
        )

    unsupported_msg = _check_unsupported_request(cleaned_text)
    if unsupported_msg is not None:
        return NLParseOutcome(status="unsupported", reason=unsupported_msg)

    eligible_cols, _, _ = filter_eligible_columns(schema, config)

    # 1. LLM structured path (when available)
    if llm is not None:
        safe_profile, alias_to_col, _, _ = build_safe_profile(
            schema=schema,
            profile=profile,
            config=config,
            eligible_columns=eligible_cols,
        )
        system_prompt = _load_nl_prompt(prompt_path)
        user_prompt = (
            f"User question: {cleaned_text}\n\n"
            f"{format_safe_profile_block(safe_profile)}"
        )
        try:
            parsed = llm.structured(
                system=system_prompt,
                user=user_prompt,
                schema=NLHypothesisParse,
                temperature=config.llm.temperature,
                max_tokens=config.llm.max_tokens,
            )
            if parsed.status == "unsupported":
                return NLParseOutcome(
                    status="unsupported",
                    reason=parsed.unsupported_reason
                    or "This question cannot be tested as a pairwise statistical association.",
                    used_llm=True,
                )
            if parsed.status == "ambiguous":
                real_cands = [
                    alias_to_col[a] for a in parsed.candidates if a in alias_to_col
                ][:4]
                return NLParseOutcome(
                    status="ambiguous",
                    candidates=real_cands,
                    clarification_question=parsed.clarification_question
                    or "Multiple columns could match your question. Which two would you like to test?",
                    used_llm=True,
                )
            if parsed.status == "no_columns_found":
                return NLParseOutcome(
                    status="no_columns_found",
                    clarification_question=parsed.clarification_question
                    or "Could not identify two dataset columns in your question.",
                    used_llm=True,
                )

            col_a = alias_to_col.get(parsed.column_a_alias or "")
            col_b = alias_to_col.get(parsed.column_b_alias or "")
            if col_a is None or col_b is None:
                return NLParseOutcome(
                    status="no_columns_found",
                    clarification_question=(
                        "Could not map the question to two valid dataset columns. "
                        "Please specify the exact column names."
                    ),
                    reason="LLM returned unknown column alias",
                    used_llm=True,
                )
            outcome = _build_user_hypothesis(
                col_a=col_a,
                col_b=col_b,
                df=df,
                schema=schema,
                config=config,
                direction_phrase=parsed.expected_direction_phrase,
                level_of_interest=parsed.level_of_interest,
                created_stage=created_stage,
            )
            return outcome.model_copy(update={"used_llm": True})
        except (LLMUnavailable, LLMError) as exc:
            logger.info("NL parser LLM unavailable/failed (%s); using offline fuzzy fallback.", exc)

    # 2. Offline deterministic fuzzy fallback
    ranked_matches, datetime_hits = _fuzzy_match_columns(cleaned_text, df, schema, eligible_cols)

    if datetime_hits and len(ranked_matches) < 2:
        return NLParseOutcome(
            status="unsupported",
            reason=f"Datetime column(s) ({', '.join(datetime_hits)}) are not testable in this version.",
            used_llm=False,
        )

    if len(ranked_matches) < 2:
        cands = [c for c, _ in ranked_matches]
        return NLParseOutcome(
            status="no_columns_found",
            candidates=cands,
            clarification_question=(
                "Could not identify two testable columns from your question. "
                + (f"Matched so far: {', '.join(cands)}. " if cands else "")
                + f"Available columns include: {', '.join(eligible_cols[:8])}."
            ),
            used_llm=False,
        )

    # Ambiguity check: if 3+ columns match with near-tied scores (within 0.05 of the 2nd match)
    top_col, top_score = ranked_matches[0]
    sec_col, sec_score = ranked_matches[1]
    if len(ranked_matches) >= 3 and (sec_score - ranked_matches[2][1]) < 0.05:
        cands = [c for c, _ in ranked_matches[:4]]
        return NLParseOutcome(
            status="ambiguous",
            candidates=cands,
            clarification_question=(
                f"Your question matches multiple columns ({', '.join(cands)}). "
                "Which two columns would you like to test?"
            ),
            used_llm=False,
        )

    direction_phrase = _infer_direction_phrase_from_text(cleaned_text)
    outcome = _build_user_hypothesis(
        col_a=top_col,
        col_b=sec_col,
        df=df,
        schema=schema,
        config=config,
        direction_phrase=direction_phrase,
        created_stage=created_stage,
    )
    return outcome.model_copy(update={"used_llm": False})

