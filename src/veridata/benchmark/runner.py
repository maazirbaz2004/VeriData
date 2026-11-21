"""Benchmark runner: generate suites, run systems with caching, evaluate (Phase 4, Sections 5, 6, 9).

Layout (under ``outputs/benchmark``)::

    <suite>/<split>/<dataset_id>/{data.csv, truth.json, scenario.json}
    <suite>/<split>/results/<system>/<dataset_id>.json      # SystemOutput + cache_key
    <suite>/<split>/results/{metrics.csv, summary.csv, summary.md, stratified_*.csv, q_calibration.csv}
    <suite>/<split>/runtime.csv

Systems only ever see ``data.csv``; ``truth.json`` and ``scenario.json`` are read by the evaluator.
"""

from __future__ import annotations

import csv
import hashlib
import json
import logging
import time
import traceback
from collections.abc import Callable
from pathlib import Path
from typing import Any

from joblib import Parallel, delayed

from veridata.benchmark.generator import GENERATOR_VERSION, make_dataset, save_dataset
from veridata.benchmark.matcher import match_findings
from veridata.benchmark.metrics import aggregate, dataset_metrics, q_calibration, stratified_recall
from veridata.benchmark.suites import DatasetSpec, suite_hash, suite_specs
from veridata.benchmark.systems import DEFAULT_VARIANTS, get_variant, run_veridata_variants
from veridata.benchmark.truth import GroundTruth, SystemOutput

logger = logging.getLogger("veridata.benchmark")
OUT_ROOT = Path("outputs/benchmark")
_SRC = Path(__file__).resolve().parents[1]


def code_version() -> str:
    """Hash of the code a system's answers depend on (part of every result cache key).

    The evaluator (matcher, metrics, runner) is deliberately excluded: changing how results are
    scored must not force the systems to run again.
    """
    h = hashlib.sha256(b"systems-v1")
    h.update((_SRC / "benchmark" / "systems.py").read_bytes())
    for sub in ["stats", "validation", "hypotheses", "cleaning", "contracts"]:
        for f in sorted((_SRC / sub).rglob("*.py")):
            h.update(f.read_bytes())
    for f in ["config.py", "profiling.py", "type_inference.py", "ingestion.py", "schemas.py"]:
        p = _SRC / f
        if p.exists():
            h.update(p.read_bytes())
    return h.hexdigest()[:16]


def split_dir(suite: str, split: str, out_root: Path | str = OUT_ROOT) -> Path:
    return Path(out_root) / suite / split


def generator_version() -> str:
    """Hash of the code that decides the generated data and truth."""
    h = hashlib.sha256(GENERATOR_VERSION.encode())
    for f in ["generator.py", "dag.py", "truth.py"]:
        h.update((_SRC / "benchmark" / f).read_bytes())
    return h.hexdigest()[:16]


