"""Tests for the EDA module (Section 10): descriptive statistics, figures, determinism, wording."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ads.eda.core import classify_columns, run_eda_core
from ads.eda.plots import EDASettings, df_to_markdown, fmt_pct, slugify
from ads.eda.stats import (
    as_float,
    as_labels,
    count_histogram_peaks,
    cramers_v,
    eta_squared,
    imbalance_label,
    iqr_outlier_mask,
    normalized_entropy,
)

FORBIDDEN = ("p-value", "p value", "p =", "p<", "p <", "significant")


# ---------------------------------------------------------------------------------------
# statistics, checked against hand-computed values
# ---------------------------------------------------------------------------------------


def test_cramers_v_matches_hand_computed_value() -> None:
    # 2x2 table [[30, 10], [10, 30]], n = 80 -> chi2 = 20, phi2 = 0.25, bias-corrected V = 0.49029
    x = pd.Series(["a"] * 40 + ["b"] * 40)
    y = pd.Series(["u"] * 30 + ["v"] * 10 + ["u"] * 10 + ["v"] * 30)
    assert cramers_v(x, y) == pytest.approx(0.4902903378, abs=1e-9)


def test_cramers_v_edge_cases() -> None:
    assert cramers_v(pd.Series(["a"] * 10), pd.Series(["u", "v"] * 5)) is None  # one level only
    same = pd.Series(["a", "b", "c"] * 30)
    assert cramers_v(same, same) == pytest.approx(1.0, abs=1e-9)
    # missing values are ignored, not counted as a level
    x = pd.Series(["a", "b", None, "a", "b", np.nan] * 20)
    y = pd.Series(["u", "v", "u", "u", "v", "v"] * 20)
    assert cramers_v(x, y) is not None


def test_eta_squared_matches_hand_computed_value() -> None:
    # groups a = [1, 2, 3], b = [7, 8, 9]: SS_between = 54, SS_total = 58
    vals = pd.Series([1, 2, 3, 7, 8, 9], dtype="float64")
    grp = pd.Series(["a", "a", "a", "b", "b", "b"])
    assert eta_squared(vals, grp) == pytest.approx(54 / 58, abs=1e-12)


def test_eta_squared_edge_cases() -> None:
    assert eta_squared(pd.Series([1.0, 1.0, 1.0, 1.0]), pd.Series(["a", "a", "b", "b"])) is None  # no spread
    assert eta_squared(pd.Series([1.0, 2.0, 3.0]), pd.Series(["a", "a", "a"])) is None  # one group
    nullable = pd.Series([1, 2, None, 7, 8, 9], dtype="Int64")
    assert eta_squared(nullable, pd.Series(list("aaabbb"))) is not None


def test_normalized_entropy_and_imbalance_labels() -> None:
    assert normalized_entropy([50, 50]) == pytest.approx(1.0)
    assert normalized_entropy([1, 1, 1, 1]) == pytest.approx(1.0)
    assert normalized_entropy([100, 0]) == 0.0
    assert 0 < normalized_entropy([90, 10]) < 1
    assert imbalance_label(0.05, 19.0) == "highly imbalanced"
    assert imbalance_label(0.40, 1.5) == "mildly imbalanced"
    assert imbalance_label(0.45, 1.22) == "balanced"


def test_histogram_peak_heuristic() -> None:
    rng = np.random.default_rng(0)
    bimodal = pd.Series(np.concatenate([rng.normal(0, 1, 1000), rng.normal(8, 1, 1000)]))
    unimodal = pd.Series(rng.normal(0, 1, 2000))
    assert count_histogram_peaks(bimodal) == 2
    assert count_histogram_peaks(unimodal) == 1
    assert count_histogram_peaks(pd.Series([1, 2, 3])) is None  # too few values


def test_type_helpers() -> None:
    s = as_float(pd.Series([1, None, 3], dtype="Int64"))
    assert s.dtype == "float64" and np.isnan(s.iloc[1]) and s.iloc[2] == 3.0
    labels = as_labels(pd.Series([1.0, 2.0, np.nan]))
    assert labels.tolist() == ["1", "2", None]
    mask = iqr_outlier_mask(pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 100], dtype="float64"))
    assert mask.tolist()[-1] is True and mask.sum() == 1


def test_formatting_helpers() -> None:
    assert slugify("Total Charges ($)") == "total_charges"
    assert fmt_pct(99.99, 100) == "99.99%"
    assert fmt_pct(1, 3) == "33.3%"
    md = df_to_markdown([{"a": 1234, "b": 0.5}], ["a", "b"], {"a", "b"})
    assert "1,234" in md and "0.5" in md


# ---------------------------------------------------------------------------------------
# end-to-end EDA on a small constructed frame
# ---------------------------------------------------------------------------------------


def make_frame(n: int = 300, seed: int = 0) -> tuple[pd.DataFrame, dict[str, str], dict[str, str]]:
    rng = np.random.default_rng(seed)
    income = np.exp(rng.normal(10, 0.8, n))
    income[:10] = np.nan
    df = pd.DataFrame(
        {
            "cust_id": [f"C{i:05d}" for i in range(n)],
            "age": rng.integers(18, 70, n).astype(float),
            "income": income,
            "spend": np.nan_to_num(income, nan=20000) * 0.1 + rng.normal(0, 500, n),
            "visits": pd.array(rng.integers(0, 4, n), dtype="Int64"),
            "segment": pd.Series(rng.choice(["a", "b", "c"], n)).astype("category"),
            "promo": rng.choice(["yes", "no"], n, p=[0.15, 0.85]),
            "signup": pd.date_range("2021-01-01", periods=n, freq="D"),
            "churn": np.where(rng.random(n) < 0.3, "churn", "stay"),
        }
    )
    df.loc[:4, "visits"] = pd.NA
    sem = {
        "cust_id": "id_like",
        "age": "numeric_continuous",
        "income": "numeric_continuous",
        "spend": "numeric_continuous",
        "visits": "numeric_discrete",
        "segment": "categorical_nominal",
        "promo": "binary",
        "signup": "datetime",
        "churn": "binary",
    }
    roles = {c: "feature" for c in df.columns}
    roles["cust_id"] = "id"
    roles["churn"] = "target_candidate"
    return df, sem, roles


def test_classify_columns_skips_ids_and_finds_target() -> None:
    df, sem, roles = make_frame()
    groups = classify_columns(df, sem, roles, "churn", EDASettings())
    assert "cust_id" in groups["skipped"]
    assert groups["numeric"] == ["age", "income", "spend", "visits"]
    assert "visits" in groups["discrete"]
    assert groups["categorical"] == ["segment", "promo", "churn"]
    assert groups["datetime"] == ["signup"]
    assert groups["target"] == "churn" and groups["target_kind"] == "categorical"


def test_run_eda_core_writes_expected_artifacts(tmp_path: Path) -> None:
    df, sem, roles = make_frame()
    res = run_eda_core(df, sem, roles, "churn", EDASettings(), tmp_path)
    hl = res["headline"]
    assert hl["eda_errors"] == []
    names = {r["filename"] for r in res["figures"]}
    for expected in [
        "dtype_breakdown.png",
        "missing_bar.png",
        "missing_heatmap.png",
        "missing_correlation.png",
        "numeric_distributions_1.png",
        "outlier_summary.png",
        "categorical_distributions_1.png",
        "cardinality_bar.png",
        "target_balance.png",
        "correlation_heatmap.png",
        "top_scatter_pairs.png",
        "numeric_by_category.png",
        "cramers_v_heatmap.png",
        "target_relationships.png",
        "datetime_signup.png",
    ]:
        assert expected in names, expected
    for r in res["figures"]:
        assert (tmp_path / "figures" / r["filename"]).stat().st_size > 1000
        assert r["title"] and r["caption"] and r["section"]
    assert len(res["figures"]) <= 40  # plot-overload guard (Risk 9)
    assert (tmp_path / "eda_summary.json").exists()
    assert (tmp_path / "tables" / "numeric_summary.md").exists()

    # numbers in the headline match plain pandas
    assert hl["missingness"]["columns"]["income"]["n_missing"] == 10
    assert hl["overview"]["n_rows"] == len(df)
    tgt = hl["target"]
    vc = df["churn"].value_counts()
    assert tgt["minority_class"] == vc.idxmin()
    assert tgt["minority_pct"] == pytest.approx(round(100 * vc.min() / len(df), 2))
    top = hl["numeric_numeric"]["top_pairs"][0]
    assert {top["a"], top["b"]} == {"income", "spend"}
    assert top["spearman"] == pytest.approx(round(df["income"].corr(df["spend"], method="spearman"), 3), abs=1e-3)
    # the ID column never appears in any plot group
    assert "cust_id" not in json.dumps(hl["column_groups"]["numeric"] + hl["column_groups"]["categorical"])


def test_run_eda_core_is_deterministic(tmp_path: Path) -> None:
    df, sem, roles = make_frame()
    a, b = tmp_path / "a", tmp_path / "b"
    run_eda_core(df, sem, roles, "churn", EDASettings(), a)
    run_eda_core(df, sem, roles, "churn", EDASettings(), b)
    pngs_a = sorted(p.name for p in (a / "figures").glob("*.png"))
    assert pngs_a == sorted(p.name for p in (b / "figures").glob("*.png"))
    for name in pngs_a:
        assert (a / "figures" / name).read_bytes() == (b / "figures" / name).read_bytes(), name
    assert (a / "eda_summary.json").read_bytes() == (b / "eda_summary.json").read_bytes()


def test_rerun_removes_stale_figures(tmp_path: Path) -> None:
    df, sem, roles = make_frame()
    (tmp_path / "figures").mkdir(parents=True)
    (tmp_path / "figures" / "old_chart.png").write_bytes(b"stale")
    run_eda_core(df, sem, roles, "churn", EDASettings(), tmp_path)
    assert not (tmp_path / "figures" / "old_chart.png").exists()


def test_eda_text_has_no_inferential_language(tmp_path: Path) -> None:
    df, sem, roles = make_frame()
    res = run_eda_core(df, sem, roles, "churn", EDASettings(), tmp_path)
    text = " ".join(r["title"] + " " + r["caption"] for r in res["figures"]) + " ".join(res["tables"].values())
    text = text.lower()
    for word in FORBIDDEN:
        assert word not in text, word


def test_numeric_target_and_no_missing_values(tmp_path: Path) -> None:
    df, sem, roles = make_frame()
    df = df.drop(columns=["income", "visits"]).dropna()
    sem["spend"] = "numeric_continuous"
    res = run_eda_core(df, sem, roles, "spend", EDASettings(), tmp_path)
    hl = res["headline"]
    assert hl["eda_errors"] == []
    assert hl["target"]["kind"] == "numeric"
    assert hl["missingness"]["missing_cells"] == 0
    names = {r["filename"] for r in res["figures"]}
    assert "target_distribution.png" in names and "missing_bar.png" not in names
    measures = {f["measure"] for f in hl["target_relationships"]["features"]}
    assert measures <= {"Spearman rho", "eta²"}


@pytest.mark.parametrize(
    "frame,sem",
    [
        (pd.DataFrame({"x": [1.0]}), {"x": "numeric_continuous"}),
        (pd.DataFrame({"x": [np.nan, np.nan, np.nan]}), {"x": "numeric_continuous"}),
        (pd.DataFrame({"c": ["a", "a", "a"]}), {"c": "constant"}),
        (pd.DataFrame({"c": ["a", "b", None, "b"], "k": ["x", "x", "x", "x"]}), {"c": "categorical_nominal", "k": "categorical_nominal"}),
        (pd.DataFrame({"x": [1.0, 2.0, 3.0, 4.0], "y": [5.0, 5.0, 5.0, 5.0]}), {"x": "numeric_continuous", "y": "numeric_continuous"}),
    ],
)
def test_degenerate_frames_do_not_crash(tmp_path: Path, frame: pd.DataFrame, sem: dict[str, str]) -> None:
    res = run_eda_core(frame, sem, {}, None, EDASettings(), tmp_path)
    assert res["headline"]["eda_errors"] == []


def test_wide_frame_respects_plot_caps(tmp_path: Path) -> None:
    rng = np.random.default_rng(1)
    df = pd.DataFrame({f"n{i:02d}": rng.normal(i, 1 + i, 120) for i in range(40)})
    sem = {c: "numeric_continuous" for c in df.columns}
    settings = EDASettings(max_numeric_plots=10)
    res = run_eda_core(df, sem, {}, None, settings, tmp_path)
    assert len(res["headline"]["column_groups"]["numeric"]) == 10
    assert any("only the 10" in n for n in res["headline"]["notes"])
