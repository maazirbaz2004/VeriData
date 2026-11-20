# PHASE 8 — Full Evaluation, Benchmarking, and Final Deliverables

> Prerequisite reading: `00_MASTER_PLAN.md` (Section 8 definitions), Phase 4 (suites, matcher, metrics, frozen protocol), Phase 5 (number verifier), Phase 6 (transcripts, ledger), Phase 7 (demo).
> This phase produces the evidence for the project's claim and the final written deliverables. **Pre-register first, run once, report honestly, including unfavorable results.**

---

## 1. Goals

1. **E1 Main benchmark:** LLM-only analyst vs VeriData without correction vs full VeriData, on the synthetic suite with planted truth (recall, precision, FDR, null-dataset false positives).
2. **E2 Ablation:** which validation component earns its keep (BH, effect floor, assumption-aware test selection, correction variants).
3. **E3 Calibration summary:** Type-I error and BH under dependence (from Phase 4; summarized).
4. **E4 Number correctness:** verified-number rate of LLM-only outputs vs VeriData.
5. **E5 Real datasets (3-5 Kaggle):** reference-finding recovery, permuted-column null checks, injected noise columns, split-half replication, qualitative comparison with the LLM-only analyst.
6. **E6 Test-selection accuracy** (as in the original plan) and **E7 chat evaluation** (router/tool/answer correctness, hallucinated-number rate).
7. **E8 Robustness:** performance on messy inputs through the whole pipeline.
8. **Final deliverables:** final report/paper, README, user guide, architecture doc, limitations, reproducibility package, demo materials, release tag.

---

## 2. Evaluation protocol (freeze before running; `docs/eval_protocol.md`)

Mark the file `STATUS: FROZEN` with a git tag `eval-protocol-frozen` **before** any test-split run. The protocol must contain: suites and seeds (dev vs test), system definitions and configs, LLM models/versions/prompts/temperatures/repeats, the matching rule (Phase 4 §6), all metrics and their formulas, the statistical procedures for CIs and comparisons, the real-dataset reference findings (written before running), the list of experiments, and what will *not* be tuned. Any deviation after freezing is recorded in a "Deviations" section with reasons.

Reference findings for real datasets (E5) are written **before** running VeriData on them, by the human, from domain knowledge or Phase 1 manual insights; stored in `configs/eval/reference_findings/<dataset>.yaml`:
```yaml
dataset: insurance
reference_findings:
  - {col_a: smoker, col_b: charges, direction: "smoker higher", confidence: strong}
  - {col_a: age, col_b: charges, direction: positive, confidence: strong}
  - {col_a: bmi, col_b: charges, direction: positive, confidence: moderate}
known_nulls:        # pairs believed unrelated (optional, modest)
  - {col_a: region, col_b: sex}
```
Only `strong`/`moderate` items count toward recovery; `known_nulls` used cautiously (not as hard truth).

---

## 3. Systems under test

| ID | System | Description |
|---|---|---|
| S1a | **LLM-only (summary mode)** | LLM receives schema, `describe()`, head and a random sample (same as Phase 1 Mode A) and must list statistically supported findings. No code execution. |
| S1b | **LLM-only (code mode)** | LLM writes pandas/scipy code in the Phase 1 sandbox, with ≤ 8 turns, then outputs findings. The strong baseline: real computation but no systematic validation. |
| S2 | **VeriData-nocorrection** | Same agent pipeline; accepted = raw p < alpha (no BH, no effect floor). |
| S3 | **VeriData-full** | Full pipeline (BH at 5% + effect floor + assumption-aware selection + gates). |
| A1 | bh_only | BH, no floor, assumption-aware selection on |
| A2 | floor_only | No correction, floor on |
| A3 | assumption_only | Assumption-aware selection, raw p < alpha, no floor |
| A4 | naive_tests | Parametric tests always (Welch t / ANOVA / Pearson / chi-square), BH + floor on (isolates the selection component) |
| A5 | bonferroni / holm / by | alternative corrections, floor on |
| A6 | full_minus_floor, full_minus_gates | leave-one-component-out variants |