def _file_hash(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def _cache_key(system: str, data_hash: str, seed: int, version: str) -> str:
    v = get_variant(system)
    payload = json.dumps({"system": v.__dict__, "data": data_hash, "seed": seed, "code": version}, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()[:20]


# ---------------------------------------------------------------------------------------
# generation
# ---------------------------------------------------------------------------------------


def _gen_one(spec: DatasetSpec, d: Path) -> str:
    meta = d / "scenario.json"
    if meta.exists() and (d / "data.csv").exists() and (d / "truth.json").exists():
        old = json.loads(meta.read_text(encoding="utf-8"))
        if old.get("scenario") == spec.scenario.model_dump(mode="json") and old.get("seed") == spec.seed and old.get("generator_code") == generator_version():
            return "cached"
    df, truth, structure = make_dataset(spec.scenario, spec.seed)
    save_dataset(d, df, truth, spec.scenario, structure)
    meta = json.loads(meta.read_text(encoding="utf-8"))
    meta["generator_code"] = generator_version()
    (d / "scenario.json").write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return "generated"


def _filter(specs: list[DatasetSpec], only: list[str] | None) -> list[DatasetSpec]:
    return [s for s in specs if only is None or s.dataset_id in only]


def generate_suite(suite: str, split: str, *, out_root: Path | str = OUT_ROOT, n_jobs: int = 1, confirm_final: bool = False, only: list[str] | None = None) -> list[Path]:
    specs = _filter(suite_specs(suite, split, confirm_final=confirm_final), only)
    base = split_dir(suite, split, out_root)
    dirs = [base / s.dataset_id for s in specs]
    status = Parallel(n_jobs=n_jobs)(delayed(_gen_one)(s, d) for s, d in zip(specs, dirs))
    (base / "suite.json").write_text(
        json.dumps({"suite": suite, "split": split, "suite_hash": suite_hash(suite), "datasets": [s.dataset_id for s in specs], "generator_version": GENERATOR_VERSION}, indent=2) + "\n",
        encoding="utf-8",
    )
    logger.info("suite %s/%s: %d generated, %d cached", suite, split, status.count("generated"), status.count("cached"))
    return dirs


# ---------------------------------------------------------------------------------------
# running systems
# ---------------------------------------------------------------------------------------


def _run_dataset(d: Path, dataset_id: str, systems: list[str]) -> dict[str, dict[str, Any]]:
    try:
        outs = run_veridata_variants(d / "data.csv", dataset_id, systems)
        return {k: v.model_dump(mode="json") for k, v in outs.items()}
    except Exception as exc:  # noqa: BLE001 — one dataset failing must not kill the suite
        err = f"{type(exc).__name__}: {exc}"
        logger.warning("dataset %s failed: %s", dataset_id, err)
        tb = traceback.format_exc(limit=5)
        return {s: SystemOutput(system_name=s, dataset_id=dataset_id, error=err, meta={"traceback": tb}).model_dump(mode="json") for s in systems}


def run_suite(
    suite: str,
    split: str,
    systems: list[str] | None = None,
    *,
    out_root: Path | str = OUT_ROOT,
    n_jobs: int = 1,
    use_cache: bool = True,
    confirm_final: bool = False,
    progress: Callable[[str], None] | None = None,
    only: list[str] | None = None,
) -> dict[str, Any]:
    systems = systems or list(DEFAULT_VARIANTS)
    if split != "dev" and any(s.startswith("tune_") for s in systems):
        raise ValueError("tuning variants may only run on the dev split")
    specs = _filter(suite_specs(suite, split, confirm_final=confirm_final), only)
    base = split_dir(suite, split, out_root)
    version = code_version()
    todo: list[tuple[DatasetSpec, list[str]]] = []
    for spec in specs:
        d = base / spec.dataset_id
        if not (d / "data.csv").exists():
            raise FileNotFoundError(f"{d} missing; run `veridata bench gen --suite {suite} --split {split}` first")
        need = []
        dh = _file_hash(d / "data.csv")
        for s in systems:
            f = base / "results" / s / f"{spec.dataset_id}.json"
            key = _cache_key(s, dh, spec.seed, version)
            if use_cache and f.exists():
                try:
                    if json.loads(f.read_text(encoding="utf-8")).get("cache_key") == key:
                        continue
                except json.JSONDecodeError:
                    pass
            need.append(s)
        if need:
            todo.append((spec, need))
    t0 = time.perf_counter()
    outputs = Parallel(n_jobs=n_jobs, verbose=0)(delayed(_run_dataset)(base / spec.dataset_id, spec.dataset_id, need) for spec, need in todo)
    runtime_rows = []
    for (spec, need), out in zip(todo, outputs):
        dh = _file_hash(base / spec.dataset_id / "data.csv")
        for s in need:
            rec = out[s]
            rec["cache_key"] = _cache_key(s, dh, spec.seed, version)
            rec["code_version"] = version
            p = base / "results" / s / f"{spec.dataset_id}.json"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n", encoding="utf-8")
        first = out[need[0]]
        runtime_rows.append({
            "dataset_id": spec.dataset_id, "n_rows": spec.scenario.n_rows, "n_cols": spec.scenario.n_cols,
            "n_tests": first.get("n_tests_attempted"), "prep_s": first.get("meta", {}).get("prep_s"),
            "stage_a_s": first.get("meta", {}).get("stage_a_s"), "error": first.get("error"),
        })
        if progress:
            progress(spec.dataset_id)
    if runtime_rows:
        _append_csv(base / "runtime.csv", runtime_rows)
    return {"n_datasets": len(specs), "n_run": len(todo), "elapsed_s": round(time.perf_counter() - t0, 1), "code_version": version}


def _append_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing: dict[str, dict[str, Any]] = {}
    if path.exists():
        with path.open(encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                existing[r["dataset_id"]] = r
    for r in rows:
        existing[r["dataset_id"]] = r
    fields = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for k in sorted(existing):
            w.writerow(existing[k])


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields: list[str] = []
    for r in rows:
        for k in r:
            if k not in fields:
                fields.append(k)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


# ---------------------------------------------------------------------------------------
# evaluation
# ---------------------------------------------------------------------------------------


def evaluate_suite(
    suite: str,
    split: str,
    systems: list[str] | None = None,
    *,
    out_root: Path | str = OUT_ROOT,
    n_resamples: int = 2000,
    confirm_final: bool = False,
    only: list[str] | None = None,
    write: bool = True,
) -> dict[str, Any]:
    systems = systems or list(DEFAULT_VARIANTS)
    specs = _filter(suite_specs(suite, split, confirm_final=confirm_final), only)
    base = split_dir(suite, split, out_root)
    metric_rows: list[dict[str, Any]] = []
    pair_rows: list[dict[str, Any]] = []
    finding_rows: list[dict[str, Any]] = []
    summary: dict[str, Any] = {}
    errors: dict[str, int] = {}
    truths = {s.dataset_id: GroundTruth.load(base / s.dataset_id / "truth.json") for s in specs}
    scen = {s.dataset_id: json.loads((base / s.dataset_id / "scenario.json").read_text(encoding="utf-8"))["scenario"] for s in specs}
    for system in systems:
        per_mode: dict[str, list[dict[str, Any]]] = {"if_reported": [], "ignore": []}
        errors[system] = 0
        for spec in specs:
            f = base / "results" / system / f"{spec.dataset_id}.json"
            if not f.exists():
                errors[system] += 1
                continue
            out = SystemOutput.model_validate({k: v for k, v in json.loads(f.read_text(encoding="utf-8")).items() if k not in {"cache_key", "code_version"}})
            if out.error:
                errors[system] += 1
                continue
            truth = truths[spec.dataset_id]
            for mode in ("if_reported", "ignore"):
                m = match_findings(out.findings, truth, mode)  # type: ignore[arg-type]
                row = dataset_metrics(m, truth, scen[spec.dataset_id])
                row.update({"system": system, "direction_mode": mode, "runtime_s": out.runtime_s})
                per_mode[mode].append(row)
                metric_rows.append(row)
                if mode == "if_reported":
                    sc = scen[spec.dataset_id]
                    for t in m.truths:
                        pair_rows.append({**t.model_dump(), "system": system, "dataset_id": spec.dataset_id, "n_rows": truth.n_rows, "n_cols": len(truth.columns), "dist": sc.get("dist")})
                    for fm in m.findings:
                        finding_rows.append({**fm.model_dump(), "system": system, "dataset_id": spec.dataset_id})
        summary[system] = {mode: aggregate(rows, n_resamples=n_resamples, seed=0) for mode, rows in per_mode.items()}
        summary[system]["n_errors"] = errors[system]
    res = base / "results"
    flat = []
    for system, s in summary.items():
        for mode in ("if_reported", "ignore"):
            flat.append({"system": system, "direction_mode": mode, "n_errors": s["n_errors"], **s[mode]})
    strat = {}
    for name, by in {"form": ["system", "form"], "bin": ["system", "form", "bin"], "n": ["system", "n_rows"], "p": ["system", "n_cols"], "dist": ["system", "dist"], "power": ["system", "form", "n_rows", "bin"]}.items():
        strat[name] = stratified_recall(pair_rows, by)
    qcal = []
    for system in systems:
        for r in q_calibration([f for f in finding_rows if f["system"] == system]):
            qcal.append({"system": system, **r})
    if write:
        _write_csv(res / "metrics.csv", metric_rows)
        _write_csv(res / "summary.csv", flat)
        for name, rows in strat.items():
            _write_csv(res / f"stratified_{name}.csv", rows)
        _write_csv(res / "q_calibration.csv", qcal)
        (res / "summary.md").write_text(render_summary_md(suite, split, summary, strat, n_resamples), encoding="utf-8")
    return {"summary": summary, "stratified": strat, "q_calibration": qcal, "metric_rows": metric_rows}


def _fmt(v: Any, pct: bool = False) -> str:
    if v is None:
        return "–"
    if isinstance(v, float):
        return f"{100 * v:.1f}%" if pct else f"{v:.3f}"
    return str(v)


def _ci(s: dict[str, Any], k: str, pct: bool = True) -> str:
    lo, hi = s.get(f"{k}_ci_low"), s.get(f"{k}_ci_high")
    if lo is None or hi is None:
        return _fmt(s.get(k), pct)
    return f"{_fmt(s.get(k), pct)} [{_fmt(lo, pct)}, {_fmt(hi, pct)}]"


def render_summary_md(suite: str, split: str, summary: dict[str, Any], strat: dict[str, list[dict[str, Any]]], n_resamples: int = 2000) -> str:
    lines = [
        f"# Benchmark results — `{suite}` / `{split}`",
        "",
        (
            "Primary direction mode (`if_reported`): a true pair reported with the wrong sign / higher group counts as a false discovery. "
            f"Brackets are 95% bootstrap CIs over datasets ({n_resamples:,} resamples)."
        ),
        "",
        "| System | Datasets | FDR (mean FDP) | Recall (testable truths) | Precision | FWER on zero-effect datasets | Mean reported | Mean false | Errors |",
        "| :--- | ---: | :--- | :--- | :--- | :--- | ---: | ---: | ---: |",
    ]
    for system, s in summary.items():
        p = s["if_reported"]
        lines.append(
            f"| `{system}` | {p['n_datasets']} | {_ci(p, 'fdr')} | {_ci(p, 'recall')} | {_ci(p, 'precision')} | {_ci(p, 'fwer_null')} | "
            f"{_fmt(p['mean_reported'])} | {_fmt(p['mean_fp'])} | {s['n_errors']} |"
        )
    lines += ["", "## Pair-only matching (direction ignored)", "", "| System | FDR | Recall |", "| :--- | :--- | :--- |"]
    for system, s in summary.items():
        p = s["ignore"]
        lines.append(f"| `{system}` | {_ci(p, 'fdr')} | {_ci(p, 'recall')} |")
    lines += ["", "## Recall by effect form", "", "| System | Form | Truths | Recall |", "| :--- | :--- | ---: | ---: |"]
    for r in strat.get("form", []):
        lines.append(f"| `{r['system']}` | {r['form']} | {r['n_truths']} | {_fmt(r['recall'], True)} |")
    lines += ["", "## Recall by sample size", "", "| System | n | Truths | Recall |", "| :--- | ---: | ---: | ---: |"]
    for r in strat.get("n", []):
        lines.append(f"| `{r['system']}` | {r['n_rows']} | {r['n_truths']} | {_fmt(r['recall'], True)} |")
    return "\n".join(lines) + "\n"
