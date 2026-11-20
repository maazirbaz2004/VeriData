# VeriData — MASTER PLAN (Phases 2-8)

> **Read this file first, before any phase file.** It holds the non-negotiable principles, the phase map, the shared data contracts, global config, conventions, and definitions that every phase file relies on.
> Phase 1 (profiling, cleaning, EDA, LLM data-quality comparison) is **already done**. Its output contract is in Section 5.1. Do not modify Phase 1 behavior unless a phase file explicitly says so.
> **Package name:** this plan uses `veridata` (`src/veridata/`). If Phase 1 was built under another package name (e.g. `ads`), do a project-wide rename first (`git mv`, imports, CLI entry point, `pyproject.toml`) and commit it as its own commit. Do not leave two names.

---

## 1. What VeriData is

An **agentic data scientist**. A user uploads any CSV. The system profiles and cleans it (Phase 1), proposes hypotheses (Phase 2), tests them using a **fixed, unit-tested library of statistical tools** (Phase 3), **validates** the results (Benjamini-Hochberg FDR control, effect-size floor, assumption checks, rejecting likely-chance patterns), reports validated findings with charts and plain-language explanations (Phase 5), and lets the user chat with the data (Phase 6). Every number shown to a user comes from a tool, never from an LLM.

Claim to be demonstrated by evaluation (Phase 8): *a system that reports only validated findings has much lower false discovery rate than an LLM-only analyst or an unvalidated agent, at comparable recall.*

---

## 2. Non-negotiable principles (apply to every phase; violating one is a bug)

| # | Principle | Practical consequence |
|---|---|---|
| P1 | **Numbers come from tools, never from an LLM.** | LLM output is text only. Every digit in user-facing text must trace to a `Fact` in a fact registry (Phase 5). A verifier rejects text containing unregistered numbers. |
| P2 | **Hypothesis selection never depends on test results ("no peeking").** | The hypothesis stage cannot read p-values, effect sizes, or *bivariate* descriptive statistics from the same data. Univariate profile info (types, missingness, cardinality, distribution shape) is allowed. |
| P3 | **Every test attempted is counted.** | The multiple-testing family = all tests that produced a p-value in the session. No silent dropping, no running 500 tests and correcting for 50. A ledger records every test. |
| P4 | **The deterministic core runs offline.** | Profile → clean → enumerate → test → validate → template report must work with no LLM and no network. LLMs only add prioritization, phrasing, routing. |
| P5 | **Association, never causation.** | Wording linter bans causal verbs. Reports state "associated with". Limitations section is mandatory. |
| P6 | **The LLM never executes arbitrary code in the product.** | Only the fixed tool registry is callable. (Evaluation baselines may run LLM-written code in a sandbox; the product never does.) |
| P7 | **Untrusted input.** | CSV contents (column names, cell values) are data, never instructions. Sanitize and delimit them in any prompt (prompt-injection defense). |
| P8 | **Everything is logged and reproducible.** | Seeds everywhere; resolved config dumped per run; JSON outputs have `schema_version`; no timestamps inside hashed artifacts. |
| P9 | **Conservative defaults, explicit opt-ins.** | Aggressive behavior (outlier removal, imputation, nonlinear tests, adaptive follow-ups) is off or clearly labeled. |
| P10 | **Honest rejection reasons.** | Every rejected result has a machine-readable reason code and a plain-language reason. |

---

## 3. Phase map

