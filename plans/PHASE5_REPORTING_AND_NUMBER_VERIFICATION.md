# PHASE 5 — Reporting, Charts, Plain-Language Explanations, Number Verification

> Prerequisite reading: `00_MASTER_PLAN.md` (P1, P5, P7, Section 5.5-5.7), `PHASE3_STATISTICAL_TOOLS_AND_VALIDATION.md` (`Finding`, `TestResult.descriptives`).
> This phase delivers the project's most visible promise: **every number in the explanation comes from a tool, and this is machine-verified.**
> The deterministic path (templates, no LLM) is built first and must be complete on its own. The LLM adds only fluency, and its output is checked.

---

## 1. Goals

1. **Fact registry:** convert every `Finding` into a set of `Fact`s, the only numbers allowed in text.
2. **Narration:** produce plain-language explanations (a) deterministically from templates, and (b) optionally via an LLM that may only use fact placeholders; both pass the verifier.
3. **Number verifier:** reject any text containing a number not in the registry (with defined tolerances and whitelists); retry, then fall back to the template.
4. **Language linter:** enforce association-not-causation wording, no overclaiming, correct interpretation of each test.
5. **Charts:** one chart type per relationship, plus summary charts (forest, volcano, BH plot, rejection breakdown).
6. **Report builder:** Markdown + self-contained HTML report with summary, validated findings, rejected patterns ("what looked interesting but was rejected, and why"), methods, data-quality summary, limitations.

### Out of scope
LangGraph orchestration and chat explanations beyond reusing these functions (Phase 6); UI (Phase 7).

---

## 2. Module layout (`src/veridata/reporting/`)

```
facts.py            # build_facts(Finding) -> list[Fact]; FactRegistry
templates.py        # deterministic text templates per relationship/test/effect
narration.py        # slot-based LLM narration + fallback orchestration
number_verifier.py  # extract & verify numbers in text
language_lint.py    # banned/required wording rules
charts/             # style.py scatter.py groups.py categorical.py forest.py bh_plot.py volcano.py rejection_bar.py data_quality.py
report_builder.py   # assemble sections -> Markdown/HTML
html.py             # self-contained HTML (inline CSS, base64 images)
```
Prompts: `configs/prompts/narration_v1.txt`, `configs/prompts/summary_v1.txt`.

---

## 3. Fact registry (`facts.py`)

### 3.1 What becomes a Fact
Every numeric or label value that might appear in text:
- Sample: `n_used`, `n_total`, per-group `n_<label>`, % missing dropped.
- Test: `test_name` (string), `statistic`, `df`, `p_raw`, `q_value`, `family_size`, `alpha`.
- Effect: `effect_name`, `effect_value`, `ci_low`, `ci_high`, `ci_level`, `magnitude_label`, `comparable_value`.
- Descriptives (type-dependent): group means/medians/sds, mean difference and its CI, correlation coefficient, slope, percent in each cell, odds ratio and CI, top residual cells and their percentages, probability of superiority.
- Context: counts of tested/rejected hypotheses, `n_raw_significant`, `n_accepted`, counts by rejection reason (for summary sections).
- Strings: column names, level labels, group names (exact original strings).

### 3.2 Formatting rules (`display` field)
- p-values: `<0.001` below 0.001; else 3 decimals; q-values same.
- Effect sizes and correlations: 2 decimals; CI: 2 decimals; means: adaptive (2 significant decimals, thousands separators); counts: integer with thousands separators; percentages: 1 decimal with `%`.
- Always keep the **raw value** (`value`) and the **exact displayed string** (`display`). The verifier compares against `display` strings and numeric values within the display precision.
- Fact keys are namespaced per finding: `f12.effect_value`.

### 3.3 Traceability
Each `Fact.source` records the field path (e.g., `TestResult.effect.ci_low`). A debug view (`facts_table.md`) lists every fact for a finding; used in tests and the UI ("show me where this number came from").

