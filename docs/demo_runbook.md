# VeriData Live Demo Runbook (Phase 7)

## 1. Overview & Setup

- **Demo Goal:** Showcase that naive data analysis and LLM analysts find patterns everywhere by chance, whereas VeriData validates discoveries through Benjamini-Hochberg FDR control and strict machine-verified numbers.
- **Estimated Duration:** 5 to 7 minutes.
- **Launch Command:**
  ```bash
  make app
  # or
  streamlit run src/veridata/app/main.py
  ```
- **Demo Datasets (in `data/demo/`):**
  1. `pure_noise.csv`: 200 rows × 25 random independent columns (zero true signal).
  2. `insurance.csv`: 1,338 rows (smoker, age, BMI → charges).
  3. `messy.csv`: Synthetic messy dataset with planted true effects and format anomalies.
  4. `telco_churn.csv`: Churn prediction and subscription feature data.

---

## 2. Minute-by-Minute Demo Script

### Step 1: Hook (30 seconds)
- **Speaker:** *"If you give an LLM or a naive automated analyst a spreadsheet, it will test hundreds of arbitrary comparisons and enthusiastically report patterns that are purely noise. VeriData is an agentic data scientist that guarantees statistical honesty: every number comes from unit-tested tools, every discovery survives false discovery rate validation, and all claims are machine-verified."*

### Step 2: The Noise Demo (60–90 seconds) — The Contrast
- **Action:** Click the **"Pure Noise"** demo button in the sidebar.
- **Action:** Click **"Run Full Analysis Pipeline"**.
- **Action:** Open the **"⚖️ Naive vs. Validated"** tab.
- **Speaker:**
  - *"Here we have a dataset of 200 rows with 25 completely random, independent columns. There is zero true signal."*
  - *"Look at the Naive analysis: at an uncorrected p < 0.05 threshold, it falsely claims ~15 'significant discoveries' purely by chance."*
  - *"Now look at VeriData: 0 validated discoveries."*
- **Action:** Click the **"🛡️ Rejected Patterns"** tab.
  - *"Every spurious pattern was intercepted by Benjamini-Hochberg FDR correction. The system explains exactly why: raw p was nominally low, but after correcting for multiple tests, the adjusted q-value exceeded our alpha threshold."*

### Step 3: Real Data Demo (90 seconds) — Discoveries & Traceability
- **Action:** Click the **"Insurance"** demo button in the sidebar.
- **Action:** Click **"Run Full Analysis Pipeline"**. Watch the live status tracker stream stages (ingest, clean, hypothesize, test, validate, report).
- **Action:** Open the **"✅ Validated Findings"** tab.
  - Expand Finding #1: `charges vs smoker`.
  - Point out the plain-language explanation: *"Smokers have higher charges than non-smokers (Hedges' g = 1.42, large). FDR adjusted q < 0.001."*
  - Show the colorblind-safe distribution chart with jittered points and 95% CI error bars.
- **Action:** Open the **"🔍 Facts & Traceability"** tab.
  - *"Where did these numbers come from? Every number shown in the text is registered in our immutable FactRegistry with its exact precision and source code origin."*

### Step 4: Conversational Chat (90–120 seconds) — Honest Multi-Turn
- **Action:** Open the **"💬 Chat"** tab.
- **Action:** Type: `"Do smokers have higher charges?"`
  - Assistant answers with verified numbers, displays the boxplot inline, and shows the green `✓ Numbers verified against FactRegistry` badge.
- **Action:** Type: `"Is region related to charges?"`
  - Assistant tests the association, notes that region differences are small/non-significant after correction, and avoids exaggerating.
- **Action:** Click one of the **Suggested Follow-up buttons** (e.g. `👉 Examine correlation between age and charges`).
  - Assistant executes the correlation tool without router ambiguity and updates the multiple-testing family.
- **Speaker:** *"Notice the ledger status chip: every question asked by the user in chat is recorded into the session ledger, keeping the multiple-testing family honest across both batch and interactive turns."*

### Step 5: Wrap & Export (30 seconds)
- **Action:** Open the **"📥 Report & Export"** tab.
  - Download the findings summary CSV and structured audit ledger JSON.
- **Speaker:** *"VeriData turns AI from an unreliable code generator into a rigorous, verifiable scientific assistant."*

---

## 3. Plan B & Safety Nets

| Scenario | Plan B Action |
|---|---|
| **Slow computation on laptop** | Load precomputed bundle from `demo_bundles/<dataset>/` for instant tab population. |
| **No internet access** | App runs 100% offline using `NullLLM` and deterministic rule-based routers. |
| **Audience provides surprise CSV** | Upload via file uploader. If malformed, the friendly error handler explains the schema issue without crashing. |