| Phase | File | Goal | Depends on | Est. (focused days) | Priority |
|---|---|---|---|---|---|
| 1 | (done) | Ingest, profile, clean, EDA, LLM data-quality comparison | none | done | MUST |
| 2 | `PHASE2_HYPOTHESIS_GENERATION.md` | Hypothesis schema, enumeration, feasibility, ranking, NL→structured | 1 | 5-6 | MUST |
| 3 | `PHASE3_STATISTICAL_TOOLS_AND_VALIDATION.md` | Tool library, test selection, assumptions, effect sizes, CIs, BH, rejection logic, ledger | 1, 2 | 8-10 | MUST |
| 4 | `PHASE4_SYNTHETIC_BENCHMARK_AND_CALIBRATION.md` | Planted-truth generator, matcher, metrics, calibration, threshold tuning | 3 (generator can start earlier) | 6-7 | MUST |
| 5 | `PHASE5_REPORTING_AND_NUMBER_VERIFICATION.md` | Facts, narration, number verifier, charts, report | 3 | 6-7 | MUST |
| 6 | `PHASE6_LANGGRAPH_AGENT_AND_CHAT.md` | LangGraph batch + chat graphs, tool registry, router, ledger, follow-ups | 2, 3, 5 | 8-10 | MUST (chat core), SHOULD (extras) |
| 7 | `PHASE7_UI_AND_DEMO.md` | Streamlit app, offline demo mode, demo script | 5, 6 | 4-5 | MUST (basic), SHOULD (polish) |
| 8 | `PHASE8_EVALUATION_AND_FINAL_DELIVERABLES.md` | Full benchmark vs LLM-only, ablations, Kaggle runs, chat eval, final report | 4, 5, 6 (7 for demo) | 8-10 | MUST |

Total ≈ 45-55 focused days if everything is built. **Section 12 gives the cut list** if time is short. Parallelism: the Phase 4 *generator* and *matcher* can be built while Phase 3 is in progress (it only needs the output schema). Phase 5 charts can start once Phase 3 result schemas are frozen.

Dependency picture:

```
Phase1 ──► Phase2 ──► Phase3 ──┬──► Phase4 ──────────────┐
                               ├──► Phase5 ──┐           ├──► Phase8
                               └─────────────┴──► Phase6 ─┤
                                                  └─► Phase7 ┘
```

Each phase file ends with a **handoff contract** and **acceptance criteria**. A phase is done only when all its acceptance checkboxes pass.

---

## 4. Repository layout (Phase 1 files already exist; additions marked NEW)

```
veridata/
├── README.md
├── CLAUDE.md                      # NEW: agent rules (Section 9.6). Mirror to AGENTS.md for Antigravity.
├── pyproject.toml  requirements.txt  Makefile  .env.example  .gitignore
├── configs/
│   ├── default.yaml               # extended in Section 6
│   ├── datasets/*.yaml            # Phase 1
│   ├── benchmark/                 # NEW (Phase 4): grid definitions, dev/test seed lists
│   └── prompts/                   # NEW: all LLM prompts, versioned text files (never inline)
├── data/  raw/ cleaned/ synthetic/ ...            # Phase 1
├── src/veridata/
│   ├── (Phase 1 modules: config, schemas, ingestion, type_inference, profiling, cleaning/, eda/, scaling, insights, pipeline, synthetic/, baselines/, comparison/)
│   ├── contracts/                 # NEW: shared pydantic models (Section 5), one file per concept
│   │   ├── hypothesis.py  results.py  validation.py  facts.py  ledger.py  findings.py  common.py
│   ├── hypotheses/                # NEW (Phase 2)
│   │   ├── enumerate.py  feasibility.py  ranking.py  llm_proposer.py  nl_parser.py  dedupe.py  generator.py
│   ├── stats/                     # NEW (Phase 3): the fixed tool library
│   │   ├── registry.py  selection.py  assumptions.py  effect_sizes.py  intervals.py
│   │   ├── tests_numeric_binary.py  tests_numeric_categorical.py  tests_numeric_numeric.py  tests_categorical.py
│   │   ├── adjusted.py (optional)  runner.py  posthoc.py (optional)
│   ├── validation/                # NEW (Phase 3)
│   │   ├── correction.py  rules.py  validator.py  ledger.py
│   ├── benchmark/                 # NEW (Phase 4)
│   │   ├── generator.py  dag.py  truth.py  matcher.py  metrics.py  runner.py  calibration.py  tuning.py
│   ├── reporting/                 # NEW (Phase 5)
│   │   ├── facts.py  narration.py  templates.py  number_verifier.py  language_lint.py
│   │   ├── charts/  (scatter.py groups.py categorical.py forest.py bh_plot.py volcano.py style.py)
│   │   ├── report_builder.py  html.py
│   ├── agent/                     # NEW (Phase 6)
│   │   ├── state.py  graph_batch.py  graph_chat.py  nodes/  router.py  tools.py  followups.py
│   │   ├── memory.py  guardrails.py  llm.py (provider interface)  fake_llm.py  checkpoint.py
│   ├── evaluation/                # NEW (Phase 8)
│   │   ├── systems/ (llm_only.py veridata_full.py veridata_nocorrection.py ablations.py)
│   │   ├── experiments/ (e1_main.py e2_test_selection.py e3_calibration.py e4_numbers.py e5_real.py e6_chat.py e7_robustness.py)
│   │   ├── stats_utils.py  tables.py  figures.py
│   └── app/                       # NEW (Phase 7): Streamlit
│       ├── main.py  pages/  components/  session.py
├── scripts/                       # CLI helpers per phase
├── tests/                         # mirrors src structure; one folder per package
├── docs/  decisions.md  contract.md  eval_protocol.md  architecture.md  user_guide.md  limitations.md
├── outputs/                       # gitignored except final_report
└── final_report/
```

