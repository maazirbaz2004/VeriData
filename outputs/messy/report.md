# VeriData Analysis Report — `messy`

- **Multiple-testing family size:** 45
- **Validated discoveries:** 5

## Validated Findings

### income vs monthly_spend
- **Explanation:** income and monthly_spend are positively associated (n = 1,840). The correlation is large (spearman_rho = 0.89). After correcting for 32 tests (FDR 5%), the association is statistically supported (adjusted p <0.001). This reflects an observed correlation, not a direct causal link.
- **P-value:** 0.000e+00 (FDR adjusted q: 0.000e+00)

### income vs membership
- **Explanation:** Across levels of membership, values of income showed variation (n = 1,840). The overall association is large (epsilon_squared = 0.26). After correcting for 32 tests (FDR 5%), the association is statistically supported (adjusted p <0.001). This is an observed association and does not establish that membership determines income.
- **P-value:** 9.065e-106 (FDR adjusted q: 1.450e-104)

### monthly_spend vs membership
- **Explanation:** Across levels of membership, values of monthly_spend showed variation (n = 2,000). The overall association is large (epsilon_squared = 0.23). After correcting for 32 tests (FDR 5%), the association is statistically supported (adjusted p <0.001). This is an observed association and does not establish that membership determines monthly_spend.
- **P-value:** 1.241e-99 (FDR adjusted q: 1.324e-98)

### tenure_months vs churned
- **Explanation:** Among 1,980 records, the values of tenure_months were associated with churned. The difference is medium (hedges_g = 0.70). After correcting for 32 tests (FDR 5%), the association is statistically supported (adjusted p <0.001). This is an observed association and does not show that churned causes differences in tenure_months.
- **P-value:** 1.525e-47 (FDR adjusted q: 1.220e-46)

### churned vs satisfaction
- **Explanation:** churned and satisfaction showed an association across categories (n = 1,940). The degree of association is small (cramers_v_bc = 0.28). After correcting for 32 tests (FDR 5%), the association is statistically supported (adjusted p <0.001). This reflects category co-occurrence, not a causal dependency.
- **P-value:** 1.076e-32 (FDR adjusted q: 6.887e-32)