### 3.4 Registry API
```python
class FactRegistry:
    def add(self, fact: Fact) -> None
    def for_finding(self, finding_id: str) -> list[Fact]
    def allowed_numbers(self, finding_ids: list[str] | None = None) -> set[AllowedNumber]   # numeric value + display + tolerance
    def render(self, template: str, finding_id: str) -> str   # fills {fact_key} placeholders, raises on missing key
```

---

## 4. Deterministic templates (`templates.py`) — the always-available explanation

One template family per (relationship, test path). Each template is a function `(finding, registry) -> str` that builds 3 parts: **Result sentence**, **Magnitude/interpretation sentence**, **Caveat sentence(s)**. All numbers via `registry.render`.

### 4.1 Examples (wording is normative; adapt phrasing but keep structure and the safety words)

**NUM_BINARY, Welch** (`welch_t`, `hedges_g`):
"Among {n_used} records, the average {numeric_col} was {mean_g1} for {col_b}={g1} and {mean_g2} for {col_b}={g2} (difference {mean_diff}, 95% CI {diff_ci_low} to {diff_ci_high}). The difference is {magnitude_label} (Hedges' g = {effect_value}). After correcting for {family_size} tests (FDR {alpha_pct}), the association is statistically supported (adjusted p {q_display}). This is an observed association and does not show that {col_b} causes the difference."

**NUM_BINARY, Mann-Whitney:**
"Values of {numeric_col} tended to be higher for {higher_group} than for {other_group} (median {med_g1} vs {med_g2}; probability that a random {higher_group} record exceeds a random {other_group} record: {prob_sup}). ... rank-biserial correlation {effect_value} ({magnitude_label})..." — must **not** say "medians differ significantly" unless the shapes-similar flag is true; otherwise "tends to be higher".

**NUM_CATEGORICAL:** names the highest and lowest groups by mean (Welch ANOVA) or median (Kruskal), η²/ε² as "{pct_var}% of the variation in {numeric_col} is associated with {col_b}" (η² × 100, formatted as a fact `eta_sq_pct`).

**NUM_NUM:** "{col_a} and {col_b} are {positive|negative}ly associated (Pearson r = {r}, 95% CI ...; n = ...)": for Spearman: "rank correlation ρ = ...; the relationship is monotonic and may not be linear." Add the slope phrase only for Pearson ("each extra unit of {col_a} corresponds to {slope} {col_b} on average" — as description of the fitted line, not causal).

**CAT_CAT:** 2×2: odds ratio with CI and percentage of level in each group (facts). r×c: Cramér's V with magnitude and the top two cells by standardized residual in plain words ("more {level_a}-{level_b} records than expected: {observed_pct} observed vs {expected_pct} expected").

**Caveat sentences** (conditional, from `flags`/assumptions): non-normal data handled by a rank-based test; fragile to outliers; sparse table handled by simulation; small n; rows assumed independent (once per report, not per finding); trivial/derived relationship.

**Rejected pattern templates** (per `RejectionReason`):
- `not_significant_after_correction`: "Raw p = {p_raw}, but after correcting for {family_size} tests the adjusted p is {q}. With this many comparisons, a pattern like this is expected by chance, so it is not reported as a finding."
- `effect_below_threshold`: "Statistically detectable (adjusted p {q}) but the effect is negligible ({effect_name} = {effect_value}, below the {threshold} threshold), so it has little practical importance."
- `assumption_violated_no_fallback`, `insufficient_data`, `degenerate_data`, `test_error`, `trivial_relationship` ("These two columns appear to be derived from one another or measure the same thing ({effect_name} = {effect_value}); this is a data-structure observation, not a discovery.").

### 4.2 Magnitude words
`magnitude_label` comes from Phase 3 thresholds (negligible/small/medium/large); never invented by narration.

---

## 5. LLM narration (optional; `narration.py`)

Config `reporting.narration: llm_slots | template_only` (default `llm_slots` when an LLM is available, else `template_only`).