---

## 5. Shared data contracts (Pydantic v2; all JSON-serializable; every top-level artifact carries `schema_version: "1.0"`)

These are the **single source of truth**. Phase files add detail but must not contradict. Put them in `src/veridata/contracts/`.

### 5.1 Phase 1 outputs consumed by later phases (already produced)

- `data/cleaned/<name>_cleaned.csv`: conservative cleaned frame (NaN preserved).
- `outputs/<name>/column_schema.json`: `{col: {semantic_type, role, n_unique, pct_missing}}` with `role ∈ {feature, target_candidate, id, excluded}`.
- `outputs/<name>/profile.json` (`DataProfile`), `cleaning_log.json`, `insights.json`.
- API: `veridata.pipeline.run_phase1(...)`, `profile_dataset`, `clean_dataset`.
- `SemanticType` enum: `numeric_continuous, numeric_discrete, binary, categorical_nominal, categorical_ordinal, datetime, id_like, free_text, constant, unknown`.

### 5.2 Hypothesis (Phase 2 produces)

```python
class RelationshipType(str, Enum):
    NUM_BINARY       = "numeric_vs_binary"        # two-group difference in a numeric variable
    NUM_CATEGORICAL  = "numeric_vs_categorical"   # k>2 group differences
    NUM_NUM          = "numeric_vs_numeric"       # association (monotonic/linear)
    CAT_CAT          = "categorical_vs_categorical"  # includes binary-binary (2x2)
    NUM_NUM_NONLINEAR= "numeric_vs_numeric_nonlinear"  # OPTIONAL, off by default
    # Reserved for later / stretch: ADJUSTED_ASSOCIATION

class Direction(str, Enum):
    ANY="any"; POSITIVE="positive"; NEGATIVE="negative"; A_GREATER="a_greater"; B_GREATER="b_greater"

class Hypothesis(BaseModel):
    schema_version: str = "1.0"
    id: str                      # stable hash of (sorted columns, relationship_type, covariates); NOT a counter
    column_a: str                # for NUM_BINARY/NUM_CATEGORICAL: column_a = the numeric outcome, column_b = the grouping column
    column_b: str
    relationship: RelationshipType
    expected_direction: Direction = Direction.ANY   # two-sided tests always; direction is only a stated expectation
    covariates: list[str] = []   # reserved for adjusted tests (stretch)
    source: Literal["enumerated","llm","user","followup"]
    rationale: str = ""          # plain-text why (LLM or rule-generated). Never contains numbers from data.
    feasibility: FeasibilityReport
    priority_score: float = 0.0  # ordering ONLY; never gates membership in the family
    priority_components: dict[str,float] = {}
    created_stage: Literal["batch","chat"]
    status: Literal["proposed","queued","tested","skipped_infeasible","error"] = "proposed"

class FeasibilityReport(BaseModel):
    feasible: bool
    reasons: list[str]            # e.g. "group 'X' has n=3 < min_group_n"
    n_pairwise_complete: int
    group_sizes: dict[str,int] | None
    min_expected_count: float | None
```

