# PHASE 7 — User Interface, Demo Mode, and Demo Rehearsal

> Prerequisite reading: `00_MASTER_PLAN.md`, Phase 5 (report, charts), Phase 6 (`Session`, `build_batch_graph`, `build_chat_graph`, streaming).
> Goal: a polished **live-upload demo** that makes the project's core idea visible in minutes: *naive analysis finds patterns everywhere; VeriData keeps only the ones that survive validation, and every number is traceable.*
> The UI contains **no statistics or business logic**. It calls the Phase 6 `Session` API only.

---

## 1. Goals

1. **Streamlit app**: upload a CSV → watch the pipeline stages → see validated findings, rejected patterns, charts → chat with the data → download the report.
2. **Transparency features** that sell the project: "naive vs validated" comparison, "where did this number come from" fact tables, selection traces ("why this test?"), rejection reasons.
3. **Robust live demo**: offline/cached mode with no network dependency, pre-loaded sample datasets, fallbacks for every failure mode, a rehearsed script, and backups (screenshots, video).
4. **Basic hardening**: file size/type limits, session isolation, friendly errors, privacy notice.

### Out of scope
Authentication, multi-user deployment, databases beyond SQLite, mobile layout polish.

---

## 2. Technology choices

- **Streamlit** (pin the version). Rationale: fastest path to a demo-quality UI in Python; native chat elements (`st.chat_message`, `st.chat_input`), `st.status` for progress, `st.tabs`, `st.dataframe`, `st.download_button`.
- Alternative (document in `decisions.md` but do not build): Gradio. Choose only if the team already knows it.
- Run locally for the demo (`make app` → `streamlit run src/veridata/app/main.py`). Hosted deployment (Streamlit Community Cloud / HF Spaces) is optional; note that hosted mode requires secrets handling and public-upload warnings.

---

## 3. App structure (`src/veridata/app/`)

```
main.py              # entry: page config, sidebar, tab routing
session.py           # Streamlit session_state wrapper around agent.Session; creation, reset, persistence
components/
  upload.py          # uploader + sample dataset buttons + config panel
  progress.py        # st.status stage tracker fed by graph streaming
  overview.py        # data profile + cleaning summary
  findings.py        # validated findings list with expanders
  rejected.py        # rejected patterns table with reasons
  naive_vs_validated.py  # headline comparison + BH plot
  chat.py            # chat panel, follow-up buttons, ledger status chip
  facts_viewer.py    # "where did this number come from?"
  report_export.py   # download HTML/MD/CSV/JSON
  settings.py        # alpha, effect floor toggle, LLM on/off, mode, target selection
assets/ (css, logo)
```

### 3.1 Layout
- **Sidebar:** logo/name (VeriData), dataset upload/sample picker, "Target column (optional)", expert settings (collapsed): alpha, correction method (BH default; BY option), effect-floor toggle, LLM on/off, narration mode, offline demo mode toggle. Privacy notice ("column names and category labels are sent to the LLM provider when LLM is enabled; cell values are not").
- **Main area tabs:**
  1. **Overview**: rows/cols, column types table, missingness chart, cleaning log summary (what was fixed, counts), warnings (ID-like columns excluded, etc.).
  2. **Findings** (default after analysis): headline cards ("{m} tests · {n_raw} raw p<0.05 · {n_acc} validated"), list of validated findings sorted by effect magnitude; each is an expander with explanation text, chart, stats table, "How was this tested?" (selection trace in plain language), "Where do these numbers come from?" (facts table), flags (outlier sensitivity etc.).
  3. **Rejected patterns**: table (columns, raw p, adjusted q, effect, reason) + plain explanation for each; filter by reason. This tab is the star of the demo.
  4. **Naive vs validated**: side-by-side counts + BH plot + volcano plot; toggle "show what a naive analysis would have reported" listing naive-only findings with reasons they were rejected.
  5. **Chat**: conversation, suggested follow-up buttons (from Phase 6), ledger status chip ("Session family: 812 tests · 7 validated"), charts inline, "exploratory" badges on chat tests.
  6. **Report**: preview + download (HTML, Markdown, CSV of findings, JSON of facts/ledger).
  7. **About/Methods**: the methods text from the report, limitations.

