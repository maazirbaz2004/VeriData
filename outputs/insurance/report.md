# VeriData Analysis Report — `insurance`

- **Multiple-testing family size:** 21
- **Validated discoveries:** 6

## Validated Findings

### charges vs smoker
- **Explanation:** Among 1,337 records, the values of charges were associated with smoker. The difference is large (hedges_g = -3.16). After correcting for 21 tests (FDR 5%), the association is statistically supported (adjusted p <0.001). This is an observed association and does not show that smoker causes differences in charges.
- **P-value:** 6.262e-103 (FDR adjusted q: 1.315e-101)

### age vs charges
- **Explanation:** age and charges are positively associated (n = 1,337). The correlation is large (spearman_rho = 0.53). After correcting for 21 tests (FDR 5%), the association is statistically supported (adjusted p <0.001). This reflects an observed correlation, not a direct causal link.
- **P-value:** 3.188e-99 (FDR adjusted q: 3.347e-98)

### bmi vs region
- **Explanation:** Across levels of region, values of bmi showed variation (n = 1,337). The overall association is medium (eta_squared = 0.08). After correcting for 21 tests (FDR 5%), the association is statistically supported (adjusted p <0.001). This is an observed association and does not establish that region determines bmi.
- **P-value:** 1.243e-21 (FDR adjusted q: 8.704e-21)

### bmi vs charges
- **Explanation:** bmi and charges are positively associated (n = 1,337). The correlation is small (spearman_rho = 0.12). After correcting for 21 tests (FDR 5%), the association is statistically supported (adjusted p <0.001). This reflects an observed correlation, not a direct causal link.
- **P-value:** 1.164e-05 (FDR adjusted q: 6.110e-05)

### charges vs children
- **Explanation:** Across levels of children, values of charges showed variation (n = 1,337). The overall association is small (epsilon_squared = 0.02). After correcting for 21 tests (FDR 5%), the association is statistically supported (adjusted p <0.001). This is an observed association and does not establish that children determines charges.
- **P-value:** 2.196e-05 (FDR adjusted q: 9.222e-05)

### age vs bmi
- **Explanation:** age and bmi are positively associated (n = 1,337). The correlation is small (spearman_rho = 0.11). After correcting for 21 tests (FDR 5%), the association is statistically supported (adjusted p <0.001). This reflects an observed correlation, not a direct causal link.
- **P-value:** 7.714e-05 (FDR adjusted q: 2.700e-04)