**LLM-only fairness rules (document in the protocol):**
- Same data access in S1b as the pipeline (the cleaned CSV, or the raw CSV if evaluating without cleaning; decide per experiment and apply to all systems equally).
- Same output format: a JSON list of findings `{col_a, col_b, direction?, claim, evidence?}`; closed schema parsed automatically; no free-form scoring by a human.
- A **well-engineered prompt** (reviewed by a teammate for fairness: instructs to avoid false positives, to consider multiple testing, to use appropriate tests). Include a second prompt variant "careful" to show the LLM was given a fair chance; report both. Prompt versions saved and frozen.
- Same time/turn/token budget; record cost.
- Repeats: R = 5 runs per dataset per LLM system (temperature 0.7 for diversity; plus one temperature-0 run for reference). Report mean ± SD and per-run points.
- Model(s): primary = the project default model (`llm.model`); optionally one stronger and one cheaper model to show robustness (nice-to-have; state in protocol).
- Pairs are mapped to canonical unordered column pairs by the same parser; claims mentioning unknown columns are discarded and counted as "hallucinated column" events.
- LLM-only gets no information about the ground truth, suite design, or that datasets are synthetic.

Each system implements the `SystemFn` interface (Phase 4 §5) and is registered in `evaluation/systems/`.

---

## 4. Experiments

