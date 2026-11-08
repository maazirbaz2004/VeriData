# VeriData — Agentic Data Scientist (Phase 1)

Deterministic CSV ingestion, semantic type inference, dataset profiling, conservative & imputed data cleaning, automated EDA, scaling analysis, rule-based insights, and LLM baseline comparison.

## Quickstart

```bash
# Install dependencies and package in editable mode
make setup

# Run test suite
make test

# Generate the messy synthetic dataset and ground-truth manifest
make make-messy

# Run Phase 1 pipeline on a single CSV
ads run --input data/synthetic/messy_dataset.csv --name messy_synthetic
```

