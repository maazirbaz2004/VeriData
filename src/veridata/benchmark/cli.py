"""`veridata bench ...` commands (Phase 4, Section 9)."""

from __future__ import annotations

import argparse
import json
import logging
from typing import Any


def add_bench_parser(subparsers: Any) -> None:
    p = subparsers.add_parser("bench", help="Phase 4 planted-truth benchmark: gen, run, eval, calibrate, tune, truth-selfcheck")
    p.add_argument("action", choices=["gen", "run", "run-all-variants", "eval", "calibrate", "tune", "truth-selfcheck"])
    p.add_argument("--suite", default="core60", help="smoke | core60")
    p.add_argument("--split", default="dev", choices=["dev", "test"])
    p.add_argument("--system", default=None, help="one system (run)")
    p.add_argument("--systems", default=None, help="comma-separated systems (eval / run-all-variants)")
    p.add_argument("--n-jobs", type=int, default=2)
    p.add_argument("--no-cache", action="store_true")
    p.add_argument("--confirm-final", action="store_true", help="required for --split test (Phase 8 only)")
    p.add_argument("--experiment", default="all", choices=["type1", "fdr_dependence", "power", "all"])
    p.add_argument("--reps", type=int, default=None, help="replications for calibration experiments")
    p.add_argument("--resamples", type=int, default=2000, help="bootstrap resamples for eval")


def run_bench(args: argparse.Namespace) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    from veridata.benchmark import runner
    from veridata.benchmark.systems import DEFAULT_VARIANTS, tuning_variant_names

    systems = args.systems.split(",") if args.systems else None
    if args.action == "gen":
        dirs = runner.generate_suite(args.suite, args.split, n_jobs=args.n_jobs, confirm_final=args.confirm_final)
        print(f"{len(dirs)} datasets in {runner.split_dir(args.suite, args.split)}")
        return 0
    if args.action in {"run", "run-all-variants"}:
        if args.action == "run":
            chosen = [args.system or "veridata_full"]
        else:
            chosen = systems or (list(DEFAULT_VARIANTS) + (tuning_variant_names() if args.split == "dev" else []))
        res = runner.run_suite(args.suite, args.split, chosen, n_jobs=args.n_jobs, use_cache=not args.no_cache, confirm_final=args.confirm_final)
        print(json.dumps(res, indent=2))
        return 0
    if args.action == "eval":
        runner.evaluate_suite(args.suite, args.split, systems, n_resamples=args.resamples, confirm_final=args.confirm_final)
        print((runner.split_dir(args.suite, args.split) / "results" / "summary.md").read_text(encoding="utf-8"))
        return 0
    if args.action == "tune":
        from veridata.benchmark.tuning import tune

        r = tune(args.suite, args.split)
        print(f"chosen multiplier {r['chosen_multiplier']}: {r['reason']}")
        return 0
    if args.action == "truth-selfcheck":
        from veridata.benchmark.generator import truth_selfcheck
        from veridata.benchmark.suites import suite_specs

        bad = 0
        for spec in suite_specs(args.suite, "dev"):
            rep = truth_selfcheck(spec.scenario, spec.seed)
            bad += 0 if rep["ok"] else 1
            print(("OK  " if rep["ok"] else "FAIL"), spec.dataset_id, f"true={rep['n_true']} null={rep['n_null']} max_null={rep['max_null_measure']}")
        return 1 if bad else 0
    if args.action == "calibrate":
        from veridata.benchmark import calibration as cal

        t1 = cal.run_type1(args.reps or 1000, n_jobs=args.n_jobs) if args.experiment in {"type1", "all"} else None
        fd = cal.run_fdr_dependence(args.reps or 300, n_jobs=args.n_jobs) if args.experiment in {"fdr_dependence", "all"} else None
        pw = cal.run_power(args.reps or 400) if args.experiment in {"power", "all"} else None
        print(json.dumps(cal.write_outputs(t1, fd, pw), indent=2, default=str))
        return 0
    return 2