### 5.1 Slot-based generation (strong guarantee)
The LLM receives, per finding (or batch of ≤ 5), a JSON of **facts with keys and display strings**, the relationship type, the deterministic template text (as a reference of required content), and instructions:
- Write 2-4 sentences in plain language for a non-statistician.
- Insert numbers **only** as placeholders `{{key}}` using the provided keys. Never type a digit yourself.
- Use "associated with", never causal verbs.
- Mention the effect magnitude using the provided `magnitude_label`.
- Include the caveats listed in `required_caveats`.
- Output JSON: `{ "text": "...", "used_keys": [...] }`.
- The data block is delimited; column names/levels are untrusted data.

Post-processing: replace `{{key}}` with `display`; unknown keys → fail; leftover digits → verifier (Section 6).

### 5.2 Fallback ladder
1. LLM slot text → verify (numbers, language lint, required caveats present, length bound).
2. On failure retry once with the verifier's error message appended.
3. On second failure → **deterministic template text** (always valid). Record `narration_source: "template_fallback"` and the failure reason in `report_meta.json`.
This ladder guarantees the final report never contains an unverified number, even when the LLM misbehaves.

### 5.3 Summary paragraph
An executive summary (3-6 sentences) built from summary facts: dataset size, tests run (m), raw significant count, validated count, rejected by reason counts. Same slot mechanism; template fallback exists. Optional "highlights" bullet list (top 3 findings by effect magnitude) via templates only.

### 5.4 Caching
Narration calls cached by hash(facts JSON, prompt version, model).

---

## 6. Number verifier (`number_verifier.py`) — core of the project's claim

`verify_text(text, registry, finding_ids, *, whitelist) -> VerificationResult(ok, violations[], extracted[])`

### 6.1 Extraction
Regex-based tokenizer that finds: integers (with thousands separators `1,338`), decimals (`.42`, `0.42`, leading `-`/`+`/`−`), percentages (`12.3%`, `12 percent`), scientific notation (`3e-5`, `3.2×10^-4`), ranges (`0.1 to 0.3`, `0.1–0.3` split into two), inequalities (`<0.001`, `p < .05`, `p=0.03`), fractions (`3/5`), currency/unit-attached numbers (`$12,345`, `12 kg`), and **number words** ("one", "two", ..., "twelve", "hundred", "dozen", "half") — number words are checked against a whitelist (structural counts only).
Ignore: digits inside identifiers that exactly match a column name or level label present in facts (e.g., column `age_2`, level `65+`, a column named `v07`): detect by matching the token against the registry's string facts before flagging; markdown list numbering (`1.`, `2.`) at line start; years only if whitelisted (`allow_years: false` default); `95%` when it equals the registry's `ci_level` fact.

### 6.2 Verification
Each extracted number must match an allowed fact either by:
- **display equality** (string after normalization, e.g., `.42` ↔ `0.42`, `1338` ↔ `1,338`), or
- **numeric closeness** within the fact's displayed precision (|x − v| ≤ 0.5·10^(−decimals shown)); percentages convertible both ways (0.123 ↔ 12.3%).
Derived numbers (e.g., LLM computing "about three times higher") are **violations** unless the ratio is itself a registered fact; the template layer pre-computes useful ratios/differences (`ratio_means`, `mean_diff`, `pct_diff`) so narration has no reason to compute.
Whitelist of structural numbers allowed without registry: counts of items the text itself enumerates ("two groups", "three columns") **only when** the corresponding structural fact exists (`n_groups`, `n_columns_involved`) — otherwise violation; the verifier is strict by default (`strict: true`), configurable for UI/chat phrasing.

### 6.3 Output
`VerificationResult.violations`: list of `{token, span, reason: "not_in_registry" | "precision_mismatch" | "derived_number" | "unknown_key"}`. Used to build the retry message and the test assertions.

