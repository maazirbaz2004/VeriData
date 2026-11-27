# VeriData Presentation Outline (12 Slides)

1. **Title & Motivation:** *VeriData: Validated Agentic Data Science with Controlled False Discovery Rate.* Problem: exploratory analysis & LLMs report chance noise and unverified numbers.
2. **Core Principles (P1–P10):** Zero-peeking hypotheses, unified BH session ledger, fixed statistical tool library, FactRegistry verification, association-only linting.
3. **End-to-End Architecture:** Phases 1–7 pipeline (`docs/architecture.md`) + LangGraph batch & chat state machines.
4. **Statistical Tool Library & Selection Rules:** Assumption-aware routing across Welch *t* / MWU, Welch ANOVA / Kruskal, Pearson / Spearman, Chi-square / Fisher / MC Chi-square + Stage B CIs.
5. **Multiple-Testing Ledger & Validation Gates:** Unified `batch U chat` BH family, Cohen small effect-size floor, assumption & triviality gates.
6. **Number Verification & Language Linting:** `FactRegistry` traceability, half-ULP verifier tolerance, zero causal claims.
7. **E1 Main Benchmark Results (`fig_e1_fdr_recall_bars.png`):** `S3` (`veridata_full`) FDR <= 5% vs `S2` (`veridata_nocorrection`) ~70% FDR and LLM-only baselines.
8. **E1 Trade-Off & Null Calibration (`fig_e1_alpha_tradeoff.png`, `fig_e1_null_fp.png`, `fig_e1_q_calibration.png`):** Alpha sweep, zero-effect FWER, and borderline q-value behavior.
9. **E2 Ablation & E3 Calibration (`fig_e2_ablation.png`, `fig_e3_dependence_fdr.png`):** Marginal contribution of BH, effect floor, assumption selection, and gates.
10. **E4 Number Correctness & E6 Test Selection:** 100% VeriData verification on both Phase 5 verifier and independent recomputation vs baseline fabrication.
11. **E5 Real Datasets & E7/E8 (`fig_e5_real_reliability.png`):** Pre-registered Kaggle/UCI recovery, permuted-null FP suppression, split-half replication, chat evaluation, and messy-input robustness.
12. **Live Demo Walkthrough & Conclusion:** Pure Noise vs Insurance vs Messy Synthetic in Streamlit (`docs/demo_runbook.md`).