Direction convention: tests are **always two-sided**. `expected_direction` only affects narration ("as hypothesized" / "opposite to expectation") and, in evaluation, the matching rule.

### 5.3 Test result (Phase 3 produces)

```python
class AssumptionCheck(BaseModel):
    name: str                    # "normality_group_<label>", "equal_variance", "expected_counts", "min_group_size", "independence_note", "linearity", "outlier_influence"
    method: str                  # "shapiro", "levene_median", "skew_kurtosis_rule", ...
    statistic: float | None
    p_value: float | None
    passed: bool
    severity: Literal["info","warning","violation"]
    detail: str

class EffectSize(BaseModel):
    name: str                    # "hedges_g","rank_biserial","pearson_r","spearman_rho","eta_squared","epsilon_squared","cramers_v_bc","phi","odds_ratio"
    value: float
    ci_low: float | None
    ci_high: float | None
    ci_method: str | None        # "analytic_hedges_olkin","bootstrap_bca","fisher_z","woolf",...
    magnitude: Literal["negligible","small","medium","large"]
    comparable_value: float | None   # standardized |value| used for the effect-size floor (Section 8)

class TestResult(BaseModel):
    schema_version: str = "1.0"
    hypothesis_id: str
    status: Literal["ok","skipped_infeasible","error"]
    test_name: str               # "welch_t","mann_whitney_u","welch_anova","kruskal_wallis","pearson","spearman","chi_square","fisher_exact","monte_carlo_chi_square"
    test_selection_reason: str   # human-readable; also machine reasons in selection_trace
    selection_trace: list[dict]  # ordered decision steps: {"rule":..., "input":..., "outcome":...}
    fallback_used: bool
    n_used: int
    group_sizes: dict[str,int] | None
    statistic: float | None
    df: float | list[float] | None
    p_value: float | None        # two-sided, raw
    effect: EffectSize | None
    descriptives: dict           # group means/medians/sds, correlation coeff, contingency table, etc. (all numbers here become Facts)
    direction_observed: Direction | None   # computed, e.g. A_GREATER, POSITIVE
    assumptions: list[AssumptionCheck]
    warnings: list[str]
    runtime_ms: float
    seed: int | None
    error: str | None
```

### 5.4 Validation (Phase 3 produces)

```python
class RejectionReason(str, Enum):
    NOT_SIGNIFICANT_AFTER_CORRECTION = "not_significant_after_correction"
    EFFECT_BELOW_THRESHOLD  = "effect_below_threshold"
    ASSUMPTION_VIOLATED     = "assumption_violated_no_fallback"
    INSUFFICIENT_DATA       = "insufficient_data"
    DEGENERATE_DATA         = "degenerate_data"      # constant after NA removal, zero variance
    TEST_ERROR              = "test_error"
    TRIVIAL_RELATIONSHIP    = "trivial_relationship" # deterministic/derived (|r|>=0.999, V>=0.99): reported separately, not as discovery
    UNSTABLE_CI             = "ci_includes_zero"     # only in strict mode

class ValidationDecision(BaseModel):
    hypothesis_id: str
    p_raw: float | None
    q_value: float | None        # BH-adjusted
    family_id: str
    family_size: int             # m used in this correction
    rank_in_family: int | None
    accepted: bool
    reasons: list[RejectionReason]      # empty if accepted
    reason_text: str             # plain language
    flags: list[str]             # e.g. "possible_derived_column","small_n","assumption_warning","heavy_outliers"
    would_pass_without_correction: bool  # raw p<alpha (used for "what naive analysis would claim")
    would_pass_without_effect_floor: bool
```

### 5.5 Finding (joined view, used by reporting/agent/evaluation)