### 6.4 Tests (adversarial; the main correctness evidence for P1)
- Positive: template outputs for all relationship/test paths verify at 100%.
- Negative: constructed texts with (a) a fabricated number, (b) a rounded-differently number (0.42 vs 0.43), (c) a derived number ("twice as high"), (d) number words ("three times"), (e) percent vs fraction confusion, (f) a number matching a different finding's fact (cross-finding leakage: must fail when verifying against finding A only), (g) scientific notation, (h) ranges, (i) digits in a column name (must pass), (j) markdown list numbers (must pass), (k) unicode minus/digits (e.g., `−0.31`, Arabic-Indic digits → violation unless registered).
- Fuzz: random numeric strings inserted into valid text always detected.
- Integration with FakeLLM: scripted bad outputs trigger retry then fallback; the final text always verifies.
- A **report-level verifier** runs over the complete rendered Markdown (all sections) as the last build step; the build fails (or flags) if any violation remains. Chart annotation text goes through the same check.

---

## 7. Language linter (`language_lint.py`)

Rules (regex/lexicon-based; word-boundary, case-insensitive), each with an error code:
- **Banned causal language** in finding explanations: causes, caused by, leads to, results in, due to, because of, drives, affects (as a claim), impact on (ok in "impact" only when defined? ban to be safe), makes, increases/decreases when used causally ("smoking increases charges" banned; "smokers have higher charges" fine), responsible for, determines, effect of (use "association with"). A lexicon test file documents examples.
- **Banned overclaims:** proves, confirms, definitively, certainly, undeniable, guarantee. "Significant" must be qualified: allowed only as "statistically supported"/"statistically significant after correction"; bare "significant"/"significantly" banned in prose.
- **Required qualifiers:** every accepted-finding text includes at least one of "associated with"/"tend to"/"on average" and the correction statement; each report includes the independence assumption note, and a limitations section.
- **Direction words consistency:** if text says "higher" the fact `direction_observed` must agree (check pairs of words vs structured direction: lint compares narrated direction word to `direction_observed`). Implement for NUM_BINARY and NUM_NUM (positive/negative).
- **Mann-Whitney guardrail:** text for MWU may not contain "median" claims unless the median facts are in the registry; may not say "means".
Linter runs on template text (unit tests ensure templates themselves pass), on LLM text (violation → retry/fallback), and on chat answers (Phase 6).

---

## 8. Charts (`reporting/charts/`)

General: matplotlib + seaborn; Agg backend; consistent style module (`style.py`): colorblind-safe palette (e.g., Okabe-Ito), font sizes ≥ 10pt, 150 dpi, figure sizes fixed (6.5×4.2 in), titles state the takeaway using a fact-registry string (e.g., "Charges are higher for smokers") — title text goes through the verifier too; axis labels use the original column names (wrapped/truncated to 40 chars) with units if known; no chartjunk; each chart saved as PNG and, optionally, SVG; deterministic output (seeded jitter). Every chart function signature: `plot_x(finding, df, registry, out_path) -> Path` and **uses only `df` and the `Finding`** (numbers annotated on charts come from facts).

| Relationship | Chart | Details |
|---|---|---|
| NUM_BINARY | **Violin/box + jittered points** (subsample ≤ 800 points/group), mean markers with 95% CI error bars | annotate n per group, effect size, adjusted p ("q") |
| NUM_CATEGORICAL | box plot ordered by median/mean, n per group under labels, group means with CI | cap at 12 groups (+ "Other" lump for display only, labeled) |
| NUM_NUM | scatter (hexbin when n > 3,000), linear fit with CI band (Pearson) or LOWESS curve (Spearman) | annotate r/ρ and n; log-axis suggestion only if skew fact flags (display transform labeled) |
| CAT_CAT | **100% stacked bars** (proportion of B within each A level) + a small **standardized residual heatmap** | annotate V and n; top cells highlighted |
| Summary | **Forest plot** of accepted effects (standardized comparable value with CI; grouped by relationship; sorted by magnitude) | |
| Summary | **BH plot**: sorted p-values vs the BH line `(i/m)·alpha`, accepted points highlighted, rejected-by-floor marked differently | shows *why* correction matters |
| Summary | **Volcano-style**: effect size (x) vs −log10(q) (y); thresholds drawn; quadrant labels ("significant but trivial", "validated", "not significant") | |
| Summary | **Rejection breakdown** bar: counts by `RejectionReason` and counts of raw p<alpha vs accepted | headline "naive vs validated" chart |
| Data quality | missingness bar, cleaning summary table image (from Phase 1 log) | optional |

