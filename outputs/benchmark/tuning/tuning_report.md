# Effect-floor tuning — `core60` / `dev`

Objective: highest mean recall with mean FDP ≤ 5.0%. Grid: every floor × 0.5, 0.75, 1.0, 1.25, 1.5.

| Multiplier | Mean FDP (FDR) | Recall | FWER on zero-effect datasets | Precision |
| ---: | ---: | ---: | ---: | ---: |
| 0.5 | 7.3% | 71.2% | 16.7% | 90.4% |
| 0.75 | 6.6% | 70.7% | 16.7% | 91.4% |
| 1.0 | 4.7% | 66.6% | 8.3% | 93.6% |
| 1.25 | 4.6% | 65.8% | 8.3% | 93.7% |
| 1.5 | 4.5% | 64.3% | 8.3% | 93.9% |

**Decision:** multiplier **1.0** — best feasible multiplier 1.0 is within one grid step of the conventions -> keep conventional values.

Resulting floors:

- `cohens_d` = 0.2
- `correlation` = 0.1
- `cramers_v_df1` = 0.1
- `epsilon_squared` = 0.01
- `eta_squared` = 0.01
- `rank_biserial` = 0.1
