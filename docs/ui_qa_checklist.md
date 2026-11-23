# VeriData UI QA & Verification Checklist (Phase 7)

This checklist verifies the stability, accessibility, and presentation quality of the Streamlit user interface across the 4 demo datasets.

---

## 1. Automated & Smoke Checks

- [x] Application module `veridata.app` imports cleanly without errors.
- [x] Streamlit compatibility shim allows headless testing and execution.
- [x] All 4 demo datasets exist under `data/demo/`:
  - [x] `insurance.csv`
  - [x] `pure_noise.csv`
  - [x] `messy.csv`
  - [x] `telco_churn.csv`
- [x] Pre-warm script `scripts/prewarm_demo_cache.py` executes without errors.
- [x] Noise generator `scripts/make_noise_csv.py` produces 200 rows × 25 independent columns.

---

## 2. Tab-by-Tab Functional QA

### Sidebar
- [x] Logo, title, and descriptive tagline render properly.
- [x] Demo buttons load the respective datasets into `st.session_state`.
- [x] Upload component enforces the 50 MB size limit with friendly notifications.
- [x] Validation settings (alpha slider, correction selectbox, effect floor checkbox) update pipeline parameters.
- [x] Privacy notice is clearly visible.

### Tab 1: 📊 Overview
- [x] Displays total rows, columns, numeric columns, and categorical columns.
- [x] Column inventory table renders data types, unique counts, and missingness percentages.
- [x] Missingness summary reflects actual dataset missing values.

### Tab 2: ✅ Validated Findings
- [x] Displays count of validated discoveries surviving Benjamini-Hochberg FDR control.
- [x] Findings are sorted in descending order of standardized effect magnitude.
- [x] Each finding expander contains:
  - [x] Plain-language explanation (machine-verified, non-causal language).
  - [x] Test name, raw p-value, adjusted q-value, and sample size.
  - [x] Inline publication-quality figure.

### Tab 3: 🛡️ Rejected Patterns
- [x] Displays all hypotheses rejected during validation.
- [x] Rejection reasons clearly documented (e.g. `not_significant_after_correction`, `effect_below_threshold`).
- [x] Filter dropdown allows filtering by rejection category.

### Tab 4: ⚖️ Naive vs. Validated
- [x] Displays headline metric cards: Tests Evaluated, Naive Discoveries (raw p < 0.05), VeriData Validated, Spurious Patterns Blocked.
- [x] On `pure_noise.csv`, naive discovers ~15 false positives while VeriData validates 0.
- [x] Multiple-testing correction plot renders sorted p-values against the Benjamini-Hochberg boundary.

### Tab 5: 💬 Chat
- [x] Displays multiple-testing family status banner (total tests, validated discoveries, alpha).
- [x] Responds to queries with machine-verified numbers and inline charts.
- [x] Displays `✓ Numbers verified against FactRegistry` badge on answers.
- [x] Renders executable follow-up buttons that execute with one click.
- [x] Enforces guardrails against code generation, prediction requests, and prompt injections.

### Tab 6: 🔍 Facts & Traceability
- [x] Dropdown lists all evaluated hypotheses.
- [x] Facts table displays fact key, displayed string, numeric value, source, and unit.

### Tab 7: 📥 Report & Export
- [x] Download button for Findings Summary CSV produces valid CSV.
- [x] Download button for Complete Audit Ledger JSON produces valid JSON.

---

## 3. Visual & Usability Standards

- [x] Colorblind-safe palette (Okabe-Ito compliant) used across all figures.
- [x] No raw Python stack traces or uncaught exceptions shown to the user.
- [x] Responsive layout with side-by-side metric cards and readable dataframes.
