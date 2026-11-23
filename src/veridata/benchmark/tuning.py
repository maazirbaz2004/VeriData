"""Effect-floor tuning on the dev split only (Phase 4, Section 8).

Pre-declared grid: every effect-floor threshold multiplied by m in TUNING_GRID. Objective:
maximise mean recall subject to mean FDP <= 0.05 on the dev split; tie-break by closeness to the
conventional values (m = 1). Rule against overfitting: if the winner is within one grid step of
m = 1, keep the conventional values. ``large_n_clt`` and ``extreme_skew`` are NOT tuned (they change
test selection and would need new Stage-A runs; kept at their documented defaults).
"""

from __future__ import annotations

import itertools
from pathlib import Path
from typing import Any

import yaml

from veridata.benchmark.runner import OUT_ROOT, evaluate_suite
from veridata.benchmark.systems import (
    TUNING_GRID,
    benchmark_config,
    get_variant,
    tuning_variant_names,
    variant_config,
)


def tune(suite: str = "core60", split: str = "dev", *, out_root: Path | str = OUT_ROOT, max_fdp: float = 0.05, grid: tuple[float, ...] = TUNING_GRID, write: bool = True) -> dict[str, Any]:
    assert split == "dev", "tuning is only allowed on the dev split"
    names = tuning_variant_names(grid)
    ev = evaluate_suite(suite, split, names, out_root=out_root, n_resamples=500, write=False)
    rows = []
    for m, name in zip(grid, names):
        s = ev["summary"][name]["if_reported"]
        rows.append({"multiplier": m, "system": name, "fdr": s["fdr"], "recall": s["recall"], "fwer_null": s["fwer_null"], "precision": s["precision"], "n_datasets": s["n_datasets"]})
    feasible = [r for r in rows if r["fdr"] is not None and r["fdr"] <= max_fdp and r["recall"] is not None]
    step = min(abs(b - a) for a, b in itertools.pairwise(grid)) if len(grid) > 1 else 0.0
    if feasible:
        best = max(feasible, key=lambda r: (round(r["recall"], 4), -abs(r["multiplier"] - 1.0)))
        chosen = 1.0 if abs(best["multiplier"] - 1.0) <= step + 1e-9 else best["multiplier"]
        reason = (
            f"best feasible multiplier {best['multiplier']} is within one grid step of the conventions -> keep conventional values"
            if chosen == 1.0
            else f"multiplier {chosen} gives the highest recall with mean FDP <= {max_fdp}"
        )
    else:
        best, chosen, reason = None, 1.0, f"no grid point met mean FDP <= {max_fdp}; conventional values kept"
    cfg = variant_config(benchmark_config(), get_variant(f"tune_floor_x{chosen:.2f}"))
    floors = {k: v for k, v in cfg.effect_floor.model_dump().items() if isinstance(v, float)}
    result = {"suite": suite, "split": split, "max_fdp": max_fdp, "grid": list(grid), "rows": rows, "best": best, "chosen_multiplier": chosen, "reason": reason, "effect_floor": floors}
    if write:
        out = Path(out_root) / "tuning"
        out.mkdir(parents=True, exist_ok=True)
        (out / "tuning_report.md").write_text(render_tuning_md(result), encoding="utf-8")
        Path("configs").mkdir(exist_ok=True)
        Path("configs/tuned_defaults.yaml").write_text(
            "# Produced by `veridata bench tune` on the dev split (Phase 4, Section 8). Do not edit by hand.\n"
            + yaml.safe_dump({"suite": suite, "split": split, "chosen_multiplier": chosen, "reason": reason, "effect_floor": floors}, sort_keys=True),
            encoding="utf-8",
        )
    return result


def render_tuning_md(r: dict[str, Any]) -> str:
    def pct(v: float | None) -> str:
        return "–" if v is None else f"{100 * v:.1f}%"

    lines = [
        f"# Effect-floor tuning — `{r['suite']}` / `{r['split']}`",
        "",
        f"Objective: highest mean recall with mean FDP ≤ {pct(r['max_fdp'])}. Grid: every floor × {', '.join(str(m) for m in r['grid'])}.",
        "",
        "| Multiplier | Mean FDP (FDR) | Recall | FWER on zero-effect datasets | Precision |",
        "| ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in r["rows"]:
        lines.append(f"| {row['multiplier']} | {pct(row['fdr'])} | {pct(row['recall'])} | {pct(row['fwer_null'])} | {pct(row['precision'])} |")
    lines += ["", f"**Decision:** multiplier **{r['chosen_multiplier']}** — {r['reason']}.", "", "Resulting floors:", ""]
    for k, v in sorted(r["effect_floor"].items()):
        lines.append(f"- `{k}` = {v}")
    return "\n".join(lines) + "\n"
