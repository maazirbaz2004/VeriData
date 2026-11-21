# VeriData — Agent Rules

1. Read `plans/00_MASTER_PLAN.md` and the current phase file before coding. Implement milestones in order. Run `make test` after each milestone and commit.
2. Never let an LLM produce or alter a number shown to the user. Never call an LLM inside `stats/`, `validation/`, `benchmark/` (generator/matcher/metrics) or `reporting/number_verifier.py`.
3. Do not read test results inside `hypotheses/`. Do not drop hypotheses from the family for outcome-dependent reasons.
4. Do not change shared contracts (`contracts/`) without bumping `schema_version` and updating `docs/contract.md` and the master plan.
5. Every new statistical function gets a test against scipy/statsmodels and a hand-computed case.
6. Record every non-obvious choice in `docs/decisions.md`.
7. Ask the human only for the items listed under "Human tasks" in the phase file.
8. When unsure, choose the conservative option and record it.

