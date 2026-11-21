# VeriData Statistical Methods & Validation Guide (`docs/stats_methods.md`)

> **Applies to:** Phase 3 Statistical Tool Library (`src/veridata/stats/`) and Validation Layer (`src/veridata/validation/`).
> **Design invariant:** Every p-value, statistic, effect size, confidence interval, and validation decision is computed deterministically by tested Python code—never by an LLM (Principle P1).

---

## 1. Fixed Statistical Tool Library & Selection Rules

Test selection depends **exclusively** on univariate/per-group assumption diagnostics and table expected counts—never on p-values or bivariate effect sizes. Every `TestResult` records its full decision path in `selection_trace`.

| Relationship | Primary Test | Non-Parametric / Exact Fallback | Deterministic Selection Rule |
| :--- | :--- | :--- | :--- |
| **`NUM_BINARY`** (2 groups) | **Welch's t-test** (`scipy.stats.ttest_ind(equal_var=False)`) | **Mann-Whitney U** (`scipy.stats.mannwhitneyu`, `exact` if no ties & $n \le 50$) | Use Welch's t if both groups pass normality (Shapiro $p > 0.01$ for $n \le 5000$, or $|\text{skew}| < 1$ and $|\text{excess kurt}| < 3$), **or** both groups have $n \ge 50$ with $|\text{skew}| \le 2.0$ (CLT). Fall back to Mann-Whitney U if normality/CLT fails or if either group has zero variance. |
| **`NUM_CATEGORICAL`** ($k \ge 3$ groups) | **Welch's one-way ANOVA** (`statsmodels.stats.oneway.anova_oneway(use_var="unequal")`) | **Kruskal-Wallis H** (`scipy.stats.kruskal`) | Use Welch's ANOVA if all groups pass normality **or** all groups have $n \ge 50$ with $|\text{skew}| \le 2.0$. Fall back to Kruskal-Wallis otherwise (or if any group has zero variance). If rare-level filtering ($n < 8$) leaves 2 groups, collapse cleanly to `NUM_BINARY` rules. |
| **`NUM_NUM`** (2 numeric vars) | **Pearson $r$** (`scipy.stats.pearsonr`) | **Spearman $\rho$** (`scipy.stats.spearmanr`) | Use Spearman if ties $> 50\%$ or $n < 30$. Use Pearson if both pass normality with $< 2\%$ extreme ($3\times\text{IQR}$) outliers, **or** $n \ge 200$ with $|\text{skew}| \le 2.0$ and $< 5\%$ extreme outliers. Fall back to Spearman otherwise. An advisory quadratic F-test is logged for Pearson without altering test selection. |
| **`CAT_CAT`** ($r \times c$ table) | **Pearson Chi-Square** (`scipy.stats.chi2_contingency(correction=False)`) | **Fisher's Exact** ($2\times 2$) / **Monte Carlo Chi-Square** ($r \times c$) | For $2 \times 2$: Fisher's exact if any expected count $< 5$ or $n < 40$; else Chi-Square. For $r \times c$: Chi-Square if $\ge 80\%$ of cells have expected $\ge 5$ and $\min(\text{expected}) \ge 1$; else seeded permutation Monte Carlo Chi-Square ($p = (1 + \#\{T^* \ge T_{\text{obs}}\}) / (1 + B)$). |

All tests are **two-sided** (`stats.two_sided: true`). Random seeds are derived deterministically per hypothesis (`sha256(seed:hypothesis_id)`) so results are 100% reproducible and independent of parallel execution order.

---

## 2. Standardized Effect Sizes & Confidence Intervals

| Test | Primary Effect Size | Practical "Small" Floor | Confidence Interval (95%) |
| :--- | :--- | :---: | :--- |
| `welch_t` | **Hedges' $g$** (bias-corrected Cohen's $d$, pooled SD) + mean difference | $|g| \ge 0.20$ | Analytic Hedges & Olkin SE (Stage A); Welch-Satterthwaite $t$ CI for raw mean diff |
| `mann_whitney_u` | **Rank-biserial $r_{rb} = 2U_1/(n_1 n_2) - 1$**, Prob. of Superiority, Hodges-Lehmann shift | $|r_{rb}| \ge 0.10$ | Stratified within-group percentile bootstrap (Stage B) |
| `welch_anova` | **$\eta^2$** ($\text{SS}_{\text{between}}/\text{SS}_{\text{total}}$) and bias-corrected **$\omega^2$** | $\eta^2 \ge 0.01$ | Stratified within-group percentile bootstrap on $\eta^2$ (Stage B) |
| `kruskal_wallis` | **$\epsilon^2 = H / (n - 1)$** (Tomczak & Tomczak) | $\epsilon^2 \ge 0.01$ | Stratified within-group percentile bootstrap (Stage B) |
| `pearson` | **Pearson $r$** | $|r| \ge 0.10$ | Analytic Fisher $z$-transform (Stage A) |
| `spearman` | **Spearman $\rho$** | $|\rho| \ge 0.10$ | Paired row bootstrap (Stage B; Fieller Fisher-$z$ in benchmark fast mode) |
| `chi_square` / `fisher_exact` / `monte_carlo_chi_square` | **Bias-corrected Cramér's $\tilde{V}$** (Bergsma 2013); for $2 \times 2$ also $\phi$, Odds Ratio (Woolf CI), Risk Diff | $\tilde{V}\sqrt{\text{df}^*} \ge 0.10$ (Cohen's $w$ equivalence) | Paired row bootstrap on $\tilde{V}$ (Stage B); Woolf CI for $2 \times 2$ OR |

