# VeriData User Guide (`docs/user_guide.md`)

## 1. Installation & Optional LLM Key Setup

```powershell
python -m pip install -r requirements.txt streamlit
python -m pip install -e .
```

VeriData's deterministic statistical core works **100% offline** with no API key.
To enable optional Google Gemini LLM support (for hypothesis ranking, narration, and LLM-only evaluation baselines), open `.env` at the repository root and set:

```dotenv
GEMINI_API_KEY=your_api_key_here
```

*(Anthropic Claude is also supported via `ANTHROPIC_API_KEY=` and `llm.provider: "anthropic"` in `configs/default.yaml`.)*

---

## 2. Launching the Streamlit Dashboard

```powershell
streamlit run src/veridata/app/main.py
```

Open `http://localhost:8501` in your browser:
1. **Upload or select a demo dataset** (`Insurance`, `Pure Noise`, `Messy Synthetic`, or your own CSV).
2. Click **Run Full Analysis Pipeline** to execute Phase 1 cleaning, Phase 2 enumeration, Phase 3 testing + BH validation, and Phase 5 reporting.
3. Inspect tabs:
   - **Validated Findings**: Only discoveries passing FDR control, practical effect floors, and assumption/triviality gates.
   - **Naive vs. Validated**: Direct contrast showing how many raw `p < 0.05` noise patterns were filtered out.
   - **Rejected Patterns**: Machine-readable and plain-language rejection reasons (`not_significant_after_correction`, `effect_below_threshold`, etc.).
   - **Facts & Traceability**: Immutable `FactRegistry` audit table showing the exact origin of every printed number.
   - **Chat**: Multi-turn statistical assistant whose follow-up tests append to the shared `SessionLedger` and revalidate the BH family.

---

## 3. CLI Reference

| Command | Purpose |
| :--- | :--- |
| `veridata run --input data.csv --name mydata` | Run Phase 1 ingestion, profiling, cleaning, and EDA |
| `veridata hypotheses --dataset mydata --no-llm` | Generate feasible hypotheses without peeking at outcomes |
| `veridata test --dataset mydata` | Execute statistical tests, Stage B CIs, and BH validation |
| `veridata report --dataset mydata` | Render verified Markdown & self-contained HTML findings report |
| `veridata chat --dataset mydata` | Launch interactive terminal chat backed by `SessionLedger` |
| `veridata eval plan --suite core60 --split dev` | Print evaluation run counts and estimated LLM budget |
| `veridata eval run --experiment all --suite core60 --split dev` | Run Phase 8 evaluation suite (`E1`–`E8`) |
| `veridata final-report --suite core60 --split dev` | Build `final_report/FINAL_REPORT.md` & `FINAL_REPORT.html` from cache |

---

## 4. How to Interpret VeriData Outputs

- **Raw `p`-value vs. Adjusted `q`-value:** A raw `p < 0.05` on one pair ignores all other tests run in the session. The Benjamini-Hochberg `q`-value controls the expected **False Discovery Rate** (share of false positives among all reported findings) at `alpha = 0.05`. Note that individual findings near `q = 0.04–0.05` are borderline and carry higher false-lead risk than findings with `q < 0.001`.
- **Standardized Effect Size Floor:** With large datasets (`n = 5,000+`), tiny meaningless correlations (`r = 0.04`) can have `q < 0.001`. VeriData requires effects to meet at least Cohen's "small" threshold (`|d| >= 0.20`, `|r| >= 0.10`, `|r_rb| >= 0.10`, `eta^2 >= 0.01`, `V_bc * sqrt(df*) >= 0.10`).
- **95% Confidence Intervals:** Intervals are computed via analytic or BCa bootstrap methods in Stage B. As noted in `docs/stats_methods.md`, reported CIs are nominal post-selection intervals.
- **Association, Not Causation:** Every finding reflects statistical association in the supplied sample; confounding variables and unmeasured biases can explain observed links.
