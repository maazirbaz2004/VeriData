# Phase 2 Hypothesis Set — `insurance`

## Family Manifest Summary
- **Mode:** `exhaustive` (effective: `exhaustive`)
- **Target:** `charges`
- **Columns:** `7` eligible / `7` total
- **Candidate Hypotheses:** `21`
- **Planned Family Size (`m`):** `21` feasible (`0` infeasible, `0` pruned)
- **LLM Used:** `False`
- **Selection Inputs Hash:** `89bdbeb7872f17d9`

### Planned Tests by Relationship Type
- `categorical_vs_categorical`: `6`
- `numeric_vs_binary`: `6`
- `numeric_vs_categorical`: `6`
- `numeric_vs_numeric`: `3`

## Hypotheses (Ordered by Outcome-Independent Priority)

| ID | Column A | Column B | Relationship | Feasible | n_complete | Priority | Source | Rationale |
| :--- | :--- | :--- | :--- | :---: | ---: | ---: | :--- | :--- |
| `dbbefcba4507014b` | `charges` | `smoker` | `numeric_vs_binary` | yes | 1337 | 0.875 | `enumerated` |  |
| `fc87f82acb437423` | `charges` | `sex` | `numeric_vs_binary` | yes | 1337 | 0.875 | `enumerated` |  |
| `7879d2e98b9f3fc3` | `bmi` | `charges` | `numeric_vs_numeric` | yes | 1337 | 0.855 | `enumerated` |  |
| `9ceff6678f472d3a` | `age` | `charges` | `numeric_vs_numeric` | yes | 1337 | 0.855 | `enumerated` |  |
| `cbc355b43e0dd6f9` | `charges` | `region` | `numeric_vs_categorical` | yes | 1337 | 0.851 | `enumerated` |  |
| `03088ab28e083960` | `charges` | `children` | `numeric_vs_categorical` | yes | 1337 | 0.843 | `enumerated` |  |
| `14b21894518babf6` | `bmi` | `smoker` | `numeric_vs_binary` | yes | 1337 | 0.575 | `enumerated` |  |
| `15d74a366b0a3bca` | `age` | `sex` | `numeric_vs_binary` | yes | 1337 | 0.575 | `enumerated` |  |
| `2cb47aca909f72e8` | `sex` | `smoker` | `categorical_vs_categorical` | yes | 1337 | 0.575 | `enumerated` |  |
| `6cebb444aca418b8` | `age` | `smoker` | `numeric_vs_binary` | yes | 1337 | 0.575 | `enumerated` |  |
| `b6b08a817c661487` | `bmi` | `sex` | `numeric_vs_binary` | yes | 1337 | 0.575 | `enumerated` |  |
| `4c3d52697add8a19` | `age` | `bmi` | `numeric_vs_numeric` | yes | 1337 | 0.555 | `enumerated` |  |
| `0688a4be09061aef` | `age` | `region` | `numeric_vs_categorical` | yes | 1337 | 0.551 | `enumerated` |  |
| `5da20203ad979461` | `bmi` | `region` | `numeric_vs_categorical` | yes | 1337 | 0.551 | `enumerated` |  |
| `093844d87e3c6328` | `region` | `sex` | `categorical_vs_categorical` | yes | 1337 | 0.547 | `enumerated` |  |
| `8c16745ee5780c67` | `region` | `smoker` | `categorical_vs_categorical` | yes | 1337 | 0.547 | `enumerated` |  |
| `cb56fc08a3e6f85a` | `bmi` | `children` | `numeric_vs_categorical` | yes | 1337 | 0.543 | `enumerated` |  |
| `d428bc651c8a9989` | `age` | `children` | `numeric_vs_categorical` | yes | 1337 | 0.543 | `enumerated` |  |
| `04e49dc5789ba544` | `children` | `sex` | `categorical_vs_categorical` | yes | 1337 | 0.541 | `enumerated` |  |
| `16934eaf6eb36cff` | `children` | `smoker` | `categorical_vs_categorical` | yes | 1337 | 0.541 | `enumerated` |  |
| `c1347eda564dedc3` | `children` | `region` | `categorical_vs_categorical` | yes | 1337 | 0.541 | `enumerated` |  |
