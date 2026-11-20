# PHASE 2 — Intelligent Hypothesis Generation

> Prerequisite reading: `00_MASTER_PLAN.md` (principles P1-P10, contracts in Section 5, config in Section 6).
> Inputs: Phase 1 artifacts (`column_schema.json`, `profile.json`, cleaned CSV).
> Output: a validated, deduplicated, feasibility-annotated, ranked list of `Hypothesis` objects plus a **family manifest** that fixes how many tests will be attempted.

---

## 1. Goal and scope

Turn a profiled, cleaned dataset into a list of **testable statistical hypotheses** in a fixed structured form, in three ways:

1. **Systematic enumeration**: all sensible column pairs given their types (the honest, exhaustive baseline).
2. **LLM-assisted proposals and prioritization**: domain-aware hypotheses and ordering, constrained to the schema and validated against real columns.
3. **Natural-language → structured conversion**: a user's sentence ("do smokers pay more?") becomes a `Hypothesis`. Reused by the chat mode in Phase 6.

### In scope
Enumeration, type-compatibility rules, feasibility screening, deduplication, ranking (ordering only), LLM proposer, NL parser, family manifest, CLI, tests, a small gold set for the NL parser.

### Out of scope
Running any test or computing any p-value (Phase 3). Any use of *bivariate* data-derived statistics in selection (see Section 2).

---

## 2. The most important design rule: no peeking (P2)

If hypotheses are selected using the data's own bivariate patterns (e.g., "test the 20 pairs with the highest correlation"), then the multiple-testing family is effectively *all* pairs, and correcting only for the 20 gives inflated false discoveries.

**Therefore:**

| Allowed inputs to enumeration / ranking / LLM prompt | Forbidden inputs |
|---|---|
| Column names, semantic types, roles, user-provided descriptions | Pairwise correlations, cross-tab associations, group-mean differences |
| Univariate stats: missingness, cardinality, level frequencies, skew, outlier rates, class balance of the target | p-values or effect sizes of any test |
| Sample size, group sizes (feasibility) | Phase 1 `insights.json` entries in the "Relationships" category (descriptive bivariate) |
| Target column choice (user-specified) | Anything derived from test results |

**EDA findings (per the original plan) may be used only for presentation order after testing, never for choosing which hypotheses enter the family.** Enforce structurally: the `hypotheses/` package must not import from `stats/` or `validation/` and must not read `insights.json` relationship entries. Add an import-lint test that fails if it does.

Corollary: **ranking never removes hypotheses.** `priority_score` only orders them (e.g., which tests to show or run first, which to narrate first). If the number of candidate hypotheses exceeds `max_tests`, pruning is allowed **only by outcome-independent criteria** (Section 6), and the pruned set is recorded in the manifest.

---

## 3. Hypothesis space definition

### 3.1 Eligible columns
From `column_schema.json`: roles `feature` and `target_candidate`; exclude `id`, `excluded` (constant, id_like, free_text, mostly-missing), datetime (not testable in this version; list in manifest as "not testable"), and Phase 1 derived columns (`__was_missing`, `__log1p`, `__z`).
Additionally exclude columns with `n_unique > max_levels_categorical` when categorical (high cardinality → unstable tests); record as excluded with reason. Optionally allow lumping rare levels into "Other" if configured (`lump_rare_levels: false` default; if true, rule: levels with < 1% of non-null rows lumped, recorded).

### 3.2 Type → relationship mapping (deterministic; LLM never chooses it)

| Column A type | Column B type | `RelationshipType` | Notes |
|---|---|---|---|
| numeric (continuous or discrete with >10 levels) | numeric | `NUM_NUM` | symmetric: one hypothesis per unordered pair |
| numeric | binary | `NUM_BINARY` | `column_a` = numeric outcome, `column_b` = grouping |
| numeric | categorical (3..max_levels) | `NUM_CATEGORICAL` | same orientation |
| binary / categorical | binary / categorical | `CAT_CAT` | unordered pair; binary×binary is a 2×2 |
| numeric_discrete with ≤ 10 levels | any | treat as **categorical** for pairing with numeric? | **DECISION:** `numeric_discrete` with ≤ 10 distinct values is treated as categorical *and also* eligible as numeric ordinal only if config `treat_small_discrete_as_numeric: true` (default false). Record choice in manifest. |
| ordinal categorical | numeric | `NUM_CATEGORICAL` default | ordinal-aware trend tests are stretch |
| datetime | any | not testable | listed in manifest |

