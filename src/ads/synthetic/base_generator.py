"""Clean synthetic base dataset generator with planted relationships (Section 12.1)."""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

_REGIONS = ["North Area", "South Bay", "East Coast", "West Valley", "Central Hub"]
_REGION_PROBS = [0.32, 0.25, 0.20, 0.15, 0.08]

_NOTE_TEMPLATES = [
    "Customer contacted support desk regarding billing cycle adjustment and plan upgrade options",
    "Account reviewed during annual loyalty checkup with positive feedback on dashboard speed",
    "Requested invoice copy for corporate tax filing and updated primary payment method on file",
    "Inquired about multi-user discount tier and seasonal promotional bundle eligibility",
    "Reported temporary login delay on mobile application which was resolved after cache reset",
    "Long-term subscriber interested in early renewal discount and dedicated account manager",
]


def make_clean_base(n_rows: int = 2000, seed: int = 42) -> pd.DataFrame:
    """Build a clean, realistic base dataset with known structure (Section 12.1).

    Planted relationships:
      1. income <-> monthly_spend (strong positive linear correlation)
      2. income <-> membership (Basic / Silver / Gold tiers)
      3. tenure_months & satisfaction <-> churned (lower tenure & lower satisfaction -> higher churn)
    """
    rng = np.random.default_rng(seed)

    # 1. customer_id (unique string IDs)
    customer_id = [f"C{i:06d}" for i in range(1, n_rows + 1)]

    # 2. age (int, 18-80, roughly normal around 42)
    age_raw = rng.normal(loc=42.0, scale=14.0, size=n_rows)
    age = np.clip(np.round(age_raw), 18, 80).astype(int)

    # 3. gender (Male/Female, ~50/50)
    gender = rng.choice(["Male", "Female"], size=n_rows, p=[0.50, 0.50]).tolist()

    # 4. income (right-skewed lognormal, positive)
    income_raw = rng.lognormal(mean=10.85, sigma=0.55, size=n_rows)
    income = np.round(np.clip(income_raw, 15000.0, 500000.0), 2)

    # 5. region (5 levels, unequal frequencies)
    region = rng.choice(_REGIONS, size=n_rows, p=_REGION_PROBS).tolist()

    # 6. membership (Basic/Silver/Gold, related to income)
    membership: list[str] = []
    for inc in income:
        r = rng.random()
        if inc > 90000:
            tier = "Gold" if r < 0.65 else ("Silver" if r < 0.92 else "Basic")
        elif inc > 50000:
            tier = "Silver" if r < 0.55 else ("Basic" if r < 0.85 else "Gold")
        else:
            tier = "Basic" if r < 0.75 else ("Silver" if r < 0.95 else "Gold")
        membership.append(tier)

    # 7. tenure_months (int, 0-120)
    tenure_months = rng.integers(low=0, high=121, size=n_rows).astype(int)

    # 8. monthly_spend (float, correlated with income)
    spend_noise = rng.normal(loc=0.0, scale=25.0, size=n_rows)
    monthly_spend = np.round(np.clip(20.0 + 0.0022 * income + spend_noise, 5.0, 2500.0), 2)

    # 9. signup_date (dates over 5 years: 2020-01-01 to 2024-12-31)
    start_date = date(2020, 1, 1)
    day_offsets = rng.integers(low=0, high=365 * 5, size=n_rows)
    signup_date = [(start_date + timedelta(days=int(d))).isoformat() for d in day_offsets]

    # 10. satisfaction (ordinal 1-5 ints)
    satisfaction = rng.choice([1, 2, 3, 4, 5], size=n_rows, p=[0.10, 0.18, 0.32, 0.25, 0.15]).astype(int)

    # 11. churned (Yes/No, ~20%, related to tenure_months and satisfaction)
    # Logistic model calibrated so overall churn rate is ~20%
    logit = 0.65 - 0.022 * tenure_months - 0.55 * (satisfaction - 3)
    probs = 1.0 / (1.0 + np.exp(-logit))
    churn_draw = rng.random(size=n_rows) < probs
    churned = ["Yes" if flag else "No" for flag in churn_draw]

    # 12. notes (short random free text for ~30% rows, else empty)
    notes: list[str] = []
    for i in range(n_rows):
        if rng.random() < 0.30:
            tpl = _NOTE_TEMPLATES[int(rng.integers(0, len(_NOTE_TEMPLATES)))]
            notes.append(f"{tpl} (ref #{1000 + i})")
        else:
            notes.append("")

    # 13. constant_flag (constant "A" column)
    constant_flag = ["A"] * n_rows

    return pd.DataFrame(
        {
            "customer_id": customer_id,
            "age": age,
            "gender": gender,
            "income": income,
            "region": region,
            "membership": membership,
            "tenure_months": tenure_months,
            "monthly_spend": monthly_spend,
            "signup_date": signup_date,
            "satisfaction": satisfaction,
            "churned": churned,
            "notes": notes,
            "constant_flag": constant_flag,
        }
    )


def generate_base_truth_metadata(df_clean: pd.DataFrame, seed: int = 42) -> dict[str, Any]:
    """Compute descriptive statistics of planted relationships for data/synthetic/base_truth.json."""
    corr_income_spend = float(df_clean["income"].corr(df_clean["monthly_spend"]))
    churn_bin = (df_clean["churned"] == "Yes").astype(float)
    corr_tenure_churn = float(df_clean["tenure_months"].corr(churn_bin))
    corr_sat_churn = float(df_clean["satisfaction"].corr(churn_bin))

    return {
        "seed": seed,
        "n_rows": int(len(df_clean)),
        "n_cols": int(len(df_clean.columns)),
        "planted_relationships": [
            {
                "pair": ["income", "monthly_spend"],
                "type": "numeric_numeric_positive",
                "pearson_r": round(corr_income_spend, 4),
                "description": "monthly_spend is linearly generated from income plus Gaussian noise.",
            },
            {
                "pair": ["tenure_months", "churned"],
                "type": "numeric_binary_negative",
                "point_biserial_r": round(corr_tenure_churn, 4),
                "description": "Shorter tenure increases probability of churn.",
            },
            {
                "pair": ["satisfaction", "churned"],
                "type": "ordinal_binary_negative",
                "point_biserial_r": round(corr_sat_churn, 4),
                "description": "Lower satisfaction score increases probability of churn.",
            },
            {
                "pair": ["income", "membership"],
                "type": "numeric_categorical",
                "description": "Higher income brackets have higher probability of Silver and Gold membership.",
            },
        ],
    }


def save_base_truth_json(df_clean: pd.DataFrame, path: Path | str, seed: int = 42) -> Path:
    """Write base_truth.json to disk."""
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    meta = generate_base_truth_metadata(df_clean, seed=seed)
    out_path.write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out_path

