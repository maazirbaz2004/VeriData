"""Generate a pure noise dataset (200 rows x 25 random columns of mixed types).

In this dataset, by construction, there are zero true associations (all columns are generated
independently). Naive uncorrected testing at alpha=0.05 will report ~15 false discoveries out of ~300 tests.
VeriData's validation layer with Benjamini-Hochberg FDR control will validate 0 findings.
"""

from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd


def generate_noise_dataset(n_rows: int = 200, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    data: dict[str, Any] = {}

    # 15 Continuous Gaussian / Exponential / Uniform columns
    for i in range(1, 6):
        data[f"num_norm_{i:02d}"] = rng.normal(loc=50.0, scale=10.0, size=n_rows).round(2)
    for i in range(1, 6):
        data[f"num_unif_{i:02d}"] = rng.uniform(low=0.0, high=100.0, size=n_rows).round(2)
    for i in range(1, 6):
        data[f"num_skew_{i:02d}"] = rng.exponential(scale=15.0, size=n_rows).round(2)

    # 5 Binary columns
    for i in range(1, 6):
        data[f"bin_{i:02d}"] = rng.choice(["A", "B"], size=n_rows, p=[0.5, 0.5])

    # 5 Multi-category columns
    cats = ["low", "medium", "high", "critical"]
    for i in range(1, 6):
        data[f"cat_{i:02d}"] = rng.choice(cats, size=n_rows)

    return pd.DataFrame(data)


def main():
    out_dir = Path("data/demo")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "pure_noise.csv"

    df = generate_noise_dataset(n_rows=200, seed=42)
    df.to_csv(out_path, index=False)
    print(f"Generated pure noise dataset: {out_path} ({df.shape[0]} rows x {df.shape[1]} cols)")


if __name__ == "__main__":
    main()
