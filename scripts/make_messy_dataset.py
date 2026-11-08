"""Script to generate the messy synthetic dataset and ground-truth manifests (Section 12)."""

from __future__ import annotations

import argparse
from pathlib import Path

from ads.synthetic.messy_injector import DEFAULT_INJECTION_RATES, generate_and_save_messy_dataset


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate messy synthetic datasets.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
    parser.add_argument("--rows", type=int, default=2000, help="Number of clean base rows")
    parser.add_argument(
        "--out-dir", type=str, default="data/synthetic", help="Output directory"
    )
    parser.add_argument(
        "--variants",
        action="store_true",
        help="Also generate messy_light and messy_heavy difficulty variants",
    )
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    primary = generate_and_save_messy_dataset(
        out_dir=out_dir, n_rows=args.rows, seed=args.seed, prefix="messy"
    )
    print(f"Generated primary messy dataset: {primary['messy_csv']}")

    if args.variants:
        light_rates = {
            k: (v * 0.5 if isinstance(v, float) else max(2, int(v // 2)))
            for k, v in DEFAULT_INJECTION_RATES.items()
        }
        heavy_rates = {
            k: (min(0.25, v * 2.0) if isinstance(v, float) else int(v * 2))
            for k, v in DEFAULT_INJECTION_RATES.items()
        }
        generate_and_save_messy_dataset(
            out_dir=out_dir,
            n_rows=args.rows,
            seed=args.seed + 1,
            rates=light_rates,
            prefix="messy_light",
        )
        generate_and_save_messy_dataset(
            out_dir=out_dir,
            n_rows=args.rows,
            seed=args.seed + 2,
            rates=heavy_rates,
            prefix="messy_heavy",
        )
        print("Generated messy_light and messy_heavy variants.")


if __name__ == "__main__":
    main()