### E1 — Main benchmark (synthetic, planted truth)
- **Suite:** `core60` **test** split (+ `full` if compute allows).
- **Systems:** S1a, S1b, S2, S3 (A-series in E2).
- **Metrics (Phase 4 §6):** recall (testable truths), precision, FDR (mean FDP), FWER on pure-null datasets (fraction with ≥ 1 report), mean false positives per null dataset, secondary direction-aware versions; per-dataset values stored.
- **Stratifications:** by effect strength, relationship form, n, p, distribution shape, presence of correlated null blocks, missingness.
- **Plots:** (a) FDR and recall bars per system with bootstrap CIs; (b) recall vs effect size per system; (c) FDR vs number of columns (more columns → more false discoveries for naive systems); (d) FDR vs n; (e) false positives on null datasets (strip/box plot); (f) recall–FDR trade-off curve for VeriData by varying alpha ∈ {0.01…0.2} (and the LLM-only point as a single point); (g) q-value calibration plot.
- **Statistics:** dataset-level bootstrap 95% CIs (2,000 resamples); paired comparisons between systems with Wilcoxon signed-rank on per-dataset FDP/recall differences (report effect, CI, p; do not over-claim; note n datasets); for LLM repeats: average per dataset over repeats first, then bootstrap across datasets (repeats are not independent datasets).
- **Primary hypothesis (pre-registered):** VeriData-full has lower FDR than S1a/S1b/S2 with recall not worse than the best of them minus a stated margin (e.g., ≥ 0.8× of S2's recall at medium/large effects). State what outcome would *falsify* the claim.

### E2 — Ablation of validation components
- Systems A1-A6 plus S2 and S3 on the same suite. Table: FDR, recall, FWER_null, mean FP count, per variant; marginal contribution of each component (S3 minus component).
- Expected narrative (verify, don't assume): correction drives the FDR drop; the effect floor reduces trivial findings at large n (show at n = 5000); assumption-aware selection fixes Type-I inflation for skewed/heavy-tailed data and small n (show in the corresponding strata); gates handle derived columns.
- Report any component that does **not** help (honest negative results are fine).

### E3 — Calibration summary (from Phase 4)
Include the Type-I table/plot and BH-vs-BY under dependence in the final report; state where BH's FDR exceeded 5% (if so, show BY's behavior and its recall cost).

### E4 — Number correctness
- **Data:** the outputs of S1a/S1b on core60-test and the real datasets (their free-text claims) vs VeriData's reports.
- **Procedure:** extract numeric claims (Phase 5 extractor + Phase 1 claim extraction), verify against ground truth recomputed **independently** (plain scipy/pandas in an evaluation module, not VeriData's own functions, to avoid circularity). Tolerances: counts exact; percentages ±0.5 pp; correlations/means ±1% relative; p-values: log10 difference ≤ 0.3 or same significance side (document).
- **Metrics:** verified-claim rate = correct / checkable; fabricated-number rate; unverifiable share. For VeriData, run the Phase 5 verifier **and** the independent recomputation check: both 100% expected; any failure is a bug to report.
- A small manual audit: human reads 30 random LLM claims to validate the extractor's recall/precision (report the audit result).

### E5 — Real datasets (3-5 Kaggle)
Datasets: those from Phase 1 (e.g., insurance, Telco churn, heart disease, student performance, bank marketing). For each, run S1a, S1b, S2, S3 (S1 with R = 3 repeats to save cost).
1. **Reference-finding recovery:** fraction of strong/moderate reference findings recovered (pair + direction). Report per dataset and system.
2. **Permuted-column null check:** create K = max(5, 25% of columns) permuted copies: each selected column independently row-shuffled (seeded), destroying its relationships. Pairs involving at least one permuted column are *known null* (except permuted×permuted also null). Metric: false-positive count/rate among those known-null pairs per system, repeated over 20 permutation seeds per dataset. (Pairs among unpermuted columns are unknown and excluded from this metric.)
3. **Injected noise columns:** append 10 synthetic noise columns (mixed types) to each dataset; same metric; report both (1) and (3) since they probe slightly different failure modes (shuffling preserves marginal distributions exactly).
4. **Split-half replication:** randomly split rows 50/50 (20 repeats); run each system on half A; check whether findings replicate on half B (VeriData: replication = the pair is also accepted on B, or raw p < 0.05 in the same direction on B as a looser criterion; report both). Replication rate = replicated / reported. Compare systems: naive/LLM-only should replicate less. (This is a ground-truth-free reliability metric.)
5. **Stability:** Jaccard similarity of accepted sets across 20 bootstrap resamples per system.
6. **Qualitative comparison:** side-by-side of S1 vs S3 for each dataset (plain table: finding, who found it, supported?), with a human annotation column (valid / spurious / trivial / misreported). Human annotates blind to system identity where possible (shuffle the order and hide labels), for at least 2 datasets.
7. **LLM familiarity note:** state that public datasets may be memorized by the LLM (contamination advantage to the baseline), so this experiment is not used for the main claim.

### E6 — Test-selection accuracy
- **Oracle definition:** for synthetic data, the generator knows the distribution family, n, imbalance. Oracle test = table lookup recorded in the protocol (e.g., normal & n ≥ 20 per group → Welch; lognormal/t3/zero-inflated with n < 50 per group → Mann-Whitney; large n with moderate skew → Welch acceptable). Because "appropriate test" has an acceptable *set* in many cells, define accuracy as selection ∈ acceptable set.
- **Metrics:** selection accuracy overall and by relationship; **consequence-based accuracy** (the more convincing metric): for each selection, did the chosen test keep empirical Type-I error within [0.04, 0.06] under null and retain ≥ 90% of the best available power under the alternative? Use Phase 4 calibration outputs.
- Also compare the VeriData selector with: always-parametric and always-nonparametric selectors (calibration + power tables).
- For the LLM-only system: record which tests it used (from code mode) and whether they were appropriate under the same acceptable-set rule (secondary).

### E7 — Chat evaluation
- **Question set:** ≥ 60 questions (Phase 6 gold set + extra) over ≥ 3 datasets, spanning intents, paraphrases, typos, ambiguous and out-of-scope questions, multi-turn sequences (≥ 10 conversations of 3-5 turns).
- **Metrics:** intent accuracy; argument accuracy (columns/levels/relationship); **answer correctness** (the test statistics/effect/p reported equal an independent recomputation within tolerance); **verified-number rate** (100% expected); causal-language violations (0 expected); clarification appropriateness (ambiguous questions → clarification, not guess; measure rate); out-of-scope handling; follow-up executability (100%); duplicate-test suppression; latency and cost per turn.
- **Baseline:** a plain LLM chat over the CSV (summary mode and code mode) answering the same questions: numeric correctness and fabricated-number rate vs VeriData chat.
- Human rating (1-5) of helpfulness and clarity on 20 sampled turns per system (two raters if possible; report agreement).

### E8 — Robustness (messy and awkward inputs)
- Suite `robustness`: core subset with Phase 1 messy injection (whitespace, case variants, placeholder tokens, numeric-as-string, mixed date formats, duplicates, outliers).
- Run through the **full** pipeline (profile → clean → hypothesize → test → validate) and compare recall/FDR with the clean versions; also the LLM-only systems on the messy files.
- Optional: wide data (150 columns, 3,000 rows) and small data (n = 40) edge cases: runtime, FDR behavior, number of skipped tests.

---

## 5. Compute and cost plan (write numbers into the protocol)

- Estimate: VeriData variants ≈ (60 datasets × ~10 variants) fast-mode runs (minutes each on 8 cores). LLM-only: 60 datasets × 2 modes × R=5 ≈ 600 runs; code mode uses several turns; budget tokens (e.g., ≤ 60k tokens/run). Set a hard budget cap in code (`eval.max_cost_usd`), log cost per run, and abort gracefully when exceeded (resume later from cache).
- Order of execution to catch problems early: dry run on 5 dev datasets for every system → fix → run dev full (for sanity) → freeze → test split once.
- Everything cached by `(system, config hash, dataset hash, seed, repeat, code version)`; `--force` disallowed on test split unless a documented failure occurred.
- Record git commit hash, package versions, model names/versions, dates, hardware in `outputs/eval/run_manifest.json`.

---

## 6. Module layout (`src/veridata/evaluation/`)

```
systems/llm_only.py         # S1a/S1b adapters (reuse Phase 1 baselines/sandbox), output parser, pair canonicalizer
systems/veridata_variants.py# S2, S3, A1-A6 adapters (wrap Phase 4 adapters)
experiments/e1_main.py  e2_ablation.py  e3_calibration.py  e4_numbers.py  e5_real.py  e6_selection.py  e7_chat.py  e8_robustness.py
stats_utils.py              # bootstrap CIs, paired tests, aggregation helpers
independent_recompute.py    # plain scipy/pandas recomputation for number checks (no VeriData imports from stats/)
tables.py                   # markdown/LaTeX tables
figures.py                  # all final figures (consistent style)
run_all.py                  # orchestrates experiments with caching; prints plan and cost estimate first
```
CLI: `veridata eval plan` (prints runs and cost estimate), `veridata eval run --experiment e1 --split dev|test`, `veridata eval tables`, `veridata eval figures`, `veridata final-report`.

`independent_recompute.py` must not import `veridata.stats` (lint test) so E4 is not circular.

---

## 7. Tests for the evaluation code itself

- Systems adapters on tiny fixtures with scripted LLM outputs: parsing, canonicalization, unknown-column discard, direction encoding.
- Metric functions on hand-computed examples (reuse Phase 4 tests plus LLM-style outputs: duplicates, reversed pairs, unknown columns).
- Bootstrap/paired-test utilities against known results.
- Permutation/noise-column generators: seeded, produce expected shapes, truly null (empirical correlation ≈ 0).
- Split-half and stability routines: deterministic with seed.
- Independent recomputation vs VeriData outputs on fixtures (agree) and vs a deliberately corrupted output (disagree).
- Cost-guard test: budget exceeded ⇒ graceful stop and resume.
- End-to-end smoke: `veridata eval run --experiment e1 --suite smoke --split dev` with FakeLLM completes and produces tables/figures.

---

## 8. Analysis and reporting requirements

- **Results tables** auto-generated (no manual copying): main metrics with CIs; ablation table; calibration table; number-correctness table; real-dataset tables; chat table.
- **Figures** (consistent style, captions with n and setup): list in E1-E8.
- **Narrative rules:** report effect sizes with CIs; avoid claiming significance from tiny datasets counts; note where the LLM-only baseline performs well; include negative/unexpected results; separate pre-registered analyses from exploratory ones (label exploratory clearly).
- **Threats to validity section:** synthetic-data realism; generator–test coupling (designed by the same people; mitigated via diverse shapes, held-out seeds, real data experiments); matching rule choices; LLM baseline strength and prompt sensitivity; single-model dependence; contamination on public datasets; BH dependence; limited number of real datasets; no causal claims; independence assumption.

---

## 9. Final deliverables

### 9.1 Code and reproducibility
- Clean repo, tagged release `v1.0`; `make setup && make test && make eval-all-dev` reproduces dev results; `make final-report` rebuilds tables/figures from cached outputs.
- `README.md`: what it is, quick start (CLI, app), architecture diagram, results highlights (with exact numbers from the tables), limitations, license, citation block.
- `docs/architecture.md` (component diagram, data flow, contracts), `docs/user_guide.md` (upload → findings → chat; interpreting q-values and effect sizes in plain words), `docs/stats_methods.md` (from Phase 3), `docs/limitations.md`, `docs/privacy.md`, `docs/decisions.md` (all DECISIONs and deviations), `docs/eval_protocol.md` (frozen) + results addendum.
- Environment lock (`requirements.txt` pinned; optionally `uv.lock`/conda export); optional Dockerfile.
- Data: synthetic suites regenerable from seeds; Kaggle datasets documented with download steps (do not redistribute if license forbids).

### 9.2 Final report / paper (`final_report/FINAL_REPORT.md`, optionally PDF via pandoc)
Sections: Abstract; 1 Introduction (problem: LLM analysts report chance patterns; contribution); 2 Related work (brief: multiple testing, automated data science/AutoML-EDA tools, LLM data analysis agents; cite BH 1995, Benjamini-Yekutieli 2001, Cohen 1988, Cramér, Hedges & Olkin, Bergsma 2013 for bias-corrected V, Welch 1947, Mann-Whitney; add actual references with verified citations; do not fabricate references: verify each); 3 System design (phases 1-6, principles P1-P10, contracts); 4 Methods (hypothesis generation without peeking, test library & selection rules, validation, ledger/session FDR, number verification); 5 Evaluation setup (protocol, systems, suites, metrics); 6 Results (E1-E8); 7 Discussion (where it works/fails, cost, UX); 8 Limitations & ethics (misuse risk: p-hacking by repeated chat questions mitigated by ledger; data privacy; overreliance); 9 Conclusion & future work (adjusted tests, interactions, causal discovery, time series, online FDR); Appendices (full tables, prompts, configs).

### 9.3 Presentation and demo
- Slide deck (10-12 slides) built from final figures; demo per Phase 7 with real numbers filled in.
- Demo video (3-5 min).
- One-page poster/summary (optional).

### 9.4 Course submission package
`submission/` folder: report, code zip (or repo link + tag), README, results tables/figures, demo video link, instructions to run, AI-assistance disclosure statement (document how Claude Code/Antigravity were used and how outputs were verified, per course policy).

---

## 10. Milestones

| ID | Work | Est. |
|---|---|---|
| P8-M0 | Draft & freeze protocol; reference findings written; compute/cost plan; tag | 1 d |
| P8-M1 | LLM-only systems (S1a/S1b), parser, canonicalizer, budgets, fairness review | 2 d |
| P8-M2 | Variants adapters (S2, S3, A1-A6), independent recompute module | 1 d |
| P8-M3 | E1/E2 code + dev-split dry runs; fix issues | 1.5 d |
| P8-M4 | E4, E6 code; E3 summary | 1 d |
| P8-M5 | E5 real-data experiments (permutation, noise, split-half, stability, qualitative sheets) | 2 d |
| P8-M6 | E7 chat evaluation + human rating sheets | 1.5 d |
| P8-M7 | E8 robustness | 0.5 d |
| P8-M8 | **Test-split runs** (E1-E8), tables/figures generation | 1.5 d (mostly compute) |
| P8-M9 | Analysis, final report writing, README/docs, threats to validity | 3 d |
| P8-M10 | Demo finalization with real numbers, video, slides, submission package, release tag | 1.5 d |

---

## 11. Acceptance criteria

- [ ] Protocol frozen (tag) before any test-split run; deviations documented.
- [ ] All experiments E1-E8 have code, tests, cached outputs, tables, and figures; the Phase 4 dev-split sanity targets were met beforehand.
- [ ] E1 reports FDR, recall, precision, FWER on null datasets with bootstrap CIs for S1a, S1b, S2, S3; paired comparisons reported; the primary hypothesis is evaluated with an explicit verdict (supported / partially / not supported).
- [ ] E2 ablation table includes every variant in Section 3 and a note on which components help.
- [ ] E4: VeriData verified-number rate = 100% on both verifiers; LLM-only rate reported with the manual audit.
- [ ] E5: reference-finding recovery, permutation and noise-column false-positive rates, split-half replication, and stability reported for ≥ 3 real datasets.
- [ ] E7: chat metrics reported against the baseline; hallucinated-number rate for VeriData = 0.
- [ ] Everything regenerates from cache with `make final-report`; run manifest recorded.
- [ ] Final report complete with threats to validity and honest limitations; references verified.
- [ ] README, docs, user guide, architecture, privacy, limitations complete; release tagged; demo video and slides done; AI-assistance disclosure included.

---

## 12. Pitfalls

1. **Tuning on the test split** (even informally). Freeze, run once.
2. **Weak or unfair LLM baseline.** A straw-man baseline invalidates the main claim; give it code execution, a good prompt, and report both modes; have a teammate review the prompt.
3. **Circular number checks.** E4 must recompute independently of VeriData's own code.
4. **Overstating real-data results** where no ground truth exists; use permutation/noise/replication framing and state limits.
5. **Cherry-picking datasets or metrics** after seeing results. Everything pre-registered; exploratory analyses labeled.
6. **Treating repeats as independent datasets** in statistical comparisons.
7. **Forgetting cost control** with LLM runs; caching and a hard budget are mandatory.
8. **Fabricated references** in the final report. Verify every citation by hand; use web search or primary sources.
9. **Leaving the demo numbers stale.** Insert numbers from the generated tables via script (`final_report/numbers.json`), not by retyping.
10. **Late discovery of a pipeline bug.** The dev-split dry run on all systems before freezing is non-negotiable.

---

## 13. Human tasks

- Write reference findings before running E5; review the oracle table (E6).
- Review the LLM-only prompts for fairness; sign the protocol freeze.
- Do the blind qualitative annotation (E5) and chat ratings (E7); audit 30 LLM claims (E4).
- Write/edit the final report's discussion and conclusions; verify references.
- Provide API budget and approve cost caps; run the final test-split pass.
- Record the demo video; assemble the submission package; complete the AI-assistance disclosure.