### 3.2 Behavior details
- **Run flow:** Upload → quick validation (size limit default 50 MB, ≤ 500k rows, ≤ 200 columns; larger → friendly message and optional subsampling prompt) → confirm roles step (shows inferred types, lets the user mark target/ID/exclude; Phase 6 `interrupt`) → "Run analysis" button → `st.status` shows stage-by-stage progress from graph streaming (profile, clean, hypotheses, testing X/Y, validation, report) → tabs populate.
- **Caching:** use `st.cache_data`/session-level caches keyed by dataset SHA + config hash so toggling tabs doesn't recompute; analysis runs once per (dataset, config).
- **Non-blocking:** long steps run in a worker thread/process with progress polling (`st.status` + `time.sleep` loop) or use Streamlit fragments; ensure the UI doesn't freeze on 780 tests. Use the batch graph's progress callback.
- **Session isolation:** each browser session gets its own `session_id` and directory under `sessions/`; no cross-talk.
- **Errors:** every `VeriDataError` displayed as a friendly `st.error` with a "what to try" hint; unexpected exceptions logged and shown as a generic message with a "download debug bundle" button (logs, config, no data).
- **Accessibility:** colorblind-safe charts (from Phase 5 style), alt text via captions, readable fonts.
- **Download buttons:** report.html, report.md, findings.csv, ledger.jsonl, facts.json, cleaned_dataset.csv, cleaning_log.json.

### 3.3 Chat panel specifics
- Streams answers progressively: status line ("Running Welch t-test…") then the verified final text (the answer is verified *before* display; show a small "✓ numbers verified" badge with a popover listing the fact keys used).
- Follow-up buttons render below the answer; clicking calls `session.run_followup(call)`.
- A "Why this test?" link expands the selection trace.
- Input box examples as placeholders ("Do smokers pay more?", "Is age related to charges?", "Why was X rejected?").
- A "Clear conversation" button (keeps ledger) and "Reset analysis" (clears all, confirms).

---

## 4. Demo mode (offline/cached) — the safety net

Config `demo.offline: true` (also `--offline-demo`):
- LLM calls are served from the **disk cache** pre-warmed by running the demo datasets once online (`scripts/prewarm_demo_cache.py` runs the batch graph and a scripted chat transcript so the cache holds every LLM call for those datasets/questions). If a request misses the cache in offline mode → deterministic fallbacks (templates/rule router), so the demo **never fails or hangs**; a small "offline mode" badge in the sidebar shows state.
- Sample dataset buttons load bundled CSVs from `data/demo/` (small, license-cleared): (1) **insurance** (clean story: smoker, age, BMI → charges); (2) a **messy** CSV (synthetic messy dataset from Phase 1, with planted effects) to show cleaning; (3) **pure noise** CSV (200 rows × 25 random columns of mixed types) for the dramatic contrast; (4) one more real dataset (e.g., Telco churn sample ≤ 5,000 rows) for variety.
- Precomputed **result bundles** for each demo dataset (`demo_bundles/<name>/`) allow instant load ("Load precomputed analysis") in case live computation is slow or the machine is under-powered.
- Pre-warm script also generates screenshots (headless browser using Playwright) for the backup deck.

---

## 5. The demo script (5-7 minutes; rehearse until smooth)

1. **Hook (30 s):** "Ask an AI to analyze a spreadsheet and it'll tell you about patterns that aren't real. VeriData only reports what survives validation."
2. **Noise demo (60-90 s):** upload `pure_noise.csv`. Show Naive vs Validated: naive reports N "significant" findings (expected ≈ 5% of tests, e.g., ~15 of ~300); VeriData reports 0 and the rejected tab explains why ("raw p = …, after correcting for … tests, adjusted p = …"). Say: "These are exactly the false discoveries an LLM analyst would happily report."
3. **Real data (90 s):** upload/pick insurance. Pipeline progress, data quality summary (cleaning), validated findings: smoker → charges with chart and plain-language explanation; open "Where do these numbers come from?"; open "Why this test?".
4. **Messy data (45 s):** (optional) show the cleaning log catching formats/duplicates.
5. **Chat (90-120 s):** ask "Do smokers have higher charges?" (answered with verified numbers and chart); ask "Is region related to charges?" (probably rejected or small → shows honesty); click a follow-up; point at the ledger chip: "every extra question adds a test to the multiple-testing family, and the system keeps count."
6. **Verification punchline (30 s):** show the number-verification badge/popover; mention the evaluation: "On 60 synthetic datasets with planted truth, the LLM-only analyst had X% false discovery rate; VeriData had Y%." (insert real numbers from Phase 8 results — only after they exist).
7. **Wrap (15 s):** limitations (association not causation; tabular; pairwise) and next steps.

