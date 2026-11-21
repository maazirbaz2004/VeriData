# Phase 2 Hypothesis Set — `telco_churn`

## Family Manifest Summary
- **Mode:** `exhaustive` (effective: `exhaustive`)
- **Target:** `Churn`
- **Columns:** `20` eligible / `21` total
- **Candidate Hypotheses:** `190`
- **Planned Family Size (`m`):** `190` feasible (`0` infeasible, `0` pruned)
- **LLM Used:** `False`
- **Selection Inputs Hash:** `c6cfd36f286069e4`

### Planned Tests by Relationship Type
- `categorical_vs_categorical`: `136`
- `numeric_vs_binary`: `21`
- `numeric_vs_categorical`: `30`
- `numeric_vs_numeric`: `3`

### Excluded Columns
- `customerID`: id

## Hypotheses (Ordered by Outcome-Independent Priority)

| ID | Column A | Column B | Relationship | Feasible | n_complete | Priority | Source | Rationale |
| :--- | :--- | :--- | :--- | :---: | ---: | ---: | :--- | :--- |
| `0c79dbf2d0a2072d` | `Churn` | `Dependents` | `categorical_vs_categorical` | yes | 7043 | 0.875 | `enumerated` |  |
| `10c792f41c6d0ec9` | `Churn` | `gender` | `categorical_vs_categorical` | yes | 7043 | 0.875 | `enumerated` |  |
| `43437db2843fdb44` | `Churn` | `PaperlessBilling` | `categorical_vs_categorical` | yes | 7043 | 0.875 | `enumerated` |  |
| `4a90acdb451d31e8` | `tenure` | `Churn` | `numeric_vs_binary` | yes | 7043 | 0.875 | `enumerated` |  |
| `529269e3e4b3fd5c` | `Churn` | `PhoneService` | `categorical_vs_categorical` | yes | 7043 | 0.875 | `enumerated` |  |
| `631194137900c1a1` | `MonthlyCharges` | `Churn` | `numeric_vs_binary` | yes | 7043 | 0.875 | `enumerated` |  |
| `c091961e0b42faef` | `Churn` | `Partner` | `categorical_vs_categorical` | yes | 7043 | 0.875 | `enumerated` |  |
| `d8aeb3c1c6542c44` | `Churn` | `SeniorCitizen` | `categorical_vs_categorical` | yes | 7043 | 0.875 | `enumerated` |  |
| `887d7cff73ac4ece` | `TotalCharges` | `Churn` | `numeric_vs_binary` | yes | 7032 | 0.875 | `enumerated` |  |
| `004071338b45c5f8` | `Churn` | `TechSupport` | `categorical_vs_categorical` | yes | 7043 | 0.850 | `enumerated` |  |
| `346155120ddb5eb0` | `Churn` | `DeviceProtection` | `categorical_vs_categorical` | yes | 7043 | 0.850 | `enumerated` |  |
| `70d795063cfb3eda` | `Churn` | `Contract` | `categorical_vs_categorical` | yes | 7043 | 0.850 | `enumerated` |  |
| `9709c6528dcbeddd` | `Churn` | `OnlineSecurity` | `categorical_vs_categorical` | yes | 7043 | 0.850 | `enumerated` |  |
| `9ff772a6f9cda252` | `Churn` | `StreamingTV` | `categorical_vs_categorical` | yes | 7043 | 0.850 | `enumerated` |  |
| `a8ab5aa270fefeea` | `Churn` | `MultipleLines` | `categorical_vs_categorical` | yes | 7043 | 0.850 | `enumerated` |  |
| `b2c7e8098ed7d370` | `Churn` | `OnlineBackup` | `categorical_vs_categorical` | yes | 7043 | 0.850 | `enumerated` |  |
| `cdb679793c7c215e` | `Churn` | `InternetService` | `categorical_vs_categorical` | yes | 7043 | 0.850 | `enumerated` |  |
| `dccc7035db88ac5d` | `Churn` | `StreamingMovies` | `categorical_vs_categorical` | yes | 7043 | 0.850 | `enumerated` |  |
| `dd216ddc9ff2517d` | `Churn` | `PaymentMethod` | `categorical_vs_categorical` | yes | 7043 | 0.847 | `enumerated` |  |
| `08f6ad745bad7bef` | `PaperlessBilling` | `SeniorCitizen` | `categorical_vs_categorical` | yes | 7043 | 0.575 | `enumerated` |  |
| `1843d4e0179f69e8` | `PaperlessBilling` | `Partner` | `categorical_vs_categorical` | yes | 7043 | 0.575 | `enumerated` |  |
| `18bc5712b8004a98` | `MonthlyCharges` | `gender` | `numeric_vs_binary` | yes | 7043 | 0.575 | `enumerated` |  |
| `23c72f48fe43e56d` | `MonthlyCharges` | `Partner` | `numeric_vs_binary` | yes | 7043 | 0.575 | `enumerated` |  |
| `28da644fb502b33c` | `MonthlyCharges` | `Dependents` | `numeric_vs_binary` | yes | 7043 | 0.575 | `enumerated` |  |
| `2c142d543cc868fe` | `Dependents` | `gender` | `categorical_vs_categorical` | yes | 7043 | 0.575 | `enumerated` |  |
| `361467c4ec24db34` | `tenure` | `Dependents` | `numeric_vs_binary` | yes | 7043 | 0.575 | `enumerated` |  |
| `4806be6cdeb24a26` | `PhoneService` | `gender` | `categorical_vs_categorical` | yes | 7043 | 0.575 | `enumerated` |  |
| `537a077824254cfa` | `Dependents` | `PaperlessBilling` | `categorical_vs_categorical` | yes | 7043 | 0.575 | `enumerated` |  |
| `6778122c3e4fc497` | `tenure` | `SeniorCitizen` | `numeric_vs_binary` | yes | 7043 | 0.575 | `enumerated` |  |
| `6939a0baf585fd21` | `tenure` | `PhoneService` | `numeric_vs_binary` | yes | 7043 | 0.575 | `enumerated` |  |
| `74ddd4374080345d` | `MonthlyCharges` | `PhoneService` | `numeric_vs_binary` | yes | 7043 | 0.575 | `enumerated` |  |
| `7ad5a6ac64d676e6` | `MonthlyCharges` | `PaperlessBilling` | `numeric_vs_binary` | yes | 7043 | 0.575 | `enumerated` |  |
| `7c5a74ad832ce4c1` | `Dependents` | `PhoneService` | `categorical_vs_categorical` | yes | 7043 | 0.575 | `enumerated` |  |
| `821a84248cb6ebb1` | `PaperlessBilling` | `PhoneService` | `categorical_vs_categorical` | yes | 7043 | 0.575 | `enumerated` |  |
| `9bf7110a8d9e370b` | `SeniorCitizen` | `gender` | `categorical_vs_categorical` | yes | 7043 | 0.575 | `enumerated` |  |
| `9eab1a6b763c37ff` | `PaperlessBilling` | `gender` | `categorical_vs_categorical` | yes | 7043 | 0.575 | `enumerated` |  |
| `a4a82c11a90be518` | `Partner` | `PhoneService` | `categorical_vs_categorical` | yes | 7043 | 0.575 | `enumerated` |  |
| `b1ea5309b1d452f1` | `Partner` | `SeniorCitizen` | `categorical_vs_categorical` | yes | 7043 | 0.575 | `enumerated` |  |
| `bb1b1acb50fb6df1` | `Partner` | `gender` | `categorical_vs_categorical` | yes | 7043 | 0.575 | `enumerated` |  |
| `bd2ed7b8e9c76306` | `Dependents` | `Partner` | `categorical_vs_categorical` | yes | 7043 | 0.575 | `enumerated` |  |
| `bdf5c8ba8c568de7` | `tenure` | `Partner` | `numeric_vs_binary` | yes | 7043 | 0.575 | `enumerated` |  |
| `cee9c2352e5e8ad1` | `tenure` | `gender` | `numeric_vs_binary` | yes | 7043 | 0.575 | `enumerated` |  |
| `d9a0eee5ac2ce6a2` | `tenure` | `PaperlessBilling` | `numeric_vs_binary` | yes | 7043 | 0.575 | `enumerated` |  |
| `f22a6924d91c45c2` | `Dependents` | `SeniorCitizen` | `categorical_vs_categorical` | yes | 7043 | 0.575 | `enumerated` |  |
| `f585ae9a9539affe` | `MonthlyCharges` | `SeniorCitizen` | `numeric_vs_binary` | yes | 7043 | 0.575 | `enumerated` |  |
| `f931c9fdd1314ce2` | `PhoneService` | `SeniorCitizen` | `categorical_vs_categorical` | yes | 7043 | 0.575 | `enumerated` |  |
| `4dfc4509fa156244` | `TotalCharges` | `Partner` | `numeric_vs_binary` | yes | 7032 | 0.575 | `enumerated` |  |
| `8ccf10a6ffa520bb` | `TotalCharges` | `Dependents` | `numeric_vs_binary` | yes | 7032 | 0.575 | `enumerated` |  |
| `935856fe3f3b4d53` | `TotalCharges` | `SeniorCitizen` | `numeric_vs_binary` | yes | 7032 | 0.575 | `enumerated` |  |
| `d1a0de4e5c51e51f` | `TotalCharges` | `PaperlessBilling` | `numeric_vs_binary` | yes | 7032 | 0.575 | `enumerated` |  |
| `ed911188cb8d94c5` | `TotalCharges` | `PhoneService` | `numeric_vs_binary` | yes | 7032 | 0.575 | `enumerated` |  |
| `fa5dca72681292b8` | `TotalCharges` | `gender` | `numeric_vs_binary` | yes | 7032 | 0.575 | `enumerated` |  |
| `02ba36a7b9381004` | `tenure` | `TechSupport` | `numeric_vs_categorical` | yes | 7043 | 0.555 | `enumerated` |  |
| `02ebdafda1bd3364` | `tenure` | `MultipleLines` | `numeric_vs_categorical` | yes | 7043 | 0.555 | `enumerated` |  |
| `39ff607798f90a1f` | `tenure` | `OnlineSecurity` | `numeric_vs_categorical` | yes | 7043 | 0.555 | `enumerated` |  |
| `3b54e233c0128493` | `MonthlyCharges` | `tenure` | `numeric_vs_numeric` | yes | 7043 | 0.555 | `enumerated` |  |
| `596311c57edced62` | `MonthlyCharges` | `DeviceProtection` | `numeric_vs_categorical` | yes | 7043 | 0.555 | `enumerated` |  |
| `5ca49b5911beb12c` | `tenure` | `DeviceProtection` | `numeric_vs_categorical` | yes | 7043 | 0.555 | `enumerated` |  |
| `7d819c1e68b96d19` | `tenure` | `StreamingTV` | `numeric_vs_categorical` | yes | 7043 | 0.555 | `enumerated` |  |
| `8dc4c345daf34a1d` | `MonthlyCharges` | `TechSupport` | `numeric_vs_categorical` | yes | 7043 | 0.555 | `enumerated` |  |
| `a01bd5c8ee99e9a4` | `MonthlyCharges` | `StreamingMovies` | `numeric_vs_categorical` | yes | 7043 | 0.555 | `enumerated` |  |
| `a03891449f04e25e` | `tenure` | `OnlineBackup` | `numeric_vs_categorical` | yes | 7043 | 0.555 | `enumerated` |  |
| `a3e17fa9e15818ac` | `tenure` | `InternetService` | `numeric_vs_categorical` | yes | 7043 | 0.555 | `enumerated` |  |
| `b2f2199668be5461` | `tenure` | `StreamingMovies` | `numeric_vs_categorical` | yes | 7043 | 0.555 | `enumerated` |  |
| `d7097c3aa1223380` | `MonthlyCharges` | `OnlineSecurity` | `numeric_vs_categorical` | yes | 7043 | 0.555 | `enumerated` |  |
| `e97402e7d7545670` | `MonthlyCharges` | `Contract` | `numeric_vs_categorical` | yes | 7043 | 0.555 | `enumerated` |  |
| `f10a664ad5ae5efd` | `MonthlyCharges` | `StreamingTV` | `numeric_vs_categorical` | yes | 7043 | 0.555 | `enumerated` |  |
| `f5144243f2831548` | `MonthlyCharges` | `InternetService` | `numeric_vs_categorical` | yes | 7043 | 0.555 | `enumerated` |  |
| `f52b34ac378b3d85` | `MonthlyCharges` | `OnlineBackup` | `numeric_vs_categorical` | yes | 7043 | 0.555 | `enumerated` |  |
| `f84756eb78b8a2c0` | `MonthlyCharges` | `MultipleLines` | `numeric_vs_categorical` | yes | 7043 | 0.555 | `enumerated` |  |
| `feb03e3a997c5683` | `tenure` | `Contract` | `numeric_vs_categorical` | yes | 7043 | 0.555 | `enumerated` |  |
| `13a009fb47e81c21` | `TotalCharges` | `TechSupport` | `numeric_vs_categorical` | yes | 7032 | 0.555 | `enumerated` |  |
| `2cf1f95489ceb976` | `TotalCharges` | `StreamingMovies` | `numeric_vs_categorical` | yes | 7032 | 0.555 | `enumerated` |  |
| `3898a8f79bb14302` | `TotalCharges` | `StreamingTV` | `numeric_vs_categorical` | yes | 7032 | 0.555 | `enumerated` |  |
| `3ad808322aec7e11` | `TotalCharges` | `tenure` | `numeric_vs_numeric` | yes | 7032 | 0.555 | `enumerated` |  |
| `44d86c3b7a4241c2` | `TotalCharges` | `Contract` | `numeric_vs_categorical` | yes | 7032 | 0.555 | `enumerated` |  |
| `6c475fd23dfa72c4` | `TotalCharges` | `DeviceProtection` | `numeric_vs_categorical` | yes | 7032 | 0.555 | `enumerated` |  |
| `6ffa3476104c6ba0` | `TotalCharges` | `OnlineBackup` | `numeric_vs_categorical` | yes | 7032 | 0.555 | `enumerated` |  |
| `8228abaa14d91582` | `TotalCharges` | `MultipleLines` | `numeric_vs_categorical` | yes | 7032 | 0.555 | `enumerated` |  |
| `8530374cc19cefc1` | `TotalCharges` | `InternetService` | `numeric_vs_categorical` | yes | 7032 | 0.555 | `enumerated` |  |
| `e03ed1d4bb7a47d8` | `TotalCharges` | `OnlineSecurity` | `numeric_vs_categorical` | yes | 7032 | 0.555 | `enumerated` |  |
| `e5022cb700228461` | `MonthlyCharges` | `TotalCharges` | `numeric_vs_numeric` | yes | 7032 | 0.555 | `enumerated` |  |
| `01c5b375291cde1e` | `tenure` | `PaymentMethod` | `numeric_vs_categorical` | yes | 7043 | 0.551 | `enumerated` |  |
| `1999f2288847bb2b` | `MonthlyCharges` | `PaymentMethod` | `numeric_vs_categorical` | yes | 7043 | 0.551 | `enumerated` |  |
| `416c4acccbc3aa0b` | `TotalCharges` | `PaymentMethod` | `numeric_vs_categorical` | yes | 7032 | 0.551 | `enumerated` |  |
| `00fce16491ccf371` | `Contract` | `StreamingMovies` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `0114269a3fd5d1bf` | `OnlineSecurity` | `PaperlessBilling` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `033c8b8b2b003387` | `MultipleLines` | `StreamingMovies` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `08c1f44b1ce82523` | `OnlineBackup` | `PaperlessBilling` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `0bc6ca6971011f0c` | `Contract` | `OnlineSecurity` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `11fd40d580a970e3` | `Contract` | `MultipleLines` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `13a10641f027369a` | `OnlineBackup` | `StreamingTV` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `153e2caea2390573` | `Partner` | `StreamingTV` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `19a0194e87ce14a6` | `OnlineSecurity` | `TechSupport` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `1af07d4a36636b1b` | `MultipleLines` | `gender` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `1b7c28e9a61f9ee0` | `Contract` | `Dependents` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `1da4c93b7e6d39e1` | `OnlineBackup` | `OnlineSecurity` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `2239fb742177f8c8` | `Dependents` | `TechSupport` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `2463455b7a0388e6` | `InternetService` | `StreamingMovies` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `2563ab96e5b676e3` | `InternetService` | `StreamingTV` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `2616c37a64ebbc9b` | `DeviceProtection` | `Partner` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `274a32d0fa4d7a27` | `MultipleLines` | `StreamingTV` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `2ab0d13c6a970c95` | `MultipleLines` | `PhoneService` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `2cc96175d427c976` | `Dependents` | `StreamingTV` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `324ec7360c7c9674` | `InternetService` | `MultipleLines` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `348470ac5b730fe5` | `OnlineSecurity` | `StreamingMovies` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `3705ab22484af512` | `OnlineSecurity` | `PhoneService` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `37912b7339e9c029` | `Contract` | `PhoneService` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `394ce7fb8751f8c3` | `OnlineBackup` | `TechSupport` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `3a73efa245b091cf` | `Dependents` | `OnlineSecurity` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `3ccf0a38f8a49cca` | `DeviceProtection` | `OnlineSecurity` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `3db10fc8b55a88e3` | `DeviceProtection` | `PaperlessBilling` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `3e9e33034bd0ce13` | `SeniorCitizen` | `StreamingTV` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `3f926e31b9db9efb` | `InternetService` | `gender` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `4066c234dff6e9b7` | `OnlineBackup` | `SeniorCitizen` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `40b4ef38fb223d82` | `PhoneService` | `StreamingMovies` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `4129803e79d4b3d2` | `StreamingTV` | `gender` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `41efd16bb00b01b5` | `Contract` | `TechSupport` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `452ac44b83732dfe` | `StreamingTV` | `TechSupport` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `462dcf635331c428` | `DeviceProtection` | `OnlineBackup` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `4a31857362168276` | `MultipleLines` | `TechSupport` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `5c8ab0a4c78018ee` | `OnlineBackup` | `StreamingMovies` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `5fc92aff1a7ece2f` | `DeviceProtection` | `gender` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `61db1bd96e1c941d` | `DeviceProtection` | `PhoneService` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `64f3b53675773903` | `MultipleLines` | `OnlineSecurity` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `6983aa40b3a3e005` | `DeviceProtection` | `StreamingMovies` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `6c350284d1776c2c` | `Dependents` | `InternetService` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `6d58f0dcb9d78efb` | `InternetService` | `SeniorCitizen` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `6ed43add85a5c304` | `MultipleLines` | `OnlineBackup` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `714422e1d8e7ae7a` | `PaperlessBilling` | `TechSupport` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `7368c7a6006bb1ea` | `StreamingMovies` | `TechSupport` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `848cc416d641778f` | `OnlineSecurity` | `SeniorCitizen` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `84f9f37ddb224d3f` | `OnlineSecurity` | `gender` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `8e13ab70f1ba11da` | `Contract` | `StreamingTV` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `8fe18222df8a9429` | `SeniorCitizen` | `StreamingMovies` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `94987362ca8c05d7` | `Contract` | `SeniorCitizen` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `975b8cabeb4017b0` | `Contract` | `PaperlessBilling` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `979865ae778a075a` | `OnlineBackup` | `Partner` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `981cff5f7a215d19` | `PaperlessBilling` | `StreamingTV` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `a0998c232fd9d494` | `Contract` | `gender` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `a72cd470e6363ee8` | `InternetService` | `Partner` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `b24e02a04a032290` | `InternetService` | `OnlineBackup` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `b400db5b1782ac0f` | `PhoneService` | `StreamingTV` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `b4e3227fd5609648` | `InternetService` | `TechSupport` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `b61112d60046cde6` | `Dependents` | `MultipleLines` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `b66b0e87135f91b6` | `MultipleLines` | `PaperlessBilling` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `b698c9a144e8988b` | `OnlineBackup` | `gender` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `b959daf0d5cf8c3e` | `OnlineSecurity` | `StreamingTV` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `b9bfbf5bfa332d73` | `DeviceProtection` | `InternetService` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `c1c00d6f1586c56f` | `DeviceProtection` | `StreamingTV` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `c70d9a30ad3a759f` | `Contract` | `InternetService` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `c994c99c1be60bbc` | `Dependents` | `OnlineBackup` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `cb1b4f5249ce72cd` | `Dependents` | `StreamingMovies` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `ccd56726c0186a89` | `PaperlessBilling` | `StreamingMovies` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `cd6a71803b968df6` | `OnlineSecurity` | `Partner` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `ce555959104ae5eb` | `Contract` | `DeviceProtection` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `ceb061e38724fdc6` | `OnlineBackup` | `PhoneService` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `cf00b739bd43a631` | `Partner` | `TechSupport` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `cf9593294dd2606b` | `Contract` | `Partner` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `d1069a4a2669a614` | `InternetService` | `PaperlessBilling` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `d53613431a44d867` | `DeviceProtection` | `MultipleLines` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `d989ff8da27e3c98` | `TechSupport` | `gender` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `db19e8c44cb69cf1` | `InternetService` | `PhoneService` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `dc1dbe320251d420` | `DeviceProtection` | `TechSupport` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `e6686ce76c4e3d5a` | `MultipleLines` | `Partner` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `e82a99a2057375c9` | `DeviceProtection` | `SeniorCitizen` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `ef4ffd0e980ccdea` | `SeniorCitizen` | `TechSupport` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `f5a0e5abc47bbcdb` | `Contract` | `OnlineBackup` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `f6451ce76918451c` | `StreamingMovies` | `StreamingTV` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `f6897534e4ade931` | `PhoneService` | `TechSupport` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `f897ab3c87e57ef2` | `MultipleLines` | `SeniorCitizen` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `f9f59d6443b0306f` | `Dependents` | `DeviceProtection` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `faa2137efcbb922c` | `InternetService` | `OnlineSecurity` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `fd17f750ea79f2f1` | `StreamingMovies` | `gender` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `ffecdc35ac621a0a` | `Partner` | `StreamingMovies` | `categorical_vs_categorical` | yes | 7043 | 0.550 | `enumerated` |  |
| `061277d6cdc09e76` | `PaperlessBilling` | `PaymentMethod` | `categorical_vs_categorical` | yes | 7043 | 0.547 | `enumerated` |  |
| `070ca34173a28625` | `Contract` | `PaymentMethod` | `categorical_vs_categorical` | yes | 7043 | 0.547 | `enumerated` |  |
| `1f91a6dd05b07726` | `PaymentMethod` | `StreamingMovies` | `categorical_vs_categorical` | yes | 7043 | 0.547 | `enumerated` |  |
| `212641ca4942b1a9` | `DeviceProtection` | `PaymentMethod` | `categorical_vs_categorical` | yes | 7043 | 0.547 | `enumerated` |  |
| `30543f3b6b059a20` | `MultipleLines` | `PaymentMethod` | `categorical_vs_categorical` | yes | 7043 | 0.547 | `enumerated` |  |
| `571f4016ee69f470` | `PaymentMethod` | `PhoneService` | `categorical_vs_categorical` | yes | 7043 | 0.547 | `enumerated` |  |
| `642a218ee38ff83d` | `PaymentMethod` | `SeniorCitizen` | `categorical_vs_categorical` | yes | 7043 | 0.547 | `enumerated` |  |
| `6bcfe1df05379a17` | `PaymentMethod` | `StreamingTV` | `categorical_vs_categorical` | yes | 7043 | 0.547 | `enumerated` |  |
| `9ddf1916ee363431` | `PaymentMethod` | `gender` | `categorical_vs_categorical` | yes | 7043 | 0.547 | `enumerated` |  |
| `bcecd2bd8f2cfb5e` | `OnlineBackup` | `PaymentMethod` | `categorical_vs_categorical` | yes | 7043 | 0.547 | `enumerated` |  |
| `e702cc780a1c4f70` | `Dependents` | `PaymentMethod` | `categorical_vs_categorical` | yes | 7043 | 0.547 | `enumerated` |  |
| `ea5904cd72634faa` | `PaymentMethod` | `TechSupport` | `categorical_vs_categorical` | yes | 7043 | 0.547 | `enumerated` |  |
| `ec89c380b28346d8` | `OnlineSecurity` | `PaymentMethod` | `categorical_vs_categorical` | yes | 7043 | 0.547 | `enumerated` |  |
| `f0c3049b524b87f5` | `Partner` | `PaymentMethod` | `categorical_vs_categorical` | yes | 7043 | 0.547 | `enumerated` |  |
| `fbde1fc2a222cd7e` | `InternetService` | `PaymentMethod` | `categorical_vs_categorical` | yes | 7043 | 0.547 | `enumerated` |  |