**Two-Stage Execution:** Stage A computes assumptions, test selection, p-values, and point effect sizes for all hypotheses. Stage B computes expensive bootstrap CIs, parametric/non-parametric sensitivity checks (`test_sensitive` flag), and leave-1%-out outlier influence checks (`fragile_to_outliers` flag) only on candidate hypotheses ($q \le \alpha$ or $p_{\text{raw}} < 0.10$).

---

## 3. Multiple-Testing Correction & Validation Gates

1. **Family Definition:** All tests in the session ledger (`ledger.jsonl`) with `status == "ok"` and finite `p_value` form the family of size $m$. Skipped/infeasible tests are excluded from $m$ and explicitly listed as `INSUFFICIENT_DATA` or `DEGENERATE_DATA`.
2. **Correction:** Benjamini-Hochberg (BH) FDR control at $\alpha = 0.05$ is default (`bh`), implemented from scratch and cross-checked against `statsmodels.stats.multitest.multipletests`. Conservative/ablation options `by` (Benjamini-Yekutieli), `holm`, `bonferroni`, and `none` are supported.
3. **Validation Gates (applied in order):**
   - `INSUFFICIENT_DATA` / `DEGENERATE_DATA` / `TEST_ERROR` (status gate)
   - `NOT_SIGNIFICANT_AFTER_CORRECTION` ($q > \alpha$)
   - `EFFECT_BELOW_THRESHOLD` (standardized comparable effect $<$ configured floor)
   - `ASSUMPTION_VIOLATED` (unresolved `violation`-severity check after fallback)
   - `TRIVIAL_RELATIONSHIP` (near-deterministic/derived pair: $|r| \ge 0.999$, $\tilde{V} \ge 0.99$, or zero-overlap $|r_{rb}| = 1$ with $n \ge 20$)
   - `UNSTABLE_CI` (strict mode only, off by default: 95% CI includes 0)

---

## 4. Statistical Limitations

- **Observational association only:** Passing all gates establishes statistical association, never causation (Principle P5).
- **Independence assumption:** All tests assume i.i.d. rows; clustered or repeated-measures data can inflate false discovery rates.
- **Dependence across pairwise tests:** Pairwise tests sharing columns are correlated; BH assumes independence or PRDS. Benjamini-Yekutieli (`--correction by`) is provided for arbitrary dependence, and empirical FDR under correlated nulls is calibrated in Phase 4.
- **Post-selection confidence intervals:** Marginal 95% CIs on BH-selected findings are unadjusted for selection (winner's curse) and should be interpreted as nominal intervals.
- **Mann-Whitney interpretation:** When Levene's test detects markedly unequal spreads, Mann-Whitney U tests stochastic dominance $P(X_1 > X_2) \ne 0.5$ rather than a pure shift in medians.