```python
class Finding(BaseModel):
    hypothesis: Hypothesis
    test: TestResult
    decision: ValidationDecision
    facts: list[Fact]            # Phase 5 fills; empty before
```

### 5.6 Ledger (Phase 3 defines; Phase 6 uses across a session)

```python
class LedgerEntry(BaseModel):
    seq: int
    hypothesis_hash: str
    stage: Literal["batch","chat"]
    test: TestResult
    added_at_utc: str            # stored in ledger only, never inside hashed artifacts
class Ledger(BaseModel):
    dataset_sha256: str
    alpha: float
    entries: list[LedgerEntry]
```

Ledger invariants: append-only; a hypothesis with the same `id` is **not** re-added (cached result returned); BH family = all entries with `status=="ok"` and non-null p.

### 5.7 Fact (Phase 5 produces; the only source of numbers in text)

```python
class Fact(BaseModel):
    key: str                     # "n_used","p_raw","q_value","effect_value","ci_low","mean_group_Yes",...
    value: float | int | str
    display: str                 # exactly what may appear in text, e.g. "0.42", "<0.001", "1,338", "12.3%"
    unit: str | None
    source: str                  # "TestResult.effect.value" etc. (traceability)
```

---

## 6. Global config additions (`configs/default.yaml`)

```yaml
stats:
  alpha: 0.05                 # FDR level q
  correction: bh              # bh | by | holm | bonferroni | none  (none/others for ablation only)
  two_sided: true
  min_n_pairwise: 20          # below -> skipped_infeasible
  min_group_n: 8              # per group in group comparisons
  min_expected_count_chi2: 5
  normality_n_max: 5000       # shapiro limit; above -> skew/kurtosis rule
  large_n_clt: 50             # per-group n at/above which Welch is allowed despite non-normality (unless extreme skew)
  extreme_skew: 2.0
  bootstrap_resamples: 2000
  bootstrap_resamples_benchmark: 500
  permutation_resamples: 9999
  seed: 20260101
effect_floor:                  # standardized minimum |effect| to accept (Cohen "small")
  cohens_d: 0.20
  rank_biserial: 0.10
  correlation: 0.10
  eta_squared: 0.01
  epsilon_squared: 0.01
  cramers_v_df1: 0.10          # scaled by 1/sqrt(df*) for larger tables (see Phase 3)
  enabled: true
hypotheses:
  mode: exhaustive             # exhaustive | target_focused | llm_prioritized
  target: null
  max_tests: 3000              # hard cap; exceeding triggers outcome-independent pruning (Phase 2 Section 6)
  max_levels_categorical: 20
  enable_nonlinear: false
  llm_proposals: true
llm:
  provider: anthropic
  model: claude-sonnet-5-5     # configurable; check current model names in Anthropic docs
  temperature: 0.0
  max_tokens: 2000
  cache_dir: .cache/llm
  retries: 2
reporting:
  narration: llm_slots         # llm_slots | template_only
  max_findings_in_report: 30
  charts_dpi: 150
agent:
  checkpoint: sqlite           # memory | sqlite
  max_followups: 3
  max_tool_calls_per_turn: 4
```

Config precedence: `default.yaml` < dataset YAML < CLI flags < programmatic overrides. Resolved config is dumped next to every run's outputs.

---

## 7. Statistical conventions (apply everywhere; Phase 3 implements)

- All tests two-sided. Test family: **BH at q = 0.05** over all tests that produced a p-value in the session ledger.
- Effect-size floor: accept only if standardized |effect| ≥ configured "small" threshold. Rationale: with large n trivially small effects become "significant"; the floor demands practical relevance. Applied **after** BH (filtering on a data-independent threshold after BH only removes findings, so FDR control is preserved, since removing discoveries cannot increase FDP in expectation... note: it can only decrease the number of false and true discoveries; document the caveat in `docs/limitations.md`).
- Missing data: pairwise complete cases per test; n_used recorded.
- Rows assumed independent (cannot be verified). Heuristic warning if a column with many repeated values behaves like a grouping ID (clustering risk).
- Tests skipped for infeasibility (n too small etc.) are **not** in the family (no p-value) but are listed in the report. This is data-adaptive only through sample-size, not through outcome; document in `docs/decisions.md`.
- BH validity: assumes independence or positive dependence (PRDS). Pairwise tests on shared columns are dependent. Provide BY as a conservative option and **empirically check FDR on correlated-null data in Phase 4.**

