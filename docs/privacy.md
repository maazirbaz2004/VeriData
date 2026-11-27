# VeriData Data Privacy & Security (`docs/privacy.md`)

## 1. Local Offline Execution by Default
- Running `veridata run --no-llm`, `veridata hypotheses --no-llm`, `veridata test`, `veridata report`, or `veridata chat --no-llm` (or leaving `.env` keys empty so `NullLLM` is active) executes **100% locally** with zero outbound network requests.
- Raw CSV files are never modified in place; SHA-256 checksums verify input immutability.

## 2. What Leaves the Machine When an LLM API Key Is Enabled
When `GEMINI_API_KEY` or `ANTHROPIC_API_KEY` is configured and `--no-llm` is not passed:
- **Phase 2 (`llm_proposals: true`):** Sends column names, inferred semantic types, missingness rates, and univariate distribution summaries (never full raw rows or bivariate test results).
- **Phase 6 Chat:** Sends sanitized user questions, column names, and schema metadata for intent/argument routing; numeric answers are always composed from local `FactRegistry` outputs.
- **Phase 8 Evaluation (`S1a`/`S1b` baselines only):** Sends schema, `df.describe()`, 5 head rows, and a 20-row sample to the baseline LLM for comparative evaluation.

## 3. Prompt-Injection & Arbitrary Code Defenses
- **Untrusted CSV Defense (P7):** Column names and string cell values embedded in LLM prompts are sanitized and delimited; `guard_input_node` (`src/veridata/agent/guardrails.py`) rejects prompt-override attempts.
- **No Arbitrary Code Execution in Product (P6):** The VeriData product agent calls only fixed, schema-validated Python statistical functions in `ToolRegistry`.
- **Isolated Benchmark Sandbox (Phase 8 `S1b` only):** LLM-generated Python code for the `S1b` baseline runs in a separate subprocess (`python -I`) after AST validation blocks `os`, `sys`, `subprocess`, `open`, `eval`, `exec`, and network imports.
