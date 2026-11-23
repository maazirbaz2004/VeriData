"""Named benchmark suites and the dev/test seed split (Phase 4, Sections 2 and 4.5)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from itertools import product
from pathlib import Path
from typing import Any

import numpy as np
import yaml

from veridata.benchmark.generator import NullBlocks, Scenario

SUITES_YAML = Path("configs/benchmark/suites.yaml")
PROTOCOL_PATH = Path("docs/eval_protocol.md")
DEV_SEED_RANGE = range(1000)
TEST_SEED_RANGE = range(10000, 11000)


class SplitGuardError(RuntimeError):
    """Raised when the frozen test split is requested without the explicit confirmation."""


@dataclass(frozen=True)
class DatasetSpec:
    scenario: Scenario
    seed: int
    split: str

    @property
    def dataset_id(self) -> str:
        return f"{self.scenario.scenario_id}__seed{self.seed}"


def _load_yaml(path: Path | None = None) -> dict[str, Any]:
    p = path or SUITES_YAML
    if not p.exists():  # allow running from another working directory
        p = Path(__file__).resolve().parents[3] / "configs" / "benchmark" / "suites.yaml"
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def check_split(split: str, *, confirm_final: bool = False, protocol_path: Path | None = None) -> None:
    """Dev is always allowed. Test needs --confirm-final AND a protocol marked 'Status: FROZEN'."""
    if split == "dev":
        return
    if split != "test":
        raise ValueError(f"split must be 'dev' or 'test', got {split!r}")
    if not confirm_final:
        raise SplitGuardError("The test split is used once, in Phase 8. Pass --confirm-final to use it.")
    p = protocol_path or PROTOCOL_PATH
    text = p.read_text(encoding="utf-8") if p.exists() else ""
    if "Status: FROZEN" not in text:
        raise SplitGuardError(f"{p} is not marked 'Status: FROZEN'; freeze the evaluation protocol first.")


def _core60(cfg: dict[str, Any]) -> list[Scenario]:
    rng = np.random.default_rng(int(cfg["design_seed"]))
    out: list[Scenario] = []
    dists, imb, miss = cfg["dists"], cfg["imbalance"], cfg["missing_rates"]
    # zero-effect datasets: one per (n, p) cell
    null_cells = list(product(cfg["n_rows"], cfg["n_cols"]))
    block_null_idx = set(rng.choice(len(null_cells), size=4, replace=False).tolist())
    for i, (n, p) in enumerate(null_cells):
        nb = NullBlocks(n_blocks=1, block_size=min(4, p // 3), within_corr=0.6) if i in block_null_idx else NullBlocks()
        out.append(Scenario(
            scenario_id=f"c{len(out):02d}_null_n{n}_p{p}", n_rows=n, n_cols=p, n_effects=0,
            dist=dists[i % len(dists)], imbalance=imb[i % len(imb)], missing_rate=0.0, null_blocks=nb,
        ))
    # effect datasets: each (n, p, k) cell gets `strengths_per_cell` strengths, rotated
    strengths = list(cfg["strengths"])
    offset = int(rng.integers(0, len(strengths)))
    cells = list(product(cfg["n_rows"], cfg["n_cols"], cfg["n_effects"]))
    j = 0
    for ci, (n, p, k) in enumerate(cells):
        for s in range(int(cfg["strengths_per_cell"])):
            strength = strengths[(offset + ci * int(cfg["strengths_per_cell"]) + s) % len(strengths)]
            wide = p >= 30
            nb = NullBlocks()
            if wide and j % int(cfg["null_blocks_every"]) == 0:
                nb = NullBlocks(n_blocks=1 + (j // 3) % 2, block_size=4, within_corr=[0.3, 0.6][(j // 3) % 2])
            out.append(Scenario(
                scenario_id=f"c{len(out):02d}_n{n}_p{p}_k{k}_{strength}",
                n_rows=n, n_cols=p, n_effects=k, effect_strength=strength,
                dist=dists[(j + 2) % len(dists)], imbalance=imb[(j + 1) % len(imb)], missing_rate=miss[j % len(miss)],
                null_blocks=nb,
                n_nonlinear_decoys=1 if wide and j % int(cfg["decoys_every"]) == 1 else 0,
                n_interaction_decoys=1 if wide and j % int(cfg["interaction_every"]) == 2 else 0,
                confounder="common_cause" if j % int(cfg["confounder_every"]) == 3 else "none",
            ))
            j += 1
    return out


def suite_scenarios(suite: str, path: Path | None = None) -> list[Scenario]:
    cfg = _load_yaml(path)
    s = cfg["suites"][suite]
    if suite == "core60":
        return _core60(s)
    return [Scenario(**item) for item in s["scenarios"]]


def suite_specs(suite: str, split: str, *, confirm_final: bool = False, path: Path | None = None) -> list[DatasetSpec]:
    check_split(split, confirm_final=confirm_final)
    cfg = _load_yaml(path)
    base = int(cfg["dev_seed_base"] if split == "dev" else cfg["test_seed_base"])
    reps = int(cfg["suites"][suite].get("seeds_per_scenario", 1))
    specs = []
    for i, sc in enumerate(suite_scenarios(suite, path)):
        for r in range(reps):
            seed = base + 10 * i + r
            rng_ok = DEV_SEED_RANGE if split == "dev" else TEST_SEED_RANGE
            assert seed in rng_ok, f"seed {seed} outside the {split} range"
            specs.append(DatasetSpec(scenario=sc, seed=seed, split=split))
    return specs


def suite_hash(suite: str, path: Path | None = None) -> str:
    payload = json.dumps([s.model_dump(mode="json") for s in suite_scenarios(suite, path)], sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]