---

## 8. Definitions (used identically in all phases and the final report)

- **Family:** the set of tests over which one BH correction is applied (all tests with a p-value in the session ledger).
- **Discovery / reported finding:** `ValidationDecision.accepted == True`.
- **Planted/true dependence (benchmark):** a column pair that is statistically dependent *by construction*, including induced dependence through shared causes (Phase 4 Section 4).
- **True discovery:** reported finding whose column pair is truly dependent and whose observed direction agrees with truth (matching rule: Phase 4 Section 6).
- **False discovery:** reported finding for a truly independent pair or with wrong direction.
- **FDP / FDR:** FDP = false / max(1, reported); FDR = mean FDP across datasets.
- **Recall (power):** true discoveries / truly dependent pairs that were testable (feasible).
- **Naive analysis:** same tests, raw p < alpha, no correction, no effect floor.

---

## 9. Conventions for the implementing agent

### 9.1 Coding standards
Python 3.11+, type hints everywhere, docstrings on public functions (state inputs, outputs, edge cases), `ruff` + `black`, no wildcard imports, no global mutable state, no hard-coded column names in library code, no `print` (use `logging`), pure functions where possible, side effects only in designated I/O functions.

### 9.2 Testing
`pytest`; one test module per source module; tolerance-based numeric asserts (`pytest.approx`). Statistical functions are validated against reference implementations (scipy/statsmodels) **and** hand-computed values. Seeded randomness only. Mark slow tests `@pytest.mark.slow`; `make test` runs fast tests, `make test-all` runs all. Target ≥ 80% line coverage on `stats/`, `validation/`, `hypotheses/`, `reporting/number_verifier.py`, `benchmark/matcher.py`, `benchmark/metrics.py`; lower elsewhere is acceptable.

### 9.3 Errors
Custom exception hierarchy in `veridata/errors.py`: `VeriDataError` → `DataError`, `ConfigError`, `HypothesisError`, `StatsError`, `ValidationError`, `ReportingError`, `AgentError`, `LLMError`. User-facing code catches and converts to friendly messages; library code raises specific errors with context. No bare `except:`.

### 9.4 LLM client interface (`agent/llm.py`, used by Phases 2, 5, 6, 8)

```python
class LLMClient(Protocol):
    def structured(self, *, system: str, user: str, schema: type[BaseModel], temperature: float = 0.0, max_tokens: int = 2000, cache_key: str | None = None) -> BaseModel: ...
    def text(self, *, system: str, user: str, temperature: float = 0.0, max_tokens: int = 1500, cache_key: str | None = None) -> str: ...
```
- Anthropic implementation: structured output via **forced tool call** whose `input_schema = schema.model_json_schema()`; validate the returned input with Pydantic; on validation failure retry up to `llm.retries` with the validation error appended; then raise `LLMError`.
- Disk cache keyed by hash(model, system, user, schema name, temperature). Re-runs cost nothing. `--no-cache` flag to bypass.
- `FakeLLM(responses: dict | callable)` for tests: deterministic, offline. **All agent and reporting tests must run against FakeLLM.**
- Log tokens, latency, cost estimate per call to `outputs/<run>/llm_calls.jsonl`.
- Prompts live in `configs/prompts/*.txt` with a version header; the version is recorded in outputs.
- API key from env only; if missing, `NullLLM` raises `LLMUnavailable` which every caller handles by falling back to deterministic behavior (P4).

### 9.5 Makefile targets (extend Phase 1's)
`setup, lint, test, test-all, run-batch DATASET=..., bench-gen, bench-run, bench-eval, report DATASET=..., app, eval-all, final-report`.

