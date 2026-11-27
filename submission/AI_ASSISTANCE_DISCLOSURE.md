# AI Assistance Disclosure Statement

## Tools Used
- **Google Antigravity / Claude Code:** Used to accelerate boilerplate implementation, unit-test authoring, refactoring, documentation drafting, and experiment orchestration across Phases 1–8.

## How Every Output Was Verified (Non-Circular Safeguards)
1. **Statistical Reference & Hand-Computed Tests (Master Plan Rule 5):** Every statistical test, effect size, confidence interval, and helper function (`src/veridata/stats/`, `src/veridata/validation/`, `src/veridata/evaluation/stats_utils.py`) is covered by unit tests checking exact agreement against `scipy.stats` / `statsmodels` and hand-computed fixtures.
2. **Non-Circular Independent Recomputation (`E4`):** `src/veridata/evaluation/independent_recompute.py` is enforced by an AST import test (`tests/evaluation/test_independent_recompute.py`) to contain zero imports from `veridata.stats`, `veridata.validation`, `veridata.reporting`, or `veridata.agent`, independently checking VeriData's own p-values, sample sizes, and effect sizes.
3. **Deterministic Seeds & Split Discipline:** All synthetic suites (`smoke`, `core60`), permutation null checks, and bootstrap CIs use explicit fixed seeds; `dev` and `test` splits are isolated by seed ranges (`0..999` vs `10000..10999`) and guarded by `check_split()`.
4. **Offline Reproducibility & Fact Verification:** All automated test suites (`pytest`) run deterministically offline (`FakeLLM` / `NullLLM`) and verify 100% numeric grounding via `FactRegistry` and `verify_text()`.
