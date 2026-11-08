"""Category label standardization and near-duplicate handling (Step 4, Section 9.4)."""

from __future__ import annotations

import difflib

import pandas as pd

from ads.cleaning.log import CleaningLog
from ads.config import PipelineConfig
from ads.schemas import SemanticType

_BOOL_POS = {"yes", "y", "true", "t", "1", "1.0"}
_BOOL_NEG = {"no", "n", "false", "f", "0", "0.0"}
_BOOL_ALL = _BOOL_POS | _BOOL_NEG


def _find_fuzzy_and_abbrev_candidates(
    canonical_counts: dict[str, tuple[str, int]],
    similarity_threshold: float,
) -> list[tuple[str, str, int, int, float, str]]:
    """Find fuzzy near-duplicate pairs and single-character abbreviation pairs (e.g. 'M'/'Male').

    Returns list of:
        (winner_spelling, variant_spelling, winner_count, variant_count, similarity, kind)
    """
    items = sorted(
        canonical_counts.items(),
        key=lambda kv: (-kv[1][1], kv[0]),
    )
    candidates: list[tuple[str, str, int, int, float, str]] = []

    for i in range(len(items)):
        cf_a, (spell_a, cnt_a) = items[i]
        for j in range(i + 1, len(items)):
            cf_b, (spell_b, cnt_b) = items[j]
            # Check single-letter prefix abbreviation (e.g., 'm' vs 'male', 'f' vs 'female')
            if len(cf_b) == 1 and len(cf_a) >= 4 and cf_a.startswith(cf_b):
                candidates.append((spell_a, spell_b, cnt_a, cnt_b, 0.85, "abbreviation"))
                continue
            if len(cf_a) == 1 and len(cf_b) >= 4 and cf_b.startswith(cf_a):
                candidates.append((spell_b, spell_a, cnt_b, cnt_a, 0.85, "abbreviation"))
                continue
            # Edit-distance similarity for strings >= 4 chars
            if min(len(cf_a), len(cf_b)) >= 4:
                sim = difflib.SequenceMatcher(None, cf_a, cf_b).ratio()
                if sim >= similarity_threshold:
                    candidates.append(
                        (spell_a, spell_b, cnt_a, cnt_b, round(float(sim), 4), "fuzzy")
                    )

    return candidates