### 9.6 `CLAUDE.md` (also copy to `AGENTS.md` / Antigravity workspace rules)
Contents to write verbatim at repo root:
1. Read `00_MASTER_PLAN.md` and the current phase file before coding. Implement milestones in order. Run `make test` after each milestone and commit.
2. Never let an LLM produce or alter a number shown to the user. Never call an LLM inside `stats/`, `validation/`, `benchmark/` (generator/matcher/metrics) or `reporting/number_verifier.py`.
3. Do not read test results inside `hypotheses/`. Do not drop hypotheses from the family for outcome-dependent reasons.
4. Do not change shared contracts (`contracts/`) without bumping `schema_version` and updating `docs/contract.md` and the master plan.
5. Every new statistical function gets a test against scipy/statsmodels and a hand-computed case.
6. Record every non-obvious choice in `docs/decisions.md`.
7. Ask the human only for the items listed under "Human tasks" in the phase file.
8. When unsure, choose the conservative option and record it.

### 9.7 Git
Trunk-based; one commit per milestone with message `phaseN-Mx: summary`; tag `phaseN-done` when acceptance criteria pass.

---

## 10. Human tasks across all phases (the AI cannot do these)

- Provide `ANTHROPIC_API_KEY` (or approve another provider).
- Verify at least 20 hypothesis-NL parses and 20 router decisions by hand (Phases 2, 6) to create small gold sets.
- Write down **reference findings** for each real dataset *before* running evaluation (Phase 8 pre-registration).
- Review all charts for readability (Phase 5) and the UI (Phase 7).
- Rehearse the demo; record a backup video.
- Make final scoping decisions with the cut list (Section 12).

---

## 11. Project-level risks

1. **Evaluation design is the project.** If the benchmark or matching rule is sloppy, results are meaningless. Phase 4 and `docs/eval_protocol.md` must be finished and frozen before running Phase 8.
2. **Double-dipping.** Using EDA correlations to choose hypotheses then correcting only for the chosen ones invalidates FDR. P2/P3 exist to prevent this.
3. **Dependence between tests** can inflate FDR above 5%. Measure it (Phase 4), report it, offer BY.
4. **AI-generated code looks right but is subtly wrong** in statistics. Every stats function needs reference tests; read the selection traces and charts yourself.
5. **LLM cost/rate limits** in Phase 8 (many runs). Cache everything; use small models for baselines where acceptable; budget in advance.
6. **Scope explosion.** Use the cut list.
7. **Prompt injection through CSVs** in a demo where the audience uploads files. Guardrails in Phase 6 are mandatory.

---

## 12. Cut list (if time runs short, drop in this order; never drop MUST items)

1. STRETCH: online FDR (LOND), adjusted/regression tool, post-hoc tests, nonlinear tests, PDF export, Docker.
2. SHOULD→drop: Mode-B (code-exec) LLM baseline variants beyond one; extra benchmark grid cells (keep ~60 datasets); E7 robustness experiment; Kaggle datasets 4-5.
3. Reduce UI to: upload, findings table, charts, chat box, report download.
4. Reduce chat intents to: describe, compare_groups, correlate, associate_categories, list_findings, explain_rejection, suggest_next.
5. Minimum viable project: Phases 2-3 (exhaustive enumeration only), Phase 4 (core grid), Phase 5 (template narration + verifier + core charts), Phase 6 (batch graph + simple chat), Phase 8 (E1 + E5 + ablation), basic Streamlit.

---

## 13. Suggested calendar (focused effort; adjust to team size)

| Week | Work |
|---|---|
| 1 | Phase 2 + start Phase 3 tool library; start Phase 4 generator |
| 2 | Phase 3 finish (selection, effect sizes, BH, validator, ledger) |
| 3 | Phase 4 (matcher, metrics, calibration, tuning) ; start Phase 5 |
| 4 | Phase 5 finish; start Phase 6 batch graph |
| 5 | Phase 6 chat graph, router, follow-ups |
| 6 | Phase 7 UI; Phase 8 experiment code |
| 7 | Phase 8 runs; analysis; final report; demo rehearsal |
