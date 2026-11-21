# Phase 2 Hypothesis Set — `messy_synthetic`

## Family Manifest Summary
- **Mode:** `exhaustive` (effective: `exhaustive`)
- **Target:** `churned`
- **Columns:** `9` eligible / `13` total
- **Candidate Hypotheses:** `36`
- **Planned Family Size (`m`):** `36` feasible (`0` infeasible, `0` pruned)
- **LLM Used:** `False`
- **Selection Inputs Hash:** `eb2cb8b22fbbecd2`

### Planned Tests by Relationship Type
- `categorical_vs_categorical`: `10`
- `numeric_vs_binary`: `8`
- `numeric_vs_categorical`: `12`
- `numeric_vs_numeric`: `6`

### Excluded Columns
- `constant_flag`: constant
- `customer_id`: id
- `notes`: free_text
- `signup_date`: datetime_not_testable

### Manifest Notes
- datetime columns not testable in this version

## Hypotheses (Ordered by Outcome-Independent Priority)

| ID | Column A | Column B | Relationship | Feasible | n_complete | Priority | Source | Rationale |
| :--- | :--- | :--- | :--- | :---: | ---: | ---: | :--- | :--- |
| `eaf7928cec2923a9` | `monthly_spend` | `churned` | `numeric_vs_binary` | yes | 2000 | 0.875 | `enumerated` |  |
| `57d2185da42c904a` | `tenure_months` | `churned` | `numeric_vs_binary` | yes | 1970 | 0.874 | `enumerated` |  |
| `6ff0291da26911e4` | `age` | `churned` | `numeric_vs_binary` | yes | 1860 | 0.872 | `enumerated` |  |
| `2d06e23f3fba4c46` | `income` | `churned` | `numeric_vs_binary` | yes | 1840 | 0.871 | `enumerated` |  |
| `440d399dbca57ad0` | `churned` | `membership` | `categorical_vs_categorical` | yes | 2000 | 0.850 | `enumerated` |  |
| `266a5d2ef3589025` | `churned` | `gender` | `categorical_vs_categorical` | yes | 2000 | 0.847 | `enumerated` |  |
| `6eb5c2437729d7b0` | `churned` | `satisfaction` | `categorical_vs_categorical` | yes | 1940 | 0.843 | `enumerated` |  |
| `ba4abeaba9778090` | `churned` | `region` | `categorical_vs_categorical` | yes | 1920 | 0.842 | `enumerated` |  |
| `d9d777c2c95f4e4f` | `monthly_spend` | `gender` | `numeric_vs_binary` | yes | 2000 | 0.575 | `enumerated` |  |
| `f238aa6f8c59b9cc` | `tenure_months` | `gender` | `numeric_vs_binary` | yes | 1970 | 0.574 | `enumerated` |  |
| `86300d32b4bc1d5a` | `age` | `gender` | `numeric_vs_binary` | yes | 1860 | 0.572 | `enumerated` |  |
| `a3e48f6562e32a4f` | `income` | `gender` | `numeric_vs_binary` | yes | 1840 | 0.571 | `enumerated` |  |
| `11e591d0b39e52cd` | `monthly_spend` | `membership` | `numeric_vs_categorical` | yes | 2000 | 0.555 | `enumerated` |  |
| `58dafdd3fcc7e54a` | `tenure_months` | `membership` | `numeric_vs_categorical` | yes | 1970 | 0.554 | `enumerated` |  |
| `9c277bf52ea9d362` | `monthly_spend` | `tenure_months` | `numeric_vs_numeric` | yes | 1970 | 0.554 | `enumerated` |  |
| `12dcc57e8536c0fd` | `age` | `membership` | `numeric_vs_categorical` | yes | 1860 | 0.551 | `enumerated` |  |
| `62c1a8cb07224989` | `age` | `monthly_spend` | `numeric_vs_numeric` | yes | 1860 | 0.551 | `enumerated` |  |
| `67435025f39bfab0` | `income` | `membership` | `numeric_vs_categorical` | yes | 1840 | 0.551 | `enumerated` |  |
| `a3ae6c5e3e862743` | `income` | `monthly_spend` | `numeric_vs_numeric` | yes | 1840 | 0.551 | `enumerated` |  |
| `0e1685a9a0392d0c` | `age` | `tenure_months` | `numeric_vs_numeric` | yes | 1831 | 0.551 | `enumerated` |  |
| `8cb228d4db25a4a1` | `income` | `tenure_months` | `numeric_vs_numeric` | yes | 1811 | 0.550 | `enumerated` |  |
| `1999e2ace938d168` | `age` | `income` | `numeric_vs_numeric` | yes | 1711 | 0.547 | `enumerated` |  |
| `de2188281035b45a` | `gender` | `membership` | `categorical_vs_categorical` | yes | 2000 | 0.547 | `enumerated` |  |
| `bc7a766d1d3cb5cf` | `monthly_spend` | `satisfaction` | `numeric_vs_categorical` | yes | 1940 | 0.545 | `enumerated` |  |
| `cd4756fdb74795e4` | `monthly_spend` | `region` | `numeric_vs_categorical` | yes | 1920 | 0.545 | `enumerated` |  |
| `94742962070b954f` | `tenure_months` | `satisfaction` | `numeric_vs_categorical` | yes | 1910 | 0.545 | `enumerated` |  |
| `c51bb321343b3418` | `tenure_months` | `region` | `numeric_vs_categorical` | yes | 1891 | 0.544 | `enumerated` |  |
| `09075bbdee06b590` | `gender` | `satisfaction` | `categorical_vs_categorical` | yes | 1940 | 0.542 | `enumerated` |  |
| `14de521fe33b75ca` | `membership` | `satisfaction` | `categorical_vs_categorical` | yes | 1940 | 0.542 | `enumerated` |  |
| `20835424e3d80610` | `gender` | `region` | `categorical_vs_categorical` | yes | 1920 | 0.542 | `enumerated` |  |
| `45a586a2365b5b50` | `membership` | `region` | `categorical_vs_categorical` | yes | 1920 | 0.542 | `enumerated` |  |
| `d7608ad2d2f5e161` | `age` | `satisfaction` | `numeric_vs_categorical` | yes | 1806 | 0.542 | `enumerated` |  |
| `0688a4be09061aef` | `age` | `region` | `numeric_vs_categorical` | yes | 1786 | 0.541 | `enumerated` |  |
| `804b1d1596932157` | `income` | `satisfaction` | `numeric_vs_categorical` | yes | 1787 | 0.541 | `enumerated` |  |
| `966e9b46398be99d` | `income` | `region` | `numeric_vs_categorical` | yes | 1770 | 0.541 | `enumerated` |  |
| `69b4b3386d0d8c6a` | `region` | `satisfaction` | `categorical_vs_categorical` | yes | 1862 | 0.540 | `enumerated` |  |
