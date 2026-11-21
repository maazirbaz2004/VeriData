# Phase 2 Hypothesis Set — `bank_marketing`

## Family Manifest Summary
- **Mode:** `exhaustive` (effective: `exhaustive`)
- **Target:** `y`
- **Columns:** `21` eligible / `21` total
- **Candidate Hypotheses:** `210`
- **Planned Family Size (`m`):** `190` feasible (`20` infeasible, `0` pruned)
- **LLM Used:** `False`
- **Selection Inputs Hash:** `6ce5bdd77de69d9e`

### Planned Tests by Relationship Type
- `categorical_vs_categorical`: `55`
- `numeric_vs_binary`: `36`
- `numeric_vs_categorical`: `63`
- `numeric_vs_numeric`: `36`

## Hypotheses (Ordered by Outcome-Independent Priority)

| ID | Column A | Column B | Relationship | Feasible | n_complete | Priority | Source | Rationale |
| :--- | :--- | :--- | :--- | :---: | ---: | ---: | :--- | :--- |
| `1de11b538a568fbb` | `contact` | `y` | `categorical_vs_categorical` | yes | 41176 | 0.875 | `enumerated` |  |
| `22ca60c3298e2fca` | `emp.var.rate` | `y` | `numeric_vs_binary` | yes | 41176 | 0.875 | `enumerated` |  |
| `25e4a4b5c900ba52` | `age` | `y` | `numeric_vs_binary` | yes | 41176 | 0.875 | `enumerated` |  |
| `2d2ffd8e429c7a71` | `campaign` | `y` | `numeric_vs_binary` | yes | 41176 | 0.875 | `enumerated` |  |
| `383409f8a6f00350` | `euribor3m` | `y` | `numeric_vs_binary` | yes | 41176 | 0.875 | `enumerated` |  |
| `72957be8edc6e172` | `cons.conf.idx` | `y` | `numeric_vs_binary` | yes | 41176 | 0.875 | `enumerated` |  |
| `7ef75d210ec74993` | `cons.price.idx` | `y` | `numeric_vs_binary` | yes | 41176 | 0.875 | `enumerated` |  |
| `9d8db73ad4f37a95` | `pdays` | `y` | `numeric_vs_binary` | yes | 41176 | 0.875 | `enumerated` |  |
| `a02eadb08393ec4b` | `duration` | `y` | `numeric_vs_binary` | yes | 41176 | 0.875 | `enumerated` |  |
| `c0bfef47e9475026` | `nr.employed` | `y` | `numeric_vs_binary` | yes | 41176 | 0.875 | `enumerated` |  |
| `6d8644f105c5d376` | `housing` | `y` | `categorical_vs_categorical` | yes | 40186 | 0.874 | `enumerated` |  |
| `7b8836c7ae6c3bd3` | `loan` | `y` | `categorical_vs_categorical` | yes | 40186 | 0.874 | `enumerated` |  |
| `379f441494c0ea3e` | `poutcome` | `y` | `categorical_vs_categorical` | yes | 41176 | 0.850 | `enumerated` |  |
| `d2155c5cccd19e7d` | `marital` | `y` | `categorical_vs_categorical` | yes | 41096 | 0.850 | `enumerated` |  |
| `bbe80c5a0cd39b86` | `day_of_week` | `y` | `categorical_vs_categorical` | yes | 41176 | 0.844 | `enumerated` |  |
| `aed69aad2e9268ec` | `education` | `y` | `categorical_vs_categorical` | yes | 39446 | 0.836 | `enumerated` |  |
| `b495776abaf7016e` | `previous` | `y` | `categorical_vs_categorical` | yes | 41170 | 0.835 | `enumerated` |  |
| `32355cb111e489bd` | `month` | `y` | `categorical_vs_categorical` | yes | 41176 | 0.829 | `enumerated` |  |
| `5df43f3dd0ec9f1f` | `job` | `y` | `categorical_vs_categorical` | yes | 40846 | 0.826 | `enumerated` |  |
| `01bfd13fe7946d93` | `default` | `y` | `categorical_vs_categorical` | no | 32577 | 0.615 | `enumerated` | dropped_levels (< min_group_n=8): default:yes; degenerate: contingency table has < 2 rows or < 2 columns after filter |
| `29a66ad52ddf6209` | `pdays` | `contact` | `numeric_vs_binary` | yes | 41176 | 0.575 | `enumerated` |  |
| `783fac50a18154d5` | `duration` | `contact` | `numeric_vs_binary` | yes | 41176 | 0.575 | `enumerated` |  |
| `8d049cb2c8296235` | `emp.var.rate` | `contact` | `numeric_vs_binary` | yes | 41176 | 0.575 | `enumerated` |  |
| `90f2230f715254c0` | `cons.price.idx` | `contact` | `numeric_vs_binary` | yes | 41176 | 0.575 | `enumerated` |  |
| `a299d5a55f3461ad` | `euribor3m` | `contact` | `numeric_vs_binary` | yes | 41176 | 0.575 | `enumerated` |  |
| `c505f1a5244a3875` | `cons.conf.idx` | `contact` | `numeric_vs_binary` | yes | 41176 | 0.575 | `enumerated` |  |
| `d32c96ace032a713` | `age` | `contact` | `numeric_vs_binary` | yes | 41176 | 0.575 | `enumerated` |  |
| `d9eda995163402d0` | `campaign` | `contact` | `numeric_vs_binary` | yes | 41176 | 0.575 | `enumerated` |  |
| `da79bd9e61ee8f7a` | `nr.employed` | `contact` | `numeric_vs_binary` | yes | 41176 | 0.575 | `enumerated` |  |
| `00d43c29f6de4bd6` | `age` | `loan` | `numeric_vs_binary` | yes | 40186 | 0.574 | `enumerated` |  |
| `0a06877c850e0d5b` | `contact` | `loan` | `categorical_vs_categorical` | yes | 40186 | 0.574 | `enumerated` |  |
| `115d47cfc3ca23ae` | `emp.var.rate` | `housing` | `numeric_vs_binary` | yes | 40186 | 0.574 | `enumerated` |  |
| `1c48f44dc7005116` | `pdays` | `loan` | `numeric_vs_binary` | yes | 40186 | 0.574 | `enumerated` |  |
| `2f7dc9d966d94a64` | `cons.conf.idx` | `housing` | `numeric_vs_binary` | yes | 40186 | 0.574 | `enumerated` |  |
| `3137f24fe0c7ba70` | `duration` | `housing` | `numeric_vs_binary` | yes | 40186 | 0.574 | `enumerated` |  |
| `388095fb1203059b` | `pdays` | `housing` | `numeric_vs_binary` | yes | 40186 | 0.574 | `enumerated` |  |
| `5b2164c3d80ebddf` | `euribor3m` | `housing` | `numeric_vs_binary` | yes | 40186 | 0.574 | `enumerated` |  |
| `66966e60da2d5db6` | `cons.price.idx` | `housing` | `numeric_vs_binary` | yes | 40186 | 0.574 | `enumerated` |  |
| `79e7a9af0143dc19` | `duration` | `loan` | `numeric_vs_binary` | yes | 40186 | 0.574 | `enumerated` |  |
| `92fd4e0256c2d49d` | `nr.employed` | `loan` | `numeric_vs_binary` | yes | 40186 | 0.574 | `enumerated` |  |
| `9c1c3f00109083bd` | `emp.var.rate` | `loan` | `numeric_vs_binary` | yes | 40186 | 0.574 | `enumerated` |  |
| `a61970bef637c077` | `nr.employed` | `housing` | `numeric_vs_binary` | yes | 40186 | 0.574 | `enumerated` |  |
| `be223b5d36d57432` | `age` | `housing` | `numeric_vs_binary` | yes | 40186 | 0.574 | `enumerated` |  |
| `c326f3ea5a9a7fea` | `campaign` | `housing` | `numeric_vs_binary` | yes | 40186 | 0.574 | `enumerated` |  |
| `cccdf3228104977e` | `euribor3m` | `loan` | `numeric_vs_binary` | yes | 40186 | 0.574 | `enumerated` |  |
| `dba09cbc62731904` | `contact` | `housing` | `categorical_vs_categorical` | yes | 40186 | 0.574 | `enumerated` |  |
| `e1023a4032448d76` | `cons.price.idx` | `loan` | `numeric_vs_binary` | yes | 40186 | 0.574 | `enumerated` |  |
| `f6a3958fdf8e177f` | `cons.conf.idx` | `loan` | `numeric_vs_binary` | yes | 40186 | 0.574 | `enumerated` |  |
| `f9eb7c54573c17f7` | `campaign` | `loan` | `numeric_vs_binary` | yes | 40186 | 0.574 | `enumerated` |  |
| `1a40f8075628fc13` | `housing` | `loan` | `categorical_vs_categorical` | yes | 40186 | 0.573 | `enumerated` |  |
| `00d05cc952dbead8` | `cons.conf.idx` | `euribor3m` | `numeric_vs_numeric` | yes | 41176 | 0.555 | `enumerated` |  |
| `0371bb242191333d` | `cons.price.idx` | `emp.var.rate` | `numeric_vs_numeric` | yes | 41176 | 0.555 | `enumerated` |  |
| `03a10a947322ffa7` | `emp.var.rate` | `pdays` | `numeric_vs_numeric` | yes | 41176 | 0.555 | `enumerated` |  |
| `05b3edf395b073ad` | `cons.conf.idx` | `pdays` | `numeric_vs_numeric` | yes | 41176 | 0.555 | `enumerated` |  |
| `0afa643aec945a47` | `euribor3m` | `pdays` | `numeric_vs_numeric` | yes | 41176 | 0.555 | `enumerated` |  |
| `0d88d801b4f751ec` | `emp.var.rate` | `poutcome` | `numeric_vs_categorical` | yes | 41176 | 0.555 | `enumerated` |  |
| `0f31f0230c932d2f` | `duration` | `pdays` | `numeric_vs_numeric` | yes | 41176 | 0.555 | `enumerated` |  |
| `0f81f453f9be7979` | `age` | `nr.employed` | `numeric_vs_numeric` | yes | 41176 | 0.555 | `enumerated` |  |
| `14f93e7e9fd73c1b` | `emp.var.rate` | `euribor3m` | `numeric_vs_numeric` | yes | 41176 | 0.555 | `enumerated` |  |
| `23be291621ad228f` | `euribor3m` | `nr.employed` | `numeric_vs_numeric` | yes | 41176 | 0.555 | `enumerated` |  |
| `26310703c78d0319` | `campaign` | `cons.price.idx` | `numeric_vs_numeric` | yes | 41176 | 0.555 | `enumerated` |  |
| `2a940be9d00b3d10` | `campaign` | `euribor3m` | `numeric_vs_numeric` | yes | 41176 | 0.555 | `enumerated` |  |
| `3a64c0db38607ec2` | `duration` | `nr.employed` | `numeric_vs_numeric` | yes | 41176 | 0.555 | `enumerated` |  |
| `3aa64d1058f9f17d` | `cons.price.idx` | `nr.employed` | `numeric_vs_numeric` | yes | 41176 | 0.555 | `enumerated` |  |
| `3e80480d785b75e2` | `age` | `duration` | `numeric_vs_numeric` | yes | 41176 | 0.555 | `enumerated` |  |
| `43c944b0d8d72de3` | `age` | `cons.conf.idx` | `numeric_vs_numeric` | yes | 41176 | 0.555 | `enumerated` |  |
| `4aa12a921577265d` | `cons.conf.idx` | `poutcome` | `numeric_vs_categorical` | yes | 41176 | 0.555 | `enumerated` |  |
| `4b7ba9ae49f108a7` | `nr.employed` | `pdays` | `numeric_vs_numeric` | yes | 41176 | 0.555 | `enumerated` |  |
| `609efa2c17122ce6` | `cons.price.idx` | `poutcome` | `numeric_vs_categorical` | yes | 41176 | 0.555 | `enumerated` |  |
| `6532bdffe978ead0` | `pdays` | `poutcome` | `numeric_vs_categorical` | yes | 41176 | 0.555 | `enumerated` |  |
| `6828f8be154b37c7` | `cons.conf.idx` | `cons.price.idx` | `numeric_vs_numeric` | yes | 41176 | 0.555 | `enumerated` |  |
| `6e5b5f07213b1d6c` | `campaign` | `emp.var.rate` | `numeric_vs_numeric` | yes | 41176 | 0.555 | `enumerated` |  |
| `720e30cd035b92c0` | `cons.price.idx` | `euribor3m` | `numeric_vs_numeric` | yes | 41176 | 0.555 | `enumerated` |  |
| `7f3346de20de7b37` | `age` | `emp.var.rate` | `numeric_vs_numeric` | yes | 41176 | 0.555 | `enumerated` |  |
| `88cd03ef597a6fce` | `campaign` | `nr.employed` | `numeric_vs_numeric` | yes | 41176 | 0.555 | `enumerated` |  |
| `8978404729c3cbba` | `duration` | `euribor3m` | `numeric_vs_numeric` | yes | 41176 | 0.555 | `enumerated` |  |
| `8a32717db7a03a8b` | `cons.price.idx` | `pdays` | `numeric_vs_numeric` | yes | 41176 | 0.555 | `enumerated` |  |
| `8c2ff454e97180fc` | `cons.conf.idx` | `nr.employed` | `numeric_vs_numeric` | yes | 41176 | 0.555 | `enumerated` |  |
| `8ca5eb6c1c1c0a53` | `age` | `campaign` | `numeric_vs_numeric` | yes | 41176 | 0.555 | `enumerated` |  |
| `8e5a9055241eba6c` | `campaign` | `cons.conf.idx` | `numeric_vs_numeric` | yes | 41176 | 0.555 | `enumerated` |  |
| `92400293d19c0ea4` | `euribor3m` | `poutcome` | `numeric_vs_categorical` | yes | 41176 | 0.555 | `enumerated` |  |
| `9af8369e7583bc62` | `age` | `euribor3m` | `numeric_vs_numeric` | yes | 41176 | 0.555 | `enumerated` |  |
| `9b03b08ea1e08f98` | `age` | `poutcome` | `numeric_vs_categorical` | yes | 41176 | 0.555 | `enumerated` |  |
| `9ed080c23bcbf639` | `campaign` | `poutcome` | `numeric_vs_categorical` | yes | 41176 | 0.555 | `enumerated` |  |
| `aa0df79478b18ab4` | `age` | `cons.price.idx` | `numeric_vs_numeric` | yes | 41176 | 0.555 | `enumerated` |  |
| `ab4d386785e603a9` | `campaign` | `duration` | `numeric_vs_numeric` | yes | 41176 | 0.555 | `enumerated` |  |
| `adf89904750fad46` | `duration` | `emp.var.rate` | `numeric_vs_numeric` | yes | 41176 | 0.555 | `enumerated` |  |
| `b25c6e2f769ee88c` | `emp.var.rate` | `nr.employed` | `numeric_vs_numeric` | yes | 41176 | 0.555 | `enumerated` |  |
| `b2b778ad0f708e6c` | `duration` | `poutcome` | `numeric_vs_categorical` | yes | 41176 | 0.555 | `enumerated` |  |
| `c115fcde900e28a6` | `cons.price.idx` | `duration` | `numeric_vs_numeric` | yes | 41176 | 0.555 | `enumerated` |  |
| `cea0db59fe4e87f5` | `age` | `pdays` | `numeric_vs_numeric` | yes | 41176 | 0.555 | `enumerated` |  |
| `d74c8aa9f5053c9c` | `cons.conf.idx` | `duration` | `numeric_vs_numeric` | yes | 41176 | 0.555 | `enumerated` |  |
| `d8f7e0cd40ee1686` | `cons.conf.idx` | `emp.var.rate` | `numeric_vs_numeric` | yes | 41176 | 0.555 | `enumerated` |  |
| `e6af230108830142` | `nr.employed` | `poutcome` | `numeric_vs_categorical` | yes | 41176 | 0.555 | `enumerated` |  |
| `e71d1ac36b93e62c` | `campaign` | `pdays` | `numeric_vs_numeric` | yes | 41176 | 0.555 | `enumerated` |  |
| `00c21f38eec4a475` | `emp.var.rate` | `marital` | `numeric_vs_categorical` | yes | 41096 | 0.555 | `enumerated` |  |
| `137d740d7de20885` | `euribor3m` | `marital` | `numeric_vs_categorical` | yes | 41096 | 0.555 | `enumerated` |  |
| `13d3d4d73cf9e918` | `duration` | `marital` | `numeric_vs_categorical` | yes | 41096 | 0.555 | `enumerated` |  |
| `31a85b65406b8c1c` | `age` | `marital` | `numeric_vs_categorical` | yes | 41096 | 0.555 | `enumerated` |  |
| `71c08797beac3d74` | `cons.conf.idx` | `marital` | `numeric_vs_categorical` | yes | 41096 | 0.555 | `enumerated` |  |
| `86aa6cf898d0289e` | `pdays` | `marital` | `numeric_vs_categorical` | yes | 41096 | 0.555 | `enumerated` |  |
| `dff2c120e459b972` | `campaign` | `marital` | `numeric_vs_categorical` | yes | 41096 | 0.555 | `enumerated` |  |
| `ead48c293f719454` | `cons.price.idx` | `marital` | `numeric_vs_categorical` | yes | 41096 | 0.555 | `enumerated` |  |
| `f1d6defb42cf91a5` | `nr.employed` | `marital` | `numeric_vs_categorical` | yes | 41096 | 0.555 | `enumerated` |  |
| `965b662ca7dfa48e` | `contact` | `poutcome` | `categorical_vs_categorical` | yes | 41176 | 0.550 | `enumerated` |  |
| `c563a0a91129f80c` | `contact` | `marital` | `categorical_vs_categorical` | yes | 41096 | 0.550 | `enumerated` |  |
| `e8b6c62a9891a465` | `marital` | `poutcome` | `categorical_vs_categorical` | yes | 41096 | 0.550 | `enumerated` |  |
| `e552a7da344bb940` | `housing` | `poutcome` | `categorical_vs_categorical` | yes | 40186 | 0.549 | `enumerated` |  |
| `ebed9ead0662c118` | `loan` | `poutcome` | `categorical_vs_categorical` | yes | 40186 | 0.549 | `enumerated` |  |
| `353b2e9f287dd721` | `loan` | `marital` | `categorical_vs_categorical` | yes | 40107 | 0.549 | `enumerated` |  |
| `c88d61a2c5955d33` | `housing` | `marital` | `categorical_vs_categorical` | yes | 40107 | 0.549 | `enumerated` |  |
| `409ab7817b0c6db7` | `pdays` | `day_of_week` | `numeric_vs_categorical` | yes | 41176 | 0.547 | `enumerated` |  |
| `6a630598b761c10d` | `cons.price.idx` | `day_of_week` | `numeric_vs_categorical` | yes | 41176 | 0.547 | `enumerated` |  |
| `71bc8df28b32d363` | `nr.employed` | `day_of_week` | `numeric_vs_categorical` | yes | 41176 | 0.547 | `enumerated` |  |
| `77e70944095a008d` | `cons.conf.idx` | `day_of_week` | `numeric_vs_categorical` | yes | 41176 | 0.547 | `enumerated` |  |
| `a2383303729b7a7f` | `age` | `day_of_week` | `numeric_vs_categorical` | yes | 41176 | 0.547 | `enumerated` |  |
| `afb86d677358a4ef` | `duration` | `day_of_week` | `numeric_vs_categorical` | yes | 41176 | 0.547 | `enumerated` |  |
| `db3c1739b91f2f60` | `emp.var.rate` | `day_of_week` | `numeric_vs_categorical` | yes | 41176 | 0.547 | `enumerated` |  |
| `dc551b906691ac34` | `euribor3m` | `day_of_week` | `numeric_vs_categorical` | yes | 41176 | 0.547 | `enumerated` |  |
| `e52ed4d971a2ea76` | `campaign` | `day_of_week` | `numeric_vs_categorical` | yes | 41176 | 0.547 | `enumerated` |  |
| `3bfbd260d6928f38` | `day_of_week` | `poutcome` | `categorical_vs_categorical` | yes | 41176 | 0.544 | `enumerated` |  |
| `fa8c825993965e2d` | `contact` | `day_of_week` | `categorical_vs_categorical` | yes | 41176 | 0.544 | `enumerated` |  |
| `cada0c33c85b8b61` | `day_of_week` | `marital` | `categorical_vs_categorical` | yes | 41096 | 0.544 | `enumerated` |  |
| `bf1b71d43718c9d0` | `day_of_week` | `loan` | `categorical_vs_categorical` | yes | 40186 | 0.543 | `enumerated` |  |
| `cbb117308c57252d` | `day_of_week` | `housing` | `categorical_vs_categorical` | yes | 40186 | 0.543 | `enumerated` |  |
| `0a615c2640c1e2fc` | `nr.employed` | `education` | `numeric_vs_categorical` | yes | 39446 | 0.537 | `enumerated` |  |
| `189afbb338590588` | `campaign` | `education` | `numeric_vs_categorical` | yes | 39446 | 0.537 | `enumerated` |  |
| `1ba9a402ba9097b7` | `euribor3m` | `education` | `numeric_vs_categorical` | yes | 39446 | 0.537 | `enumerated` |  |
| `294cac73c9c97551` | `cons.conf.idx` | `education` | `numeric_vs_categorical` | yes | 39446 | 0.537 | `enumerated` |  |
| `2f0aa9cc55af2a9e` | `duration` | `education` | `numeric_vs_categorical` | yes | 39446 | 0.537 | `enumerated` |  |
| `5bac40d23ac5fc7b` | `age` | `education` | `numeric_vs_categorical` | yes | 39446 | 0.537 | `enumerated` |  |
| `63de87c2cd24fe30` | `cons.price.idx` | `education` | `numeric_vs_categorical` | yes | 39446 | 0.537 | `enumerated` |  |
| `a5a4c902ecf77fe2` | `emp.var.rate` | `education` | `numeric_vs_categorical` | yes | 39446 | 0.537 | `enumerated` |  |
| `bf279cb99c8731d4` | `pdays` | `education` | `numeric_vs_categorical` | yes | 39446 | 0.537 | `enumerated` |  |
| `0e92528e1a3209c3` | `education` | `poutcome` | `categorical_vs_categorical` | yes | 39446 | 0.536 | `enumerated` |  |
| `1259d1da05c23c7b` | `contact` | `education` | `categorical_vs_categorical` | yes | 39446 | 0.536 | `enumerated` |  |
| `7de697da4483343d` | `day_of_week` | `education` | `categorical_vs_categorical` | yes | 39446 | 0.536 | `enumerated` |  |
| `10e27787a85cd137` | `education` | `marital` | `categorical_vs_categorical` | yes | 39375 | 0.536 | `enumerated` |  |
| `03799c0b8e3ef37a` | `campaign` | `previous` | `numeric_vs_categorical` | yes | 41170 | 0.535 | `enumerated` |  |
| `1d9436fb083e6790` | `age` | `previous` | `numeric_vs_categorical` | yes | 41170 | 0.535 | `enumerated` |  |
| `2d19099fbd35c1d4` | `cons.conf.idx` | `previous` | `numeric_vs_categorical` | yes | 41170 | 0.535 | `enumerated` |  |
| `49fce66427cef291` | `pdays` | `previous` | `numeric_vs_categorical` | yes | 41170 | 0.535 | `enumerated` |  |
| `679054c38376538c` | `nr.employed` | `previous` | `numeric_vs_categorical` | yes | 41170 | 0.535 | `enumerated` |  |
| `7813af83a054ef99` | `emp.var.rate` | `previous` | `numeric_vs_categorical` | yes | 41170 | 0.535 | `enumerated` |  |
| `79548be60b7c0bde` | `contact` | `previous` | `categorical_vs_categorical` | yes | 41170 | 0.535 | `enumerated` |  |
| `936c006d67ab5994` | `poutcome` | `previous` | `categorical_vs_categorical` | yes | 41170 | 0.535 | `enumerated` |  |
| `a4b8a78870076bb3` | `cons.price.idx` | `previous` | `numeric_vs_categorical` | yes | 41170 | 0.535 | `enumerated` |  |
| `bd46177f054c3856` | `day_of_week` | `previous` | `categorical_vs_categorical` | yes | 41170 | 0.535 | `enumerated` |  |
| `e016447999c2afe2` | `euribor3m` | `previous` | `numeric_vs_categorical` | yes | 41170 | 0.535 | `enumerated` |  |
| `eb8bf73c00aac1d1` | `duration` | `previous` | `numeric_vs_categorical` | yes | 41170 | 0.535 | `enumerated` |  |
| `3730b358d15471d2` | `marital` | `previous` | `categorical_vs_categorical` | yes | 41090 | 0.535 | `enumerated` |  |
| `86ea8c922d3e46ef` | `education` | `loan` | `categorical_vs_categorical` | yes | 38496 | 0.535 | `enumerated` |  |
| `ffe560021bec8ec5` | `education` | `housing` | `categorical_vs_categorical` | yes | 38496 | 0.535 | `enumerated` |  |
| `70cfcb6c3fdb5058` | `housing` | `previous` | `categorical_vs_categorical` | yes | 40180 | 0.534 | `enumerated` |  |
| `fd771ec7628c035e` | `loan` | `previous` | `categorical_vs_categorical` | yes | 40180 | 0.534 | `enumerated` |  |
| `36a7191f419e541f` | `education` | `previous` | `categorical_vs_categorical` | yes | 39441 | 0.533 | `enumerated` |  |
| `1f38c26082bda1b8` | `contact` | `month` | `categorical_vs_categorical` | yes | 41176 | 0.529 | `enumerated` |  |
| `67fa464bc2ddd155` | `month` | `poutcome` | `categorical_vs_categorical` | yes | 41176 | 0.529 | `enumerated` |  |
| `6aadae54566d6447` | `day_of_week` | `month` | `categorical_vs_categorical` | yes | 41176 | 0.529 | `enumerated` |  |
| `8aaa50fd39099b32` | `month` | `previous` | `categorical_vs_categorical` | yes | 41170 | 0.529 | `enumerated` |  |
| `2b89316f6d400d0a` | `marital` | `month` | `categorical_vs_categorical` | yes | 41096 | 0.529 | `enumerated` |  |
| `20868ea7f8494135` | `loan` | `month` | `categorical_vs_categorical` | yes | 40186 | 0.528 | `enumerated` |  |
| `526b6ea3dd2e6dd7` | `housing` | `month` | `categorical_vs_categorical` | yes | 40186 | 0.528 | `enumerated` |  |
| `083625b2e93cd578` | `cons.price.idx` | `month` | `numeric_vs_categorical` | yes | 41176 | 0.527 | `enumerated` |  |
| `25149c67820a0cf1` | `cons.conf.idx` | `month` | `numeric_vs_categorical` | yes | 41176 | 0.527 | `enumerated` |  |
| `32b9754570bfa655` | `pdays` | `month` | `numeric_vs_categorical` | yes | 41176 | 0.527 | `enumerated` |  |
| `386e1ab9e5f789fa` | `nr.employed` | `month` | `numeric_vs_categorical` | yes | 41176 | 0.527 | `enumerated` |  |
| `3d0a3958008d94bc` | `duration` | `month` | `numeric_vs_categorical` | yes | 41176 | 0.527 | `enumerated` |  |
| `3d75d94aae15416d` | `euribor3m` | `month` | `numeric_vs_categorical` | yes | 41176 | 0.527 | `enumerated` |  |
| `450bef51e8fd0e15` | `emp.var.rate` | `month` | `numeric_vs_categorical` | yes | 41176 | 0.527 | `enumerated` |  |
| `46923f2bbb97f069` | `age` | `month` | `numeric_vs_categorical` | yes | 41176 | 0.527 | `enumerated` |  |
| `c300a260bb7cbb8e` | `campaign` | `month` | `numeric_vs_categorical` | yes | 41176 | 0.527 | `enumerated` |  |
| `80a00baa5ae05ea5` | `education` | `month` | `categorical_vs_categorical` | yes | 39446 | 0.527 | `enumerated` |  |
| `265a013e12e302bc` | `day_of_week` | `job` | `categorical_vs_categorical` | yes | 40846 | 0.526 | `enumerated` |  |
| `afb084da75a53dfd` | `contact` | `job` | `categorical_vs_categorical` | yes | 40846 | 0.526 | `enumerated` |  |
| `b63f0668d21bbddd` | `job` | `poutcome` | `categorical_vs_categorical` | yes | 40846 | 0.526 | `enumerated` |  |
| `b7909149343315d1` | `job` | `previous` | `categorical_vs_categorical` | yes | 40840 | 0.526 | `enumerated` |  |
| `ecfc5ba2c8cdfa30` | `job` | `month` | `categorical_vs_categorical` | yes | 40846 | 0.526 | `enumerated` |  |
| `7bcd5e9120668796` | `job` | `marital` | `categorical_vs_categorical` | yes | 40775 | 0.525 | `enumerated` |  |
| `68030ffaf67a8690` | `housing` | `job` | `categorical_vs_categorical` | yes | 39861 | 0.524 | `enumerated` |  |
| `cc26040ef6788afb` | `job` | `loan` | `categorical_vs_categorical` | yes | 39861 | 0.524 | `enumerated` |  |
| `2706a4c4eca05d39` | `education` | `job` | `categorical_vs_categorical` | yes | 39247 | 0.523 | `enumerated` |  |
| `2ce57d825ba948fb` | `nr.employed` | `job` | `numeric_vs_categorical` | yes | 40846 | 0.523 | `enumerated` |  |
| `345e2cda7ce30fe8` | `age` | `job` | `numeric_vs_categorical` | yes | 40846 | 0.523 | `enumerated` |  |
| `35a00753f1ad04b2` | `pdays` | `job` | `numeric_vs_categorical` | yes | 40846 | 0.523 | `enumerated` |  |
| `3ee0668d2a45e99d` | `emp.var.rate` | `job` | `numeric_vs_categorical` | yes | 40846 | 0.523 | `enumerated` |  |
| `609ac5084c3c5476` | `cons.conf.idx` | `job` | `numeric_vs_categorical` | yes | 40846 | 0.523 | `enumerated` |  |
| `7b00cb4016584fcf` | `campaign` | `job` | `numeric_vs_categorical` | yes | 40846 | 0.523 | `enumerated` |  |
| `c2f7ecbd8caa3e78` | `euribor3m` | `job` | `numeric_vs_categorical` | yes | 40846 | 0.523 | `enumerated` |  |
| `eee76f7cc13a265e` | `duration` | `job` | `numeric_vs_categorical` | yes | 40846 | 0.523 | `enumerated` |  |
| `efeaa3698c4a834b` | `cons.price.idx` | `job` | `numeric_vs_categorical` | yes | 40846 | 0.523 | `enumerated` |  |
| `0a8fe408e9b57751` | `campaign` | `default` | `numeric_vs_binary` | no | 32580 | 0.315 | `enumerated` | group 'yes' has n=3 < min_group_n (8) |
| `1d407919c0fb4765` | `cons.price.idx` | `default` | `numeric_vs_binary` | no | 32580 | 0.315 | `enumerated` | group 'yes' has n=3 < min_group_n (8) |
| `435b42745e2f24e9` | `contact` | `default` | `categorical_vs_categorical` | no | 32577 | 0.315 | `enumerated` | dropped_levels (< min_group_n=8): default:yes; degenerate: contingency table has < 2 rows or < 2 columns after filter |
| `5e148875e9f4ad41` | `emp.var.rate` | `default` | `numeric_vs_binary` | no | 32580 | 0.315 | `enumerated` | group 'yes' has n=3 < min_group_n (8) |
| `77e7e7206e5cac02` | `cons.conf.idx` | `default` | `numeric_vs_binary` | no | 32580 | 0.315 | `enumerated` | group 'yes' has n=3 < min_group_n (8) |
| `8149a28d23c35224` | `nr.employed` | `default` | `numeric_vs_binary` | no | 32580 | 0.315 | `enumerated` | group 'yes' has n=3 < min_group_n (8) |
| `b3e6681ba88bcd3e` | `euribor3m` | `default` | `numeric_vs_binary` | no | 32580 | 0.315 | `enumerated` | group 'yes' has n=3 < min_group_n (8) |
| `c8268ab78edfcd40` | `duration` | `default` | `numeric_vs_binary` | no | 32580 | 0.315 | `enumerated` | group 'yes' has n=3 < min_group_n (8) |
| `e0f0e54eac9cd6ef` | `pdays` | `default` | `numeric_vs_binary` | no | 32580 | 0.315 | `enumerated` | group 'yes' has n=3 < min_group_n (8) |
| `eb1c9e23e604bfe8` | `age` | `default` | `numeric_vs_binary` | no | 32580 | 0.315 | `enumerated` | group 'yes' has n=3 < min_group_n (8) |
| `9a4622a1fa495678` | `default` | `loan` | `categorical_vs_categorical` | no | 31814 | 0.313 | `enumerated` | dropped_levels (< min_group_n=8): default:yes; degenerate: contingency table has < 2 rows or < 2 columns after filter |
| `adceae9002a7af64` | `default` | `housing` | `categorical_vs_categorical` | no | 31814 | 0.313 | `enumerated` | dropped_levels (< min_group_n=8): default:yes; degenerate: contingency table has < 2 rows or < 2 columns after filter |
| `787a7b799de8f837` | `default` | `poutcome` | `categorical_vs_categorical` | no | 32577 | 0.290 | `enumerated` | dropped_levels (< min_group_n=8): default:yes; degenerate: contingency table has < 2 rows or < 2 columns after filter |
| `6d92e194498a7e2e` | `default` | `marital` | `categorical_vs_categorical` | no | 32508 | 0.289 | `enumerated` | dropped_levels (< min_group_n=8): default:yes; degenerate: contingency table has < 2 rows or < 2 columns after filter |
| `5d7fcacea1b08a40` | `day_of_week` | `default` | `categorical_vs_categorical` | no | 32577 | 0.284 | `enumerated` | dropped_levels (< min_group_n=8): default:yes; degenerate: contingency table has < 2 rows or < 2 columns after filter |
| `719dedb942904b08` | `default` | `education` | `categorical_vs_categorical` | no | 31395 | 0.275 | `enumerated` | dropped_levels (< min_group_n=8): default:yes; degenerate: contingency table has < 2 rows or < 2 columns after filter |
| `47249ebba807a569` | `default` | `previous` | `categorical_vs_categorical` | no | 32571 | 0.275 | `enumerated` | dropped_levels (< min_group_n=8): default:yes, previous:6, previous:7; degenerate: contingency table has < 2 rows or < 2 columns after filter |
| `092d29082d9684f8` | `default` | `month` | `categorical_vs_categorical` | no | 32577 | 0.269 | `enumerated` | dropped_levels (< min_group_n=8): default:yes; degenerate: contingency table has < 2 rows or < 2 columns after filter |
| `9565928d2d082a9a` | `default` | `job` | `categorical_vs_categorical` | no | 32399 | 0.265 | `enumerated` | dropped_levels (< min_group_n=8): default:yes; degenerate: contingency table has < 2 rows or < 2 columns after filter |