Chart tests: each function produces a non-empty PNG with expected dimensions on fixture data; no exceptions for edge cases (a group with n=8, constant-ish data, 1 level dominating, 15+ levels, all-integer numeric, NaNs); deterministic hash for the same input (use `savefig(metadata={"Software": None})` to remove timestamps); a **visual review checklist** run by the human on the 3 real datasets: readable labels, no overlaps, colors distinguishable, titles accurate.

---

## 9. Report builder (`report_builder.py`)

### 9.1 Report structure (Markdown → HTML)
1. **Title block:** dataset name, rows × columns after cleaning, date, VeriData version, config hash.
2. **Executive summary** (summary paragraph + the "naive vs validated" headline numbers + rejection breakdown chart). Example facts-driven bullets: "Tests run: {m}", "Raw p < 0.05: {n_raw}", "Validated findings: {n_acc}", "Rejected: by reason ...".
3. **Validated findings** (sorted by `comparable_value` descending, capped by `max_findings_in_report` with the rest in an appendix table): for each: heading ("A ↔ B"), explanation text, chart, a compact stats table (test used & why, statistic, df, p, q, effect with CI, n, flags), collapsible "How was this tested?" (selection trace summarized in plain language) and "Where do the numbers come from?" (facts table).
4. **Patterns that looked interesting but were rejected** — table + short explanations (top 10 by raw p), grouped by reason. This is the signature section demonstrating the validation layer.
5. **Likely derived / duplicated columns** (from `TRIVIAL_RELATIONSHIP`).
6. **Data quality summary** (from Phase 1 cleaning log; key counts only, verified numbers).
7. **Methods:** how hypotheses were generated (manifest: mode, eligible/tested counts, LLM role), test library table, selection rules in plain language, correction (BH at q), effect-size floors, assumptions, what "validated" means.
8. **Limitations (mandatory, static + dynamic):** association not causation; rows assumed independent; pairwise only (no interactions/confounding control); BH dependence caveat; post-selection optimism of effects/CIs; descriptive CIs unadjusted; missing data handled by pairwise deletion; cleaning choices; LLM role; dataset-specific warnings (small n, heavy missingness).
9. **Appendix:** full results table (all tests: hypothesis, test, p, q, effect, decision, reason), config used, reproducibility info (dataset SHA-256, seeds, versions), fact tables.

### 9.2 Outputs
`outputs/<run>/report/{report.md, report.html, figures/*.png, findings_summary.csv, report_meta.json}`. `report.html`: self-contained (inline CSS, base64-embedded PNGs), responsive, print-friendly, collapsible sections via `<details>`. `report_meta.json`: narration source per finding (llm/template/fallback), verifier stats (n texts, n violations caught, retries), model/prompt versions, token cost.

### 9.3 Final build gate
After assembling: run verifier + linter over the entire Markdown; run a check that every image referenced exists; produce `report_checks.json`; non-zero violations ⇒ the build raises `ReportingError` (CLI exit code ≠ 0) unless `--allow-violations` (debug).

---

## 10. CLI and API

```
veridata report --dataset NAME [--narration llm_slots|template_only] [--max-findings 30] [--format md,html]
veridata verify-text --facts facts.json --text "..."    # debugging tool for the verifier
```
```python
def build_report(findings: list[Finding], hypothesis_manifest: dict, cleaning_log: list, profile: DataProfile, df, config, llm: LLMClient | None, out_dir: Path) -> ReportArtifacts
def explain_finding(finding: Finding, registry: FactRegistry, llm: LLMClient | None, config) -> Explanation   # used by Phase 6 chat
class Explanation(BaseModel): text: str; source: Literal["llm","template","template_fallback"]; verified: bool; violations: list; used_fact_keys: list[str]
```