`NUM_NUM_NONLINEAR` hypotheses are added only if `hypotheses.enable_nonlinear: true`, as a *separate* hypothesis for the same pair (and it counts in the family).

### 3.3 Exclusion of trivially related pairs (outcome-independent)
- Pairs where one column is a deterministic transform of the other **by name/provenance** (e.g., `x` and `x__log1p`).
- Pairs where both columns are one-hot expansions of the same original (if Phase 1 recorded provenance) — otherwise skip this rule.
- Do **not** exclude pairs because they "look" strongly correlated (that would be peeking). Strongly related/derived pairs are handled after testing as `TRIVIAL_RELATIONSHIP` in Phase 3.

### 3.4 Generation modes (`hypotheses.mode`)
- **`exhaustive`** (default): all eligible pairs. Family size m = number of feasible hypotheses.
- **`target_focused`**: requires `target`. Only pairs involving the target. m = (#eligible columns − 1). Use for wide data or when the user specifies an outcome. Record in manifest that non-target pairs were *not tested by design*.
- **`llm_prioritized`**: the LLM selects a subset (and an order) from the full eligible list using only allowed inputs (Section 5). Since selection is based on allowed inputs only, selected-subset BH is valid; the manifest records the **total eligible count and the selected count** so the report can say "tested 60 of 780 eligible pairs, chosen before looking at results".
- Mode selection is a user setting; the default UI path = `exhaustive` if m ≤ `max_tests`, else `target_focused` if target given, else outcome-independent pruning (Section 6).

---

## 4. Feasibility screening (`feasibility.py`)

`assess_feasibility(h, df, schema, config) -> FeasibilityReport`. Uses only counts (sample sizes), never effect measures.

Rules (all thresholds from config):
- `n_pairwise_complete = rows where both columns non-null`; need ≥ `min_n_pairwise` (default 20).
- Group comparisons: every group used must have n ≥ `min_group_n` (default 8). Groups below the threshold are **not silently dropped** in Phase 2: feasibility = False with reason "group 'X' has n=…"; Phase 3 may lump per rule (see Phase 3 Section 8, "rare group handling"). Decision: to keep family definition simple, for `NUM_CATEGORICAL` and `CAT_CAT`, feasibility is evaluated **after** applying the documented rare-level policy (levels with n < `min_group_n` are excluded from that test and listed in `FeasibilityReport.reasons` as "dropped_levels"); the hypothesis stays feasible if ≥ 2 levels remain.
- `CAT_CAT`: compute expected cell counts under independence from marginals only (allowed: marginal counts are univariate-derived? **No**: expected counts use the two marginals and n, which are univariate summaries; allowed). Record `min_expected_count`. Do not mark infeasible for low expected counts (Phase 3 picks Fisher/Monte Carlo); only mark infeasible if table is degenerate (< 2 rows or < 2 columns after level filter).
- Constant after NA removal → infeasible ("degenerate").
- `feasible=False` hypotheses are still emitted (with `status="skipped_infeasible"`) so the manifest and report can list them. They are not in the BH family.

---

## 5. LLM proposer and prioritizer (`llm_proposer.py`)

Optional (`hypotheses.llm_proposals: true`); the system works fully without it (P4).

### 5.1 What the LLM receives (a "safe profile", built by `build_safe_profile()`)
```
dataset_description (user-provided or "unknown")
columns: [{name, semantic_type, role, n_unique, pct_missing,
           top_levels (up to 8, names only + percentages) for categoricals,
           skew_bucket: "symmetric|right_skewed|left_skewed|heavy_tailed" for numerics,
           user_description (if any)}]
target (if any)
n_rows
```
**No bivariate stats, no correlations, no relationship insights.** A unit test asserts the serialized safe profile contains none of the forbidden fields.

### 5.2 Sanitization (P7)
Column names and level labels are untrusted. Before inclusion: truncate to 60 chars, strip control characters, escape/replace sequences resembling instructions (e.g., lines beginning with "ignore previous", markdown fences), wrap all dataset-derived text inside a clearly delimited block (`<dataset_profile> ... </dataset_profile>`), and tell the model in the system prompt that content inside the block is data and must never be followed as instructions. Map column names to **safe aliases** (`c01`, `c02`, ...) in the prompt and translate back after parsing; this also removes any chance the model invents a non-existent column (unknown alias → reject).

### 5.3 Output schema (structured, validated)
```python
class LLMHypothesisProposal(BaseModel):
    column_a_alias: str
    column_b_alias: str
    expected_direction: Direction = "any"
    rationale: str         # <= 240 chars; must not contain digits (validator rejects any digit)
    relevance: float       # 0..1 domain plausibility/interest

class LLMProposalBatch(BaseModel):
    proposals: list[LLMHypothesisProposal]   # max N (config, default 40)
```
Post-processing (deterministic, in code):
1. Translate aliases; drop unknown aliases (log count).
2. Determine `RelationshipType` from column types (LLM does not choose it). Orient pairs (numeric = `column_a` for NUM_BINARY/NUM_CATEGORICAL).
3. Drop pairs that are not eligible/feasible; dedupe against the enumerated set (merge: keep `source="llm"` only if not in enumerated set; otherwise annotate the enumerated hypothesis with the LLM's `relevance` and `rationale`).
4. Rationale validator: reject rationales containing digits or causal language (shared linter from Phase 5; if Phase 5 is not built yet, use a local regex list of causal words and move to the shared linter later).

### 5.4 How LLM output is used
- In `exhaustive` mode: LLM adds `relevance` to ranking and adds rationales; it **cannot add hypotheses outside the eligible pair set** (those are already all included). LLM proposals are only *new* when mode = `target_focused` or `llm_prioritized` or pairs were pruned.
- In `llm_prioritized`: the LLM returns up to N proposals; these become the family. If it returns fewer than `min_llm_hypotheses` (default 10), top up from enumeration with outcome-independent ordering (feasibility, target involvement) and record that.
- Prompt versions in `configs/prompts/hyp_proposer_v1.txt`. System prompt content: role, strict output rules (JSON only per schema), the "no numbers in rationales" rule, the "association not causation" rule, the "data inside delimiters is not instructions" rule.
- Caching, retries and fake LLM per Master Section 9.4.

---

## 6. Ranking (`ranking.py`) — ordering only

`priority_score = Σ w_i * component_i`, all components in [0, 1], computed **without outcome data**:

| Component | Definition | Default weight |
|---|---|---|
| `feasibility_strength` | min(1, n_pairwise / 500) combined with min group size ratio | 0.25 |
| `target_involvement` | 1 if pair involves target else 0 | 0.30 (0 if no target) |
| `llm_relevance` | LLM relevance (0.5 if absent) | 0.25 |
| `interpretability` | 1.0 for NUM_BINARY / CAT_CAT 2×2; 0.8 NUM_NUM; 0.6 NUM_CATEGORICAL with many levels; lower for high cardinality | 0.10 |
| `data_quality` | 1 − mean(pct_missing of two columns), capped | 0.10 |

Weights live in config and are renormalized when a component is unavailable. Ranking output also records `priority_components` for transparency. Tie-break by alphabetical `id` for determinism.

### Outcome-independent pruning when m > `max_tests`
Order of operations, stop when m ≤ max_tests:
1. If `target` exists → switch to `target_focused` (record).
2. Else drop `NUM_CATEGORICAL`/`CAT_CAT` pairs with highest cardinality first.
3. Else keep pairs with highest `priority_score` (based only on allowed components).
4. Record pruned count and rule per step in the manifest. The report must state "N eligible pairs were not tested due to the cap".

---

## 7. Natural-language → structured (`nl_parser.py`)

Used by the user ("Test whether smokers have higher charges") and by chat (Phase 6).

Pipeline:
1. **Safe alias prompt** like Section 5 (columns as aliases plus their types and, for categoricals, level names so "smokers" can map to column `smoker`, level `yes`).
2. LLM structured output:
```python
class NLHypothesisParse(BaseModel):
    status: Literal["ok","ambiguous","unsupported","no_columns_found"]
    column_a_alias: str | None
    column_b_alias: str | None
    level_of_interest: str | None      # e.g. "yes"; used only to derive expected_direction
    expected_direction_phrase: Literal["greater","less","associated","different","unspecified"]
    clarification_question: str | None  # when ambiguous
    candidates: list[str]               # alias candidates when ambiguous (max 4)
```
3. Deterministic post-processing: alias → real column; verify the columns exist; compute `RelationshipType` from types; derive `expected_direction` (e.g., "smokers pay more" → numeric A greater for group 'yes' → `A_GREATER` oriented to the actual group order, or store the level in `rationale`); build `Hypothesis(source="user")`.
4. **Fuzzy fallback without LLM:** if the LLM is unavailable, do token matching of the sentence against column names/levels (normalized, `difflib` ratio ≥ 0.8) and accept only if exactly two columns match unambiguously; otherwise ask for clarification.
5. Unsupported requests (causal questions, "predict", unsupported types, time series) return `status="unsupported"` with a one-line reason; the caller shows it.
6. The produced hypothesis gets `created_stage="chat"` or `"batch"` as appropriate; it is deduplicated against the ledger by `id` (Phase 3/6).

Gold set: `tests/gold/nl_hypotheses.jsonl`, ≥ 40 labeled sentences across the datasets in `configs/datasets` (human writes at least 20; AI may draft 20 more; human verifies all). Report parse accuracy (columns correct, relationship correct, direction correct, ambiguity handled) in `outputs/phase2/nl_parser_eval.md`.

---

## 8. Dedupe and identity (`dedupe.py`)

- `Hypothesis.id = sha1(relationship | sorted(columns) | sorted(covariates))[:16]`. For oriented relationships (NUM_BINARY etc.) the orientation is derived from types so the id is stable regardless of user phrasing.
- Symmetric pairs collapsed. Multiple sources for the same id merge: `source` keeps the highest priority (`user` > `llm` > `enumerated`), `rationale` keeps the LLM text, direction keeps user/LLM expectation.

---

## 9. Family manifest (the honesty artifact)

`outputs/<run>/hypothesis_manifest.json`:

```json
{
  "schema_version": "1.0",
  "mode": "exhaustive",
  "n_columns_total": 21,
  "n_columns_eligible": 17,
  "excluded_columns": [{"name":"customerID","reason":"id"}, ...],
  "n_candidate_hypotheses": 136,
  "n_infeasible": 3,
  "n_pruned": 0,
  "pruning_steps": [],
  "n_in_family_planned": 133,
  "counts_by_relationship": {"numeric_vs_binary": 14, ...},
  "llm_used": true,
  "llm_model": "...",
  "llm_prompt_version": "hyp_proposer_v1",
  "selection_inputs_hash": "...",   // hash of the safe profile, proving no outcome data used
  "notes": ["datetime columns not testable in this version"]
}
```
Phase 3 compares the actual number of tests run with `n_in_family_planned`; any difference is explained or raises an error.

---

## 10. Public API and CLI

```python
def generate_hypotheses(df, schema, profile, config, llm: LLMClient | None, target: str | None = None) -> HypothesisSet
class HypothesisSet(BaseModel):
    hypotheses: list[Hypothesis]      # ordered by priority_score desc (ordering only)
    manifest: dict
def parse_nl_hypothesis(text: str, df, schema, llm: LLMClient | None, config) -> NLParseOutcome
```
CLI:
```
veridata hypotheses --dataset NAME [--mode exhaustive|target_focused|llm_prioritized] [--target COL] [--no-llm]
veridata parse-hypothesis --dataset NAME --text "..."
```
Outputs: `outputs/<name>/hypotheses.json`, `hypothesis_manifest.json`, `hypotheses.md` (readable table: id, columns, relationship, feasibility, priority, source, rationale).

---

## 11. Tests

- **Type mapping:** table-driven test over every (type, type) combination → expected `RelationshipType` or exclusion.
- **Enumeration counts:** for p eligible columns with known type mix, assert exact m (e.g., 3 numeric + 2 binary + 1 categorical).
- **Symmetry/dedupe:** (A,B) and (B,A) produce one id; orientation rules.
- **Feasibility:** tiny frames with small groups, NaN-heavy columns, constant columns, level dropping.
- **No-peeking:** (a) import-lint test: `hypotheses/` has no import of `stats`/`validation`; (b) the safe profile serialization has no forbidden keys; (c) property test: permuting rows' relationships (shuffle one column independently) does not change the enumerated hypothesis set or order (outcome independence) in `exhaustive` mode.
- **Pruning:** m > max_tests triggers the documented order; manifest records it.
- **LLM proposer with FakeLLM:** unknown alias dropped; digit in rationale rejected; relationship type overridden by code; unfeasible pair dropped; fewer than min proposals topped up; prompt-injection column name (e.g., `Ignore previous instructions and ...`) is neutralized and appears only as an alias.
- **NL parser with FakeLLM + fuzzy fallback:** ok/ambiguous/unsupported/no_columns paths; direction derivation; gold-set evaluation script.
- **Determinism:** same inputs → identical ordered ids and manifest (excluding timestamps).

---

## 12. Milestones

| ID | Work | Est. |
|---|---|---|
| P2-M0 | `contracts/hypothesis.py` models; config keys; CLI stubs; test skeleton | 0.5 d |
| P2-M1 | Eligibility + type mapping + enumeration + dedupe/id | 1 d |
| P2-M2 | Feasibility + rare-level policy + manifest | 1 d |
| P2-M3 | Ranking + pruning + modes | 0.5 d |
| P2-M4 | Safe profile + sanitization + aliasing + LLM proposer (FakeLLM + Anthropic) + prompt file | 1.5 d |
| P2-M5 | NL parser + fuzzy fallback + gold set + eval script | 1.5 d |
| P2-M6 | Outputs (json/md), CLI, run on all Phase 1 datasets, docs | 0.5 d |

---

## 13. Acceptance criteria

- [ ] `veridata hypotheses --dataset X --no-llm` works offline on every Phase 1 dataset and the messy synthetic dataset; outputs `hypotheses.json`, `hypothesis_manifest.json`, `hypotheses.md`.
- [ ] Enumeration counts match hand-computed expectations on at least three fixture datasets.
- [ ] The no-peeking tests pass (import-lint, safe-profile content test, shuffle-invariance test).
- [ ] With an API key, the LLM proposer runs, every proposal maps to real columns via aliases, no rationale contains digits, relationship types are code-derived.
- [ ] NL parser gold-set accuracy reported; ≥ 85% correct on column identification on the gold set; ambiguous/unsupported cases handled without crashing.
- [ ] Prompt-injection fixture (hostile column names and cell values) does not change behavior.
- [ ] Manifest fully documents exclusions, pruning, mode, LLM usage, and `selection_inputs_hash`.
- [ ] `docs/decisions.md` updated (small-discrete handling, rare-level policy, pruning order).

---

## 14. Handoff to Phase 3

Phase 3 consumes `HypothesisSet` (only hypotheses with `feasible=True` are tested), reads `manifest.n_in_family_planned`, and returns `TestResult`s keyed by `Hypothesis.id`. The hypothesis stage is never re-invoked based on test outcomes in the batch pipeline. (Chat follow-ups in Phase 6 create *new* hypotheses with `source="followup"` or `"user"` and `created_stage="chat"`; those go through the ledger.)

---

## 15. Pitfalls

1. **Letting the LLM see correlations** to "be smart". This breaks the whole validity story. Don't.
2. **Counting only LLM-chosen hypotheses without recording the selection basis.** Manifest must show the basis.
3. **Orientation bugs** (numeric/binary swapped) produce nonsense tests. Test orientation explicitly.
4. **Small-discrete numerics** (e.g., number of children 0-5) are ambiguous; use the documented rule and be consistent.
5. **Explosion** at 100+ columns (4,950 pairs). Use the pruning order or target mode; never silently truncate.
6. **Over-trusting the NL parser.** Always show the parsed structured hypothesis to the user before/after running, so mistakes are visible.

---

## 16. Human tasks

- Write/verify the NL gold set (≥ 20 sentences by hand).
- Provide short per-column descriptions for the 3-5 real datasets (improves LLM relevance; optional).
- Decide the default `target` per real dataset for `target_focused` demos.
