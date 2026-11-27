# VeriData Architecture (`docs/architecture.md`)

VeriData is an end-to-end **agentic data scientist** organized into eight phases around a strict separation between **deterministic statistical computation** and **optional LLM-assisted narration, routing, and prioritization**.

---

## 1. Core Architectural Invariants (P1–P10)

1. **P1 — Numbers from tools only:** Every numeric value shown to users is registered as a `Fact` inside `FactRegistry` (`src/veridata/reporting/facts.py`) and enforced by `verify_text()` (`src/veridata/reporting/number_verifier.py`).
2. **P2 — Zero-peeking hypothesis generation:** `src/veridata/hypotheses/` inspects only univariate metadata and column types (`safe_profile.py`), never p-values, effect sizes, or bivariate correlations.
3. **P3 — Complete family accounting:** Every test producing a p-value in batch or chat enters the append-only `SessionLedger` (`src/veridata/validation/ledger.py`), and Benjamini-Hochberg (BH) adjustment runs over the full family.
4. **P4 — Offline deterministic core:** Ingestion, cleaning, hypothesis enumeration, statistical testing, validation, template reports, and rule-based chat run completely offline with `NullLLM`.
5. **P5 — Association, never causation:** `lint_text()` (`src/veridata/reporting/language_lint.py`) blocks causal verbs and overclaiming language across findings and chat responses.
6. **P6 — No arbitrary code execution in the product:** The interactive product exposes only the fixed `ToolRegistry` (`src/veridata/agent/tools.py`). (Subprocess code execution in `evaluation/sandbox.py` exists strictly for benchmarking the `S1b` LLM baseline.)

---

## 2. System Dataflow (Phases 1–8)

```
Raw CSV
  │
  ▼ [Phase 1: Ingestion, Type Inference, 12-Step Conservative Clean]
  │  -> df_clean_conservative, column_schema.json, profile.json, cleaning_log.json
  │
  ▼ [Phase 2: Outcome-Blind Hypothesis Generation]
  │  -> HypothesisSet (pairwise enumeration + feasibility + optional LLM proposals)
  │
  ▼ [Phase 3: Fixed Statistical Tool Library & Two-Stage Runner]
  │  -> Stage A: assumption-aware test selection + p_value + point effect size
  │  -> Stage B: bootstrap CIs + sensitivity checks (candidates only)
  │  -> SessionLedger (append-only, deduplicated by hypothesis_id)
  │
  ▼ [Phase 3: Validation Layer]
  │  -> BH / BY / Holm / Bonferroni correction + Cohen small effect floor
  │  -> Assumption gate + trivial/derived relationship gate (|r| >= 0.999)
  │  -> ValidationDecision + Finding records
  │
  ▼ [Phase 5: FactRegistry, Narration, Number Verifier, Charts & Reports]
  │  -> report.md, report.html, findings.csv, 150-DPI Okabe-Ito charts
  │
  ├─► [Phase 6 & 7: LangGraph Batch & Chat Agent + Streamlit Dashboard]
  │    -> Multi-turn chat updates SessionLedger and re-evaluates BH family
  │
  └─► [Phase 4 & 8: Synthetic Benchmark, Calibration & Full Evaluation]
       -> S3 vs S2 vs S1a/S1b vs A1-A6, E1-E8, tables, figures, FINAL_REPORT
```

---

## 3. Shared Data Contracts (`src/veridata/contracts/`, `schema_version = "1.0"`)

- `Hypothesis` & `FeasibilityReport` (`contracts/hypothesis.py`): Stable SHA-256 `id` over sorted columns and relationship type; stores `expected_direction` without peeking at outcomes.
- `TestResult`, `EffectSize`, `AssumptionCheck` (`contracts/results.py`): Records test name, full `selection_trace`, raw two-sided `p_value`, standardized effect size + CI, and assumption diagnostics.
- `ValidationDecision` & `RejectionReason` (`contracts/validation.py`): Records `p_raw`, `q_value`, `family_size`, `accepted`, machine-readable `reasons`, and counterfactual flags (`would_pass_without_correction`, `would_pass_without_effect_floor`).
- `Ledger` & `LedgerEntry` (`contracts/ledger.py`): Append-only session test log spanning `batch` and `chat` stages.
- `Fact` (`contracts/facts.py`) & `Finding` (`contracts/findings.py`): Immutable numeric traceability unit and unified finding bundle.

---

## 4. LangGraph Workflows (`src/veridata/agent/`)

### Batch Graph (`graph_batch.py`)
`START -> ingest_profile -> clean -> hypothesize -> test -> validate -> report -> END` (with conditional routing to `handle_error` on ingestion/test failure).

### Chat Graph (`graph_chat.py`)
`START -> guard_input -> (resolve_clarification | route_intent) -> extract_args -> validate_args -> (ask_clarification | execute_tool) -> update_ledger -> explain -> suggest_followups -> update_memory -> END`
with SQLite checkpointing (`checkpoint.py`) and prompt-injection/out-of-scope guards (`guardrails.py`).