---

## 11. Milestones

| ID | Work | Est. |
|---|---|---|
| P5-M0 | `Fact` model finalized, `FactRegistry`, formatting rules | 1 d |
| P5-M1 | `build_facts` for every relationship/test path; facts table debug view | 1 d |
| P5-M2 | Deterministic templates (all paths + rejection reasons + caveats) | 1.5 d |
| P5-M3 | Number verifier + adversarial tests | 1.5 d |
| P5-M4 | Language linter + tests; templates pass lint | 0.5 d |
| P5-M5 | LLM slot narration + retry/fallback + FakeLLM tests | 1 d |
| P5-M6 | Charts (type-specific) + style + tests | 2 d |
| P5-M7 | Summary charts (forest, BH, volcano, rejection) | 1 d |
| P5-M8 | Report builder, HTML, final gate, CLI; run on all datasets | 1.5 d |
| P5-M9 | Visual QA with the human, fixes | 0.5 d |

---

## 12. Acceptance criteria

- [ ] For every `Finding` in the three real datasets and the benchmark smoke suite, template text verifies at 100% and passes the linter.
- [ ] Verifier adversarial suite passes (all negative cases flagged, all positive cases pass); recall of fabricated-number detection ≥ 99% on the fuzz test.
- [ ] With FakeLLM scripted to produce bad outputs (fabricated numbers, causal verbs, missing caveats, unknown keys), the final report text is still 100% verified (via retry/fallback).
- [ ] With a real LLM (if key present) on 3 datasets: ≥ 90% of narrations pass on first attempt; the rest recovered by retry/fallback; `report_meta.json` documents rates.
- [ ] All chart types render on fixture edge cases; human visual QA checklist signed off on at least 3 reports.
- [ ] `report.html` opens offline (no external assets), under 15 MB; Markdown renders cleanly.
- [ ] Report contains the "rejected patterns" section with reason text and the executive "naive vs validated" numbers.
- [ ] Report-level verifier reports zero violations for all generated reports; the build gate triggers on an injected violation (test).
- [ ] Every report includes limitations and the independence-assumption note.

---

## 13. Handoff

- **To Phase 6:** `FactRegistry`, `explain_finding`, `verify_text`, `lint_text`, chart functions; `Explanation` objects with `verified` flags.
- **To Phase 7:** `report.html`, figures, `findings_summary.csv`, facts tables for the "where did this number come from" UI feature.
- **To Phase 8:** E4 (number-verification experiment) reuses `number_verifier.py` on LLM-only outputs.

---

## 14. Pitfalls

1. **LLM-typed numbers in titles/captions** sneak past if only body text is verified; verify chart titles and captions too.
2. **Rounding mismatches** (0.425 displayed 0.42 vs 0.43): always compare against `display`; precompute displays once.
3. **Direction-word contradictions** (narration says "lower" while data shows higher). The direction lint catches this.
4. **Over-explaining Mann-Whitney** as a median difference.
5. **Chart overload:** 30 findings × chart = long report. Cap and put the rest in the appendix table.
6. **Verifier false positives on column names containing digits** (e.g., `Q3_sales`). Handle via registry string facts.
7. **HTML size blowup** from base64 images: compress PNGs, use 150 dpi, cap figure sizes.
8. **Hidden number sources**: any helper that formats numbers outside the registry defeats P1. Grep test: no f-strings with numeric formatting in `templates.py` except through `registry.render`.

---

## 15. Human tasks

- Visual QA of charts and reports on the 3 real datasets.
- Read 10 narrations for tone and clarity; adjust templates (wording changes require rerunning the linter and verifier tests).
- Approve the limitations text.
