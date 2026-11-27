"""Tests for Phase 8 VeriData variant adapters (S2, S3, A1-A6, N0)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from veridata.evaluation.systems.veridata_variants import (
    DEFAULT_PHASE8_VARIANT_IDS,
    run_phase8_variants_on_df,
)


def test_phase8_variants_share_stage_a_and_handle_gates() -> None:
    rng = np.random.default_rng(11)
    n = 150
    x = rng.normal(size=n)
    df = pd.DataFrame(
        {
            "x": x,
            "y_real": 0.8 * x + rng.normal(scale=0.5, size=n),
            "y_dup": x,  # trivial / derived relationship (|r| = 1.0)
            "z_noise": rng.normal(size=n),
        }
    )
    outs = run_phase8_variants_on_df(df, "toy_var")
    assert set(outs.keys()) == set(DEFAULT_PHASE8_VARIANT_IDS)

    full_pairs = {(f.col_a, f.col_b) for f in outs["S3_veridata_full"].findings}
    no_gates_pairs = {(f.col_a, f.col_b) for f in outs["A6_full_minus_gates"].findings}
    # y_dup should be rejected by trivial gate in S3, but allowed in A6_full_minus_gates
    assert ("x", "y_dup") not in full_pairs and ("y_dup", "x") not in full_pairs
    assert ("x", "y_dup") in no_gates_pairs or ("y_dup", "x") in no_gates_pairs
    assert ("x", "y_real") in full_pairs or ("y_real", "x") in full_pairs
