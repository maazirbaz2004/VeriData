# Phase 2 Hypothesis Set — `heart_disease`

## Family Manifest Summary
- **Mode:** `exhaustive` (effective: `exhaustive`)
- **Target:** `target`
- **Columns:** `14` eligible / `14` total
- **Candidate Hypotheses:** `91`
- **Planned Family Size (`m`):** `91` feasible (`0` infeasible, `0` pruned)
- **LLM Used:** `False`
- **Selection Inputs Hash:** `c94ee598b315d725`

### Planned Tests by Relationship Type
- `categorical_vs_categorical`: `36`
- `numeric_vs_binary`: `20`
- `numeric_vs_categorical`: `25`
- `numeric_vs_numeric`: `10`

## Hypotheses (Ordered by Outcome-Independent Priority)

| ID | Column A | Column B | Relationship | Feasible | n_complete | Priority | Source | Rationale |
| :--- | :--- | :--- | :--- | :---: | ---: | ---: | :--- | :--- |
| `6313494ec46b4786` | `trestbps` | `target` | `numeric_vs_binary` | yes | 302 | 0.826 | `enumerated` |  |
| `74224aeb42b21287` | `thalach` | `target` | `numeric_vs_binary` | yes | 302 | 0.826 | `enumerated` |  |
| `8e2c4c80da5d26b5` | `age` | `target` | `numeric_vs_binary` | yes | 302 | 0.826 | `enumerated` |  |
| `9f2a0af0e7967ea1` | `oldpeak` | `target` | `numeric_vs_binary` | yes | 302 | 0.826 | `enumerated` |  |
| `d23bbb095bbd8de7` | `chol` | `target` | `numeric_vs_binary` | yes | 302 | 0.826 | `enumerated` |  |
| `1182ef04d7df7222` | `fbs` | `target` | `categorical_vs_categorical` | yes | 302 | 0.776 | `enumerated` |  |
| `673d4317272093f8` | `sex` | `target` | `categorical_vs_categorical` | yes | 302 | 0.776 | `enumerated` |  |
| `bf51075ec4d71b4a` | `exang` | `target` | `categorical_vs_categorical` | yes | 302 | 0.776 | `enumerated` |  |
| `54ec5790ab126039` | `slope` | `target` | `categorical_vs_categorical` | yes | 302 | 0.751 | `enumerated` |  |
| `8887e7a3b102ccbe` | `restecg` | `target` | `categorical_vs_categorical` | yes | 298 | 0.749 | `enumerated` |  |
| `496919d9895a9042` | `cp` | `target` | `categorical_vs_categorical` | yes | 302 | 0.748 | `enumerated` |  |
| `32e0d578da3a13ad` | `target` | `thal` | `categorical_vs_categorical` | yes | 300 | 0.747 | `enumerated` |  |
| `6fa9bf323ac621ef` | `ca` | `target` | `categorical_vs_categorical` | yes | 298 | 0.743 | `enumerated` |  |
| `15d74a366b0a3bca` | `age` | `sex` | `numeric_vs_binary` | yes | 302 | 0.525 | `enumerated` |  |
| `168a622a260b3739` | `thalach` | `fbs` | `numeric_vs_binary` | yes | 302 | 0.525 | `enumerated` |  |
| `22259d00117a9537` | `trestbps` | `exang` | `numeric_vs_binary` | yes | 302 | 0.525 | `enumerated` |  |
| `27c11686fca6b5e7` | `thalach` | `sex` | `numeric_vs_binary` | yes | 302 | 0.525 | `enumerated` |  |
| `2b36dc9e7d8f7caa` | `oldpeak` | `fbs` | `numeric_vs_binary` | yes | 302 | 0.525 | `enumerated` |  |
| `555841e44ae8881f` | `chol` | `fbs` | `numeric_vs_binary` | yes | 302 | 0.525 | `enumerated` |  |
| `7410ef0067f7c441` | `trestbps` | `sex` | `numeric_vs_binary` | yes | 302 | 0.525 | `enumerated` |  |
| `8875db9ac835441c` | `chol` | `sex` | `numeric_vs_binary` | yes | 302 | 0.525 | `enumerated` |  |
| `951aec24050e3fbe` | `oldpeak` | `sex` | `numeric_vs_binary` | yes | 302 | 0.525 | `enumerated` |  |
| `9d70f42bf9117f60` | `oldpeak` | `exang` | `numeric_vs_binary` | yes | 302 | 0.525 | `enumerated` |  |
| `ae66ecee8bdad5f9` | `thalach` | `exang` | `numeric_vs_binary` | yes | 302 | 0.525 | `enumerated` |  |
| `c902026cb51f3bd5` | `age` | `fbs` | `numeric_vs_binary` | yes | 302 | 0.525 | `enumerated` |  |
| `e3a68cabe7f75fff` | `trestbps` | `fbs` | `numeric_vs_binary` | yes | 302 | 0.525 | `enumerated` |  |
| `f14c7f6ed6dc348f` | `chol` | `exang` | `numeric_vs_binary` | yes | 302 | 0.525 | `enumerated` |  |
| `fff30a9937f773bb` | `age` | `exang` | `numeric_vs_binary` | yes | 302 | 0.525 | `enumerated` |  |
| `48efdf5591bbba2e` | `trestbps` | `slope` | `numeric_vs_categorical` | yes | 302 | 0.505 | `enumerated` |  |
| `4e26e928b25387d9` | `age` | `slope` | `numeric_vs_categorical` | yes | 302 | 0.505 | `enumerated` |  |
| `9d7aac07fff6b6a5` | `oldpeak` | `slope` | `numeric_vs_categorical` | yes | 302 | 0.505 | `enumerated` |  |
| `a3e63721f1130cab` | `thalach` | `slope` | `numeric_vs_categorical` | yes | 302 | 0.505 | `enumerated` |  |
| `dc3a5484b07160cd` | `chol` | `slope` | `numeric_vs_categorical` | yes | 302 | 0.505 | `enumerated` |  |
| `00c2df6704f3e2e5` | `age` | `restecg` | `numeric_vs_categorical` | yes | 298 | 0.504 | `enumerated` |  |
| `06cf5703d611facd` | `oldpeak` | `restecg` | `numeric_vs_categorical` | yes | 298 | 0.504 | `enumerated` |  |
| `6997a4dd940727ac` | `thalach` | `restecg` | `numeric_vs_categorical` | yes | 298 | 0.504 | `enumerated` |  |
| `c7e15e32aec2f589` | `trestbps` | `restecg` | `numeric_vs_categorical` | yes | 298 | 0.504 | `enumerated` |  |
| `e38cc940bd8b149e` | `chol` | `restecg` | `numeric_vs_categorical` | yes | 298 | 0.504 | `enumerated` |  |
| `3d97ccf72ea9cf3c` | `oldpeak` | `cp` | `numeric_vs_categorical` | yes | 302 | 0.501 | `enumerated` |  |
| `b8f0be5ecbc57b86` | `age` | `cp` | `numeric_vs_categorical` | yes | 302 | 0.501 | `enumerated` |  |
| `c405f17c640df078` | `trestbps` | `cp` | `numeric_vs_categorical` | yes | 302 | 0.501 | `enumerated` |  |
| `d76e20a68929475d` | `thalach` | `cp` | `numeric_vs_categorical` | yes | 302 | 0.501 | `enumerated` |  |
| `e81b584b8df4cc80` | `chol` | `cp` | `numeric_vs_categorical` | yes | 302 | 0.501 | `enumerated` |  |
| `1763814c12595dab` | `trestbps` | `thal` | `numeric_vs_categorical` | yes | 300 | 0.501 | `enumerated` |  |
| `48604f70b7b38fea` | `oldpeak` | `thal` | `numeric_vs_categorical` | yes | 300 | 0.501 | `enumerated` |  |
| `5fc372ceb72e33da` | `age` | `thal` | `numeric_vs_categorical` | yes | 300 | 0.501 | `enumerated` |  |
| `ec0e003ac7b2ddec` | `chol` | `thal` | `numeric_vs_categorical` | yes | 300 | 0.501 | `enumerated` |  |
| `efa43d5f98308751` | `thalach` | `thal` | `numeric_vs_categorical` | yes | 300 | 0.501 | `enumerated` |  |
| `447ea78e0ef0b75d` | `oldpeak` | `ca` | `numeric_vs_categorical` | yes | 298 | 0.496 | `enumerated` |  |
| `54f1511906ca004b` | `age` | `ca` | `numeric_vs_categorical` | yes | 298 | 0.496 | `enumerated` |  |
| `776d90a8a90b87b8` | `trestbps` | `ca` | `numeric_vs_categorical` | yes | 298 | 0.496 | `enumerated` |  |
| `86e33f55f82beb55` | `chol` | `ca` | `numeric_vs_categorical` | yes | 298 | 0.496 | `enumerated` |  |
| `f8ae542b41b51ee2` | `thalach` | `ca` | `numeric_vs_categorical` | yes | 298 | 0.496 | `enumerated` |  |
| `32bef2e96e5dd083` | `fbs` | `sex` | `categorical_vs_categorical` | yes | 302 | 0.476 | `enumerated` |  |
| `3e6bc38aedea6573` | `exang` | `sex` | `categorical_vs_categorical` | yes | 302 | 0.476 | `enumerated` |  |
| `49d35b07d1df3f97` | `exang` | `fbs` | `categorical_vs_categorical` | yes | 302 | 0.476 | `enumerated` |  |
| `169b0f3c01cbbaaf` | `oldpeak` | `thalach` | `numeric_vs_numeric` | yes | 302 | 0.456 | `enumerated` |  |
| `2d3c9ec78fd0b7be` | `chol` | `thalach` | `numeric_vs_numeric` | yes | 302 | 0.456 | `enumerated` |  |
| `7167152658e09d7a` | `age` | `trestbps` | `numeric_vs_numeric` | yes | 302 | 0.456 | `enumerated` |  |
| `7cd3b40dd5161f06` | `age` | `thalach` | `numeric_vs_numeric` | yes | 302 | 0.456 | `enumerated` |  |
| `91e61c8ea1a5182f` | `chol` | `trestbps` | `numeric_vs_numeric` | yes | 302 | 0.456 | `enumerated` |  |
| `b970cec8f32df4d3` | `chol` | `oldpeak` | `numeric_vs_numeric` | yes | 302 | 0.456 | `enumerated` |  |
| `d7c654f5a7a64364` | `oldpeak` | `trestbps` | `numeric_vs_numeric` | yes | 302 | 0.456 | `enumerated` |  |
| `d950ec63635781aa` | `age` | `oldpeak` | `numeric_vs_numeric` | yes | 302 | 0.456 | `enumerated` |  |
| `e4fa2016ce124328` | `age` | `chol` | `numeric_vs_numeric` | yes | 302 | 0.456 | `enumerated` |  |
| `fc19cc5db1c88caa` | `thalach` | `trestbps` | `numeric_vs_numeric` | yes | 302 | 0.456 | `enumerated` |  |
| `27e906e7297b4994` | `fbs` | `slope` | `categorical_vs_categorical` | yes | 302 | 0.451 | `enumerated` |  |
| `465e2549ae2a9952` | `sex` | `slope` | `categorical_vs_categorical` | yes | 302 | 0.451 | `enumerated` |  |
| `9a96613fdb4d8d0e` | `exang` | `slope` | `categorical_vs_categorical` | yes | 302 | 0.451 | `enumerated` |  |
| `17b44780ad31d11e` | `restecg` | `slope` | `categorical_vs_categorical` | yes | 298 | 0.449 | `enumerated` |  |
| `2c97b1c16d3a2713` | `restecg` | `sex` | `categorical_vs_categorical` | yes | 298 | 0.449 | `enumerated` |  |
| `5f64885bc73c3639` | `exang` | `restecg` | `categorical_vs_categorical` | yes | 298 | 0.449 | `enumerated` |  |
| `d847b48efa012aae` | `fbs` | `restecg` | `categorical_vs_categorical` | yes | 298 | 0.449 | `enumerated` |  |
| `17ea714237e0f785` | `cp` | `sex` | `categorical_vs_categorical` | yes | 302 | 0.448 | `enumerated` |  |
| `8e66e9bf4a3efeb5` | `cp` | `fbs` | `categorical_vs_categorical` | yes | 302 | 0.448 | `enumerated` |  |
| `d0e7a430a36f3d86` | `cp` | `exang` | `categorical_vs_categorical` | yes | 302 | 0.448 | `enumerated` |  |
| `e419aabddcfb283e` | `cp` | `slope` | `categorical_vs_categorical` | yes | 302 | 0.448 | `enumerated` |  |
| `05dca115cd8e4a80` | `sex` | `thal` | `categorical_vs_categorical` | yes | 300 | 0.447 | `enumerated` |  |
| `5520ad43aa894075` | `fbs` | `thal` | `categorical_vs_categorical` | yes | 300 | 0.447 | `enumerated` |  |
| `59f26cb3f5ca5579` | `slope` | `thal` | `categorical_vs_categorical` | yes | 300 | 0.447 | `enumerated` |  |
| `99c8467482ea7d6e` | `exang` | `thal` | `categorical_vs_categorical` | yes | 300 | 0.447 | `enumerated` |  |
| `f292f649049c298e` | `cp` | `thal` | `categorical_vs_categorical` | yes | 300 | 0.447 | `enumerated` |  |
| `e7bebd9538cbd035` | `cp` | `restecg` | `categorical_vs_categorical` | yes | 298 | 0.446 | `enumerated` |  |
| `55b87669cbce335a` | `restecg` | `thal` | `categorical_vs_categorical` | yes | 296 | 0.445 | `enumerated` |  |
| `1bd2aaa3c70d911a` | `ca` | `exang` | `categorical_vs_categorical` | yes | 298 | 0.443 | `enumerated` |  |
| `360848ba25210d3e` | `ca` | `sex` | `categorical_vs_categorical` | yes | 298 | 0.443 | `enumerated` |  |
| `5d63cd654aaeccda` | `ca` | `slope` | `categorical_vs_categorical` | yes | 298 | 0.443 | `enumerated` |  |
| `c4e27ab9af1f5754` | `ca` | `fbs` | `categorical_vs_categorical` | yes | 298 | 0.443 | `enumerated` |  |
| `c8d61c2eee9c0b4e` | `ca` | `cp` | `categorical_vs_categorical` | yes | 298 | 0.443 | `enumerated` |  |
| `1a1df41325c3c128` | `ca` | `thal` | `categorical_vs_categorical` | yes | 296 | 0.442 | `enumerated` |  |
| `4411541b777b7271` | `ca` | `restecg` | `categorical_vs_categorical` | yes | 294 | 0.441 | `enumerated` |  |