def step4_standardize_categories(
    df: pd.DataFrame,
    semantic_types: dict[str, SemanticType],
    log: CleaningLog,
    config: PipelineConfig,
) -> pd.DataFrame:
    """Step 4: Merge case/whitespace variants in categorical/binary string columns (Section 9.4)."""
    out = df.copy()
    n_rows = len(out)
    if n_rows == 0:
        return out

    sim_thresh = config.profiling.label_similarity_threshold
    auto_fuzzy = config.cleaning.auto_merge_fuzzy

    for col in out.columns:
        sem = semantic_types.get(col, SemanticType.UNKNOWN)
        if sem not in {
            SemanticType.CATEGORICAL_NOMINAL,
            SemanticType.CATEGORICAL_ORDINAL,
            SemanticType.BINARY,
        }:
            continue

        s = out[col]
        if not (pd.api.types.is_object_dtype(s) or pd.api.types.is_string_dtype(s)):
            continue

        not_na = s.notna()
        if not not_na.any():
            continue

        vals = s[not_na].astype(str)
        vc_raw = vals.value_counts()

        # 1. Group by casefold to merge case-only variants into the most frequent spelling
        cf_groups: dict[str, list[tuple[str, int]]] = {}
        for spelling, count in vc_raw.items():
            cf = str(spelling).strip().casefold()
            cf_groups.setdefault(cf, []).append((str(spelling).strip(), int(count)))

        case_mapping: dict[str, str] = {}
        canonical_counts: dict[str, tuple[str, int]] = {}
        for cf, spell_list in cf_groups.items():
            sorted_spells = sorted(spell_list, key=lambda sc: (-sc[1], sc[0]))
            winner_spelling = sorted_spells[0][0]
            total_cnt = sum(sc[1] for sc in sorted_spells)
            canonical_counts[cf] = (winner_spelling, total_cnt)
            if len(sorted_spells) > 1:
                for sp, _ in sorted_spells[1:]:
                    case_mapping[sp] = winner_spelling

        if case_mapping:
            changed_mask = not_na & out[col].astype(str).isin(case_mapping)
            n_changed = int(changed_mask.sum())
            if n_changed > 0:
                before_ex = out.loc[changed_mask, col].astype(str).head(5).tolist()
                after_ex = [case_mapping[v] for v in before_ex]
                out.loc[changed_mask, col] = out.loc[changed_mask, col].astype(str).map(
                    lambda v: case_mapping.get(v, v)
                )
                log.add(
                    step="standardize_categories",
                    column=col,
                    action="merged_case_variants",
                    n_cells_affected=n_changed,
                    n_rows_affected=n_changed,
                    rows_before=n_rows,
                    rows_after=n_rows,
                    reason=f"Merged {len(case_mapping)} case-only variant spelling(s) into dominant form.",
                    before_examples=before_ex,
                    after_examples=after_ex,
                    parameters={"mapping": case_mapping},
                    severity="info",
                )

        # 2. For BINARY columns mixing boolean encodings (e.g. Yes/No/Y/1/0 in Section 12.2):
        #    Standardize boolean aliases into the dominant positive/negative string labels
        #    (while keeping original string labels like Yes/No and never recoding Yes/No -> 1/0).
        if sem == SemanticType.BINARY:
            cur_vals = out.loc[not_na, col].astype(str)
            cur_cf_set = set(cur_vals.str.casefold().unique())
            if (
                len(cur_cf_set) > 2
                and cur_cf_set.issubset(_BOOL_ALL)
                and (cur_cf_set & _BOOL_POS)
                and (cur_cf_set & _BOOL_NEG)
            ):
                vc_cur = cur_vals.value_counts()
                pos_candidates = [
                    (str(sp), int(cnt))
                    for sp, cnt in vc_cur.items()
                    if str(sp).casefold() in _BOOL_POS
                ]
                neg_candidates = [
                    (str(sp), int(cnt))
                    for sp, cnt in vc_cur.items()
                    if str(sp).casefold() in _BOOL_NEG
                ]
                pos_winner = sorted(pos_candidates, key=lambda x: (-x[1], x[0]))[0][0]
                neg_winner = sorted(neg_candidates, key=lambda x: (-x[1], x[0]))[0][0]

                bool_map: dict[str, str] = {}
                for sp, _ in pos_candidates:
                    if sp != pos_winner:
                        bool_map[sp] = pos_winner
                for sp, _ in neg_candidates:
                    if sp != neg_winner:
                        bool_map[sp] = neg_winner

                if bool_map:
                    b_mask = not_na & out[col].astype(str).isin(bool_map)
                    n_b_changed = int(b_mask.sum())
                    if n_b_changed > 0:
                        b_before = out.loc[b_mask, col].astype(str).head(5).tolist()
                        b_after = [bool_map[v] for v in b_before]
                        out.loc[b_mask, col] = out.loc[b_mask, col].astype(str).map(
                            lambda v: bool_map.get(v, v)
                        )
                        log.add(
                            step="standardize_categories",
                            column=col,
                            action="standardized_binary_tokens",
                            n_cells_affected=n_b_changed,
                            n_rows_affected=n_b_changed,
                            rows_before=n_rows,
                            rows_after=n_rows,
                            reason=(
                                f"Standardized mixed boolean tokens in '{col}' into dominant labels "
                                f"({pos_winner!r} / {neg_winner!r})."
                            ),
                            before_examples=b_before,
                            after_examples=b_after,
                            parameters={"mapping": bool_map},
                            severity="warning",
                        )

        # 3. Check fuzzy near-duplicates and single-letter abbreviations (e.g., 'M'/'F' in gender)
        #    Recompute canonical_counts after case/boolean standardization
        cur_vc = out.loc[not_na, col].astype(str).value_counts()
        cur_canonical: dict[str, tuple[str, int]] = {
            str(sp).casefold(): (str(sp), int(cnt)) for sp, cnt in cur_vc.items()
        }
        fuzzy_candidates = _find_fuzzy_and_abbrev_candidates(cur_canonical, sim_thresh)
        if fuzzy_candidates:
            if auto_fuzzy:
                fuzzy_map = {var_sp: win_sp for win_sp, var_sp, _, _, _, _ in fuzzy_candidates}
                f_mask = not_na & out[col].astype(str).isin(fuzzy_map)
                n_f_changed = int(f_mask.sum())
                if n_f_changed > 0:
                    f_before = out.loc[f_mask, col].astype(str).head(5).tolist()
                    f_after = [fuzzy_map[v] for v in f_before]
                    out.loc[f_mask, col] = out.loc[f_mask, col].astype(str).map(
                        lambda v: fuzzy_map.get(v, v)
                    )
                    log.add(
                        step="standardize_categories",
                        column=col,
                        action="merged_fuzzy_variants",
                        n_cells_affected=n_f_changed,
                        n_rows_affected=n_f_changed,
                        rows_before=n_rows,
                        rows_after=n_rows,
                        reason=f"Auto-merged {len(fuzzy_map)} fuzzy/abbreviation variant(s) (auto_merge_fuzzy=True).",
                        before_examples=f_before,
                        after_examples=f_after,
                        parameters={"mapping": fuzzy_map},
                        severity="warning",
                    )
            else:
                cand_desc = [
                    f"{var_sp!r} ({var_cnt}) -> {win_sp!r} ({win_cnt}) [{kind}, sim={sim:.2f}]"
                    for win_sp, var_sp, win_cnt, var_cnt, sim, kind in fuzzy_candidates
                ]
                log.add(
                    step="standardize_categories",
                    column=col,
                    action="flagged_fuzzy_variants",
                    n_cells_affected=0,
                    n_rows_affected=sum(c[3] for c in fuzzy_candidates),
                    rows_before=n_rows,
                    rows_after=n_rows,
                    reason=(
                        f"Flagged near-duplicate/abbreviation label candidate(s) for human review "
                        f"(not auto-merged): {'; '.join(cand_desc[:4])}."
                    ),
                    before_examples=[c[1] for c in fuzzy_candidates[:5]],
                    after_examples=[c[1] for c in fuzzy_candidates[:5]],
                    parameters={
                        "candidates": [
                            {
                                "target": c[0],
                                "variant": c[1],
                                "target_count": c[2],
                                "variant_count": c[3],
                                "similarity": c[4],
                                "kind": c[5],
                            }
                            for c in fuzzy_candidates
                        ]
                    },
                    severity="warning",
                )

    return out