Provide **Plan B** for each step: precomputed bundle, offline mode, screenshots, and a 2-minute screen recording of the full demo (record a clean run once everything is final).

**Audience upload scenario (if asked to analyze a surprise CSV):** have a prepared line: "Let's try it." Pre-test with several odd CSVs (semicolon delimiters, BOM, 40 columns, missing values) so surprises work. If the file fails, the friendly error message explains why. Keep `scripts/make_noise_csv.py` ready to generate noise on the spot.

---

## 6. Tests

- **Unit tests for components** using `streamlit.testing.v1.AppTest` (headless): app starts; sample dataset click loads; running analysis (fixtures, FakeLLM, `use_llm=False`) populates tabs; chat question gets an answer with verification badge; rejected tab shows rows; downloads produce files.
- **Robustness:** bad uploads (empty file, binary file, wrong extension, huge file over the limit, one-column CSV, all-text CSV) → friendly errors, no traceback shown.
- **Offline-mode test:** run the app flow with network disabled and a pre-warmed cache; ensure zero outbound calls (mock `socket`).
- **Session isolation:** two `AppTest` sessions don't share state.
- **Performance:** insurance dataset analysis completes ≤ 60 s on the demo laptop without LLM, ≤ 90 s with cached LLM; noise dataset ≤ 45 s. Record timings in `docs/demo_runbook.md`.
- **Visual regression (optional):** Playwright screenshots of each tab compared to baselines manually (not automated pixel diff).
- **Manual QA checklist** (`docs/ui_qa_checklist.md`): every tab on 4 demo datasets; mobile-width sanity; dark/light theme legibility of charts; long column names; 100+ column dataset.

---

## 7. Milestones

| ID | Work | Est. |
|---|---|---|
| P7-M0 | App skeleton, `session.py`, upload + sample loader, settings | 1 d |
| P7-M1 | Progress streaming from the batch graph; roles confirmation | 0.75 d |
| P7-M2 | Overview, Findings, Rejected, Naive-vs-Validated tabs | 1.5 d |
| P7-M3 | Chat panel, follow-ups, ledger chip, verification badge, facts viewer | 1.25 d |
| P7-M4 | Report tab/downloads; error handling; limits; privacy notice | 0.5 d |
| P7-M5 | Demo datasets, pre-warm script, offline mode, precomputed bundles | 1 d |
| P7-M6 | `AppTest` tests, robustness tests, QA checklist, runbook | 1 d |
| P7-M7 | Demo script rehearsal, screenshots, video, backup deck | 1 d |

---

## 8. Acceptance criteria

- [ ] `make app` launches; all 7 tabs work on the 4 demo datasets.
- [ ] End-to-end live upload works with a never-seen CSV (UTF-8, semicolon-delimited, BOM variants) and shows friendly errors for invalid files.
- [ ] Offline demo mode runs the full demo script with the network disabled and never hangs.
- [ ] The noise demo shows naive-vs-validated contrast (validated = 0 findings in the default seed; document the seed and expected naive count).
- [ ] Every chat answer displays a verification badge; facts viewer works.
- [ ] Analysis timings meet the budgets in Section 6 on the demo machine.
- [ ] `AppTest` suite passes; QA checklist completed and signed.
- [ ] Backup assets exist: screenshots of each step, a recorded demo video, precomputed bundles.
- [ ] `docs/demo_runbook.md` includes the script, Plan B steps, machine setup, known issues, and a contact checklist (API key present, cache warmed, battery, display adapter).

---

## 9. Pitfalls

1. **Doing computation in Streamlit callbacks** blocks the UI and reruns on every interaction. Use the Session API and caching; avoid recomputation on rerun.
2. **State loss on rerun.** Everything important lives in `st.session_state` or the Phase 6 session; never in module globals.
3. **Live demo network failure.** Offline mode and bundles are mandatory, not optional.
4. **Showing numbers before verification.** Display only verified answers.
5. **Overcomplicated UI.** Time is better spent on the Findings/Rejected/Naive-vs-Validated tabs than on styling.
6. **Uncontrolled uploads** (huge files). Enforce limits early.
7. **Demo claims without evidence.** Do not quote evaluation numbers in the demo until Phase 8 is done; then quote them exactly from the results tables.

---

## 10. Human tasks

- Provide demo datasets/licenses; choose the demo machine; pre-warm the cache on the day.
- Rehearse the script ≥ 3 times with a timer; record the backup video.
- Review the privacy notice wording.
