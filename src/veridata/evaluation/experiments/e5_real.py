"""E5 — Real-dataset evaluation (reference recovery, permuted nulls, noise columns, split-half, stability)."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml
from joblib import Parallel, delayed

from veridata.agent.llm import LLMClient, NullLLM
from veridata.benchmark.matcher import _norm_level
from veridata.benchmark.truth import ReportedFinding, SystemOutput, pair_key
from veridata.config import PipelineConfig, load_config
from veridata.errors import LLMUnavailable
from veridata.evaluation.budget import BudgetExceededError, CostTracker
from veridata.evaluation.stats_utils import mean_pairwise_jaccard
from veridata.evaluation.systems.llm_only import (
    LLM_SYSTEM_IDS,
    run_llm_only_system,
    summarize_llm_error,
)

REAL_DATASETS = (
    "insurance",
    "telco_churn",
    "heart_disease",
    "student_performance",
    "bank_marketing",
)


def _load_ref_findings(ds: str, ref_dir: Path) -> dict[str, Any]:
    p = ref_dir / f"{ds}.yaml"
    if not p.exists():
        return {"dataset": ds, "reference_findings": [], "known_nulls": []}
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}


def _direction_matches_ref(rep: ReportedFinding, ref: dict[str, Any]) -> bool:
    exp = ref.get("direction")
    if not exp or not rep.direction:
        return True
    if exp.get("kind") == "sign" and rep.direction.get("kind") == "sign":
        return exp.get("value") == rep.direction.get("value")
    if exp.get("kind") == "group_diff" and rep.direction.get("kind") == "group_diff":
        if exp.get("group_col") != rep.direction.get("group_col"):
            return True
        return _norm_level(exp.get("higher_level")) == _norm_level(rep.direction.get("higher_level"))
    return True


def _score_reference_recovery(findings: list[ReportedFinding], ref_doc: dict[str, Any]) -> dict[str, Any]:
    refs = [
        r
        for r in ref_doc.get("reference_findings", [])
        if r.get("confidence", "strong") in {"strong", "moderate"}
    ]
    by_pair = {pair_key(f.col_a, f.col_b): f for f in findings}
    hits = 0
    for r in refs:
        k = pair_key(r["col_a"], r["col_b"])
        if k in by_pair and _direction_matches_ref(by_pair[k], r):
            hits += 1
    nulls = ref_doc.get("known_nulls", [])
    null_fp = sum(1 for n in nulls if pair_key(n["col_a"], n["col_b"]) in by_pair)
    return {
        "n_ref": len(refs),
        "n_recovered": hits,
        "recovery_rate": float(hits / len(refs)) if refs else None,
        "n_known_nulls": len(nulls),
        "known_null_fp": null_fp,
    }


def _append_permuted_columns(
    df: pd.DataFrame,
    seed: int,
    base_schema: dict[str, Any] | None = None,
) -> tuple[pd.DataFrame, set[str]]:
    rng = np.random.default_rng(seed)
    eligible = [
        str(c)
        for c in df.columns
        if base_schema is None
        or (str(c) in base_schema and str(base_schema[str(c)].role.value) in {"feature", "target_candidate"})
    ]
    if not eligible:
        eligible = [str(c) for c in df.columns]
    p = len(eligible)
    k = max(5, math.ceil(0.25 * p))
    chosen_idx = rng.choice(p, size=min(k, p), replace=True)
    out = df.copy()
    perm_cols: set[str] = set()
    for i, idx in enumerate(chosen_idx):
        src = eligible[int(idx)]
        name = f"perm_{i}_{src}"
        vals = df[src].to_numpy().copy()
        rng.shuffle(vals)
        out[name] = vals
        perm_cols.add(name)
    return out, perm_cols


def _append_noise_columns(df: pd.DataFrame, n_noise: int, seed: int) -> tuple[pd.DataFrame, set[str]]:
    rng = np.random.default_rng(seed)
    n = len(df)
    out = df.copy()
    noise_cols: set[str] = set()
    for i in range(n_noise):
        kind = i % 3
        name = f"noise_{i}"
        if kind == 0:
            out[name] = rng.normal(0.0, 1.0, size=n)
        elif kind == 1:
            out[name] = rng.choice(["N0", "N1"], size=n, p=[0.7, 0.3])
        else:
            out[name] = rng.choice(["C0", "C1", "C2", "C3"], size=n)
        noise_cols.add(name)
    return out, noise_cols


def _count_sentinel_fps(findings: list[ReportedFinding], sentinel_cols: set[str]) -> int:
    return sum(1 for f in findings if f.col_a in sentinel_cols or f.col_b in sentinel_cols)


def _derive_extended_schema(df: pd.DataFrame, base_schema: dict[str, Any]) -> dict[str, Any]:
    from veridata.schemas import ColumnRole, ColumnSchemaEntry, SemanticType

    ext: dict[str, Any] = {}
    for col in df.columns:
        c = str(col)
        if c in base_schema:
            ext[c] = base_schema[c]
        elif c.startswith("perm_"):
            src = c.split("_", 2)[2]
            if src in base_schema:
                ext[c] = base_schema[src].model_copy(deep=True)
                continue
        elif c.startswith("noise_"):
            idx = int(c.split("_")[1])
            kind = idx % 3
            sem = SemanticType.NUMERIC_CONTINUOUS if kind == 0 else (
                SemanticType.BINARY if kind == 1 else SemanticType.CATEGORICAL_NOMINAL
            )
            ext[c] = ColumnSchemaEntry(
                semantic_type=sem,
                role=ColumnRole.FEATURE,
                n_unique=int(df[c].nunique(dropna=True)),
                pct_missing=0.0,
            )
    return ext


def _run_variants_with_known_schema(
    df: pd.DataFrame,
    base_schema: dict[str, Any],
    dataset_id: str,
    ds_cfg: PipelineConfig,
) -> dict[str, SystemOutput]:
    from veridata.benchmark.systems import benchmark_config
    from veridata.evaluation.systems.veridata_variants import _run_variants_prepared
    from veridata.hypotheses import generate_hypotheses

    cfg = benchmark_config(ds_cfg)
    schema = _derive_extended_schema(df, base_schema)
    hset = generate_hypotheses(df, schema, None, cfg, llm=None, mode="exhaustive", dataset_name=dataset_id)
    meta = {
        "n_hypotheses": len(hset.hypotheses),
        "n_infeasible": hset.manifest.n_infeasible,
        "excluded_columns": hset.manifest.excluded_columns,
    }
    return _run_variants_prepared(df, hset, meta, dataset_id, ["S3_veridata_full", "S2_veridata_nocorrection"], cfg, 0.0)


def _perm_one(df: pd.DataFrame, base_schema: dict[str, Any], ds: str, s_idx: int, ds_cfg: PipelineConfig) -> tuple[int, int]:
    df_p, p_cols = _append_permuted_columns(df, seed=7000 + s_idx, base_schema=base_schema)
    p_outs = _run_variants_with_known_schema(df_p, base_schema, f"{ds}_perm_{s_idx}", ds_cfg)
    return (
        _count_sentinel_fps(p_outs["S3_veridata_full"].findings, p_cols),
        _count_sentinel_fps(p_outs["S2_veridata_nocorrection"].findings, p_cols),
    )


def _noise_one(
    df: pd.DataFrame,
    base_schema: dict[str, Any],
    ds: str,
    n_noise_cols: int,
    s_idx: int,
    ds_cfg: PipelineConfig,
) -> tuple[int, int]:
    df_n, n_cols = _append_noise_columns(df, n_noise_cols, seed=8000 + s_idx)
    n_outs = _run_variants_with_known_schema(df_n, base_schema, f"{ds}_noise_{s_idx}", ds_cfg)
    return (
        _count_sentinel_fps(n_outs["S3_veridata_full"].findings, n_cols),
        _count_sentinel_fps(n_outs["S2_veridata_nocorrection"].findings, n_cols),
    )


def _split_one(
    df: pd.DataFrame,
    base_schema: dict[str, Any],
    ds: str,
    s_idx: int,
    ds_cfg: PipelineConfig,
) -> dict[str, tuple[float | None, float | None]]:
    rng = np.random.default_rng(9000 + s_idx)
    perm = rng.permutation(len(df))
    mid = len(df) // 2
    df_a = df.iloc[perm[:mid]].reset_index(drop=True)
    df_b = df.iloc[perm[mid:]].reset_index(drop=True)
    out_a = _run_variants_with_known_schema(df_a, base_schema, f"{ds}_sA_{s_idx}", ds_cfg)
    out_b = _run_variants_with_known_schema(df_b, base_schema, f"{ds}_sB_{s_idx}", ds_cfg)
    b_raw_pairs = {pair_key(f.col_a, f.col_b): f for f in out_b["S2_veridata_nocorrection"].findings}
    out_map: dict[str, tuple[float | None, float | None]] = {}
    for sys_id in ("S3_veridata_full", "S2_veridata_nocorrection"):
        a_pairs = {pair_key(f.col_a, f.col_b): f for f in out_a[sys_id].findings}
        b_pairs = {pair_key(f.col_a, f.col_b): f for f in out_b[sys_id].findings}
        if a_pairs:
            strict_hits = sum(1 for k in a_pairs if k in b_pairs)
            loose_hits = sum(1 for k in a_pairs if k in b_raw_pairs)
            out_map[sys_id] = (strict_hits / len(a_pairs), loose_hits / len(a_pairs))
        else:
            out_map[sys_id] = (None, None)
    return out_map


def _boot_one(
    df: pd.DataFrame,
    base_schema: dict[str, Any],
    ds: str,
    b_idx: int,
    ds_cfg: PipelineConfig,
) -> dict[str, set[tuple[str, str]]]:
    rng_b = np.random.default_rng(9500 + b_idx)
    idx = rng_b.integers(0, len(df), size=len(df))
    df_b = df.iloc[idx].reset_index(drop=True)
    outs_b = _run_variants_with_known_schema(df_b, base_schema, f"{ds}_boot_{b_idx}", ds_cfg)
    return {
        sys_id: {pair_key(f.col_a, f.col_b) for f in outs_b[sys_id].findings}
        for sys_id in ("S3_veridata_full", "S2_veridata_nocorrection")
    }


def run_e5(
    *,
    cleaned_dir: Path = Path("data/cleaned"),
    configs_dir: Path = Path("configs/datasets"),
    ref_dir: Path = Path("configs/eval/reference_findings"),
    eval_root: Path = Path("outputs/eval"),
    datasets: tuple[str, ...] = REAL_DATASETS,
    llm: LLMClient | None = None,
    llm_systems: list[str] | None = None,
    skip_unavailable_llm: bool = True,
    cost_tracker: CostTracker | None = None,
    config: PipelineConfig | None = None,
    n_jobs: int = 2,
) -> dict[str, Any]:
    """Run E5 real-dataset evaluation suite (recovery, permutation, noise, split-half, stability)."""
    base_cfg = config or load_config()
    n_perm_cfg = int(base_cfg.eval.permutation_seeds)
    n_noise_seeds = 10
    n_noise_cols = int(base_cfg.eval.noise_columns)
    n_split_cfg = int(base_cfg.eval.split_half_repeats)
    n_boot_cfg = int(base_cfg.eval.bootstrap_stability_repeats)

    out_dir = eval_root / "e5"
    out_dir.mkdir(parents=True, exist_ok=True)
    human_dir = eval_root / "human_sheets"
    human_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = out_dir / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    chosen_llm = llm_systems if llm_systems is not None else list(LLM_SYSTEM_IDS)
    table_rows: list[dict[str, Any]] = []
    details: dict[str, Any] = {}

    for ds in datasets:
        csv_p = cleaned_dir / f"{ds}_cleaned.csv"
        if not csv_p.exists():
            continue
        ds_cfg_p = configs_dir / f"{ds}.yaml"
        ds_cfg = load_config(dataset_config_path=ds_cfg_p if ds_cfg_p.exists() else None)
        df = pd.read_csv(csv_p)
        ref_doc = _load_ref_findings(ds, ref_dir)

        from veridata.profiling import build_column_schema, profile_dataset

        # Compute base schema once so resampling loops skip repeated profiling
        base_profile = profile_dataset(
            df.astype("string").fillna("").astype(str),
            df_naive=df,
            config=ds_cfg,
            dataset_name=ds,
        )
        base_schema = build_column_schema(base_profile, config=ds_cfg)

        # Adaptive resample safeguard for wide (>=20 cols) and 41k-row (bank_marketing) datasets (Decision P8-06)
        large = len(df) > 20_000
        wide = len(df.columns) >= 20
        cap = 3 if large else (5 if wide else 8)
        n_perm = min(n_perm_cfg, cap)
        n_noise_r = min(n_noise_seeds, cap)
        n_split = min(n_split_cfg, cap)
        n_boot = min(n_boot_cfg, cap)

        # Full dataset run (S3 & S2)
        ds_cache = cache_dir / f"{ds}_full.json"
        if ds_cache.exists():
            raw = json.loads(ds_cache.read_text(encoding="utf-8"))
            full_outs = {k: SystemOutput.model_validate(v) for k, v in raw.items()}
        else:
            full_outs = _run_variants_with_known_schema(df, base_schema, ds, ds_cfg)
            ds_cache.write_text(
                json.dumps({k: v.model_dump(mode="json") for k, v in full_outs.items()}, indent=1) + "\n",
                encoding="utf-8",
            )

        # Permutation null check (averaged over seeds)
        perm_cache = cache_dir / f"{ds}_perm.json"
        if perm_cache.exists():
            perm_res = json.loads(perm_cache.read_text(encoding="utf-8"))
        else:
            perm_pairs = Parallel(n_jobs=n_jobs)(
                delayed(_perm_one)(df, base_schema, ds, s_idx, ds_cfg) for s_idx in range(n_perm)
            )
            perm_res = {
                "S3_veridata_full": float(np.mean([p[0] for p in perm_pairs])),
                "S2_veridata_nocorrection": float(np.mean([p[1] for p in perm_pairs])),
                "n_seeds": n_perm,
            }
            perm_cache.write_text(json.dumps(perm_res, indent=2) + "\n", encoding="utf-8")

        # Injected noise columns check
        noise_cache = cache_dir / f"{ds}_noise.json"
        if noise_cache.exists():
            noise_res = json.loads(noise_cache.read_text(encoding="utf-8"))
        else:
            noise_pairs = Parallel(n_jobs=n_jobs)(
                delayed(_noise_one)(df, base_schema, ds, n_noise_cols, s_idx, ds_cfg) for s_idx in range(n_noise_r)
            )
            noise_res = {
                "S3_veridata_full": float(np.mean([p[0] for p in noise_pairs])),
                "S2_veridata_nocorrection": float(np.mean([p[1] for p in noise_pairs])),
                "n_seeds": n_noise_r,
            }
            noise_cache.write_text(json.dumps(noise_res, indent=2) + "\n", encoding="utf-8")

        # Split-half replication (strict = accepted on B; loose = raw p<0.05 on B)
        split_cache = cache_dir / f"{ds}_split.json"
        if split_cache.exists():
            split_res = json.loads(split_cache.read_text(encoding="utf-8"))
        else:
            split_runs = Parallel(n_jobs=n_jobs)(
                delayed(_split_one)(df, base_schema, ds, s_idx, ds_cfg) for s_idx in range(n_split)
            )
            rep_strict: dict[str, list[float]] = {"S3_veridata_full": [], "S2_veridata_nocorrection": []}
            rep_loose: dict[str, list[float]] = {"S3_veridata_full": [], "S2_veridata_nocorrection": []}
            for sr in split_runs:
                for sys_id in ("S3_veridata_full", "S2_veridata_nocorrection"):
                    st_val, lo_val = sr[sys_id]
                    if st_val is not None:
                        rep_strict[sys_id].append(st_val)
                    if lo_val is not None:
                        rep_loose[sys_id].append(lo_val)
            split_res = {
                sys_id: {
                    "strict_replication": float(np.mean(rep_strict[sys_id])) if rep_strict[sys_id] else None,
                    "loose_replication": float(np.mean(rep_loose[sys_id])) if rep_loose[sys_id] else None,
                }
                for sys_id in ("S3_veridata_full", "S2_veridata_nocorrection")
            }
            split_cache.write_text(json.dumps(split_res, indent=2) + "\n", encoding="utf-8")

        # Bootstrap stability (Jaccard)
        boot_cache = cache_dir / f"{ds}_boot.json"
        if boot_cache.exists():
            boot_res = json.loads(boot_cache.read_text(encoding="utf-8"))
        else:
            boot_runs = Parallel(n_jobs=n_jobs)(
                delayed(_boot_one)(df, base_schema, ds, b_idx, ds_cfg) for b_idx in range(n_boot)
            )
            sets_by_sys: dict[str, list[set[tuple[str, str]]]] = {
                "S3_veridata_full": [br["S3_veridata_full"] for br in boot_runs],
                "S2_veridata_nocorrection": [br["S2_veridata_nocorrection"] for br in boot_runs],
            }
            boot_res = {sys_id: mean_pairwise_jaccard(pair_sets) for sys_id, pair_sets in sets_by_sys.items()}
            boot_cache.write_text(json.dumps(boot_res, indent=2) + "\n", encoding="utf-8")

        # Optional LLM baselines on real dataset (R=repeats_real)
        llm_real_runs: dict[str, list[SystemOutput]] = {}
        n_rep_real = int(base_cfg.eval.repeats_real)
        for sys_id in chosen_llm:
            runs: list[SystemOutput] = []
            for r in range(n_rep_real):
                cp = cache_dir / f"{ds}_{sys_id}__r{r}.json"
                if cp.exists():
                    try:
                        runs.append(SystemOutput.model_validate_json(cp.read_text(encoding="utf-8")))
                        continue
                    except (OSError, ValueError) as exc:
                        _ = str(exc)
                if llm is None or isinstance(llm, NullLLM):
                    if not skip_unavailable_llm:
                        raise LLMUnavailable(f"LLM unavailable for E5 {sys_id}.")
                    continue
                try:
                    out = run_llm_only_system(
                        sys_id,
                        csv_p,
                        ds,
                        llm=llm,
                        temperature=float(base_cfg.eval.repeat_temperature),
                        repeat_idx=r,
                        max_turns=int(base_cfg.eval.code_sandbox_max_turns),
                        sandbox_timeout_s=float(base_cfg.eval.code_sandbox_timeout_s),
                        cost_tracker=cost_tracker,
                    )
                    cp.write_text(out.model_dump_json(indent=1) + "\n", encoding="utf-8")
                    runs.append(out)
                except BudgetExceededError:
                    break
                except Exception as exc:  # noqa: BLE001
                    cp.write_text(summarize_llm_error(sys_id, ds, exc).model_dump_json(indent=1) + "\n", encoding="utf-8")
            if runs:
                llm_real_runs[sys_id] = runs

        for sys_id in ("S3_veridata_full", "S2_veridata_nocorrection"):
            rec = _score_reference_recovery(full_outs[sys_id].findings, ref_doc)
            row = {
                "dataset": ds,
                "n_rows": len(df),
                "n_cols": len(df.columns),
                "system": sys_id,
                "n_reported": len(full_outs[sys_id].findings),
                "ref_recovery_rate": rec["recovery_rate"],
                "ref_hits": f"{rec['n_recovered']}/{rec['n_ref']}",
                "known_null_fp": rec["known_null_fp"],
                "perm_mean_fp": perm_res[sys_id],
                "noise_mean_fp": noise_res[sys_id],
                "split_strict_rep": split_res[sys_id]["strict_replication"],
                "split_loose_rep": split_res[sys_id]["loose_replication"],
                "bootstrap_jaccard": boot_res[sys_id],
            }
            table_rows.append(row)

        for sys_id, runs in llm_real_runs.items():
            recs = [_score_reference_recovery(r.findings, ref_doc)["recovery_rate"] for r in runs]
            valid_recs = [v for v in recs if v is not None]
            table_rows.append(
                {
                    "dataset": ds,
                    "n_rows": len(df),
                    "n_cols": len(df.columns),
                    "system": sys_id,
                    "n_reported": float(np.mean([len(r.findings) for r in runs])),
                    "ref_recovery_rate": float(np.mean(valid_recs)) if valid_recs else None,
                    "ref_hits": f"R={len(runs)}",
                    "known_null_fp": float(np.mean([_score_reference_recovery(r.findings, ref_doc)["known_null_fp"] for r in runs])),
                    "perm_mean_fp": None,
                    "noise_mean_fp": None,
                    "split_strict_rep": None,
                    "split_loose_rep": None,
                    "bootstrap_jaccard": None,
                }
            )

        # Blind qualitative comparison sheet for human annotation (shuffled system labels)
        blind_rows: list[dict[str, Any]] = []
        sys_pool: list[tuple[str, SystemOutput]] = [("S3", full_outs["S3_veridata_full"]), ("S2", full_outs["S2_veridata_nocorrection"])]
        for sys_id, runs in llm_real_runs.items():
            if runs:
                sys_pool.append((sys_id, runs[0]))
        rng_shuf = np.random.default_rng(101)
        labels = [f"system_{chr(65 + i)}" for i in range(len(sys_pool))]
        rng_shuf.shuffle(labels)
        key_map = {}
        for anon_lbl, (real_name, out) in zip(labels, sys_pool):
            key_map[anon_lbl] = real_name
            for f in out.findings[:25]:
                blind_rows.append(
                    {
                        "anon_system": anon_lbl,
                        "col_a": f.col_a,
                        "col_b": f.col_b,
                        "direction": json.dumps(f.direction) if f.direction else "",
                        "effect": f.effect,
                        "q_or_p": f.q_value if f.q_value is not None else f.p_value,
                        "claim_text": f.claim_text or "",
                        "human_annotation": "",
                    }
                )
        rng_shuf.shuffle(blind_rows)
        pd.DataFrame(blind_rows).to_csv(human_dir / f"e5_blind_{ds}.csv", index=False)
        details[ds] = {"blind_key": key_map, "perm": perm_res, "noise": noise_res, "split_half": split_res, "bootstrap": boot_res}

    payload = {"datasets": list(details.keys()), "table": table_rows, "details": details}
    (out_dir / "summary.json").write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    pd.DataFrame(table_rows).to_csv(out_dir / "real_datasets_table.csv", index=False)
    return payload
