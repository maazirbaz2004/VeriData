"""Command-Line Interface for VeriData Agentic Data Scientist."""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

import pandas as pd

from veridata.config import load_config
from veridata.pipeline import run_phase1


def close_logging(logger: logging.Logger) -> None:
    """Close and remove all handlers on the logger (prevents Windows file locks)."""
    for handler in list(logger.handlers):
        handler.flush()
        handler.close()
        logger.removeHandler(handler)


def setup_logging(out_dir: Path | None = None) -> logging.Logger:
    """Configure INFO to console and DEBUG to outputs/<name>/run.log."""
    logger = logging.getLogger("veridata")
    logger.setLevel(logging.DEBUG)
    close_logging(logger)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_fmt = logging.Formatter("[%(levelname)s] %(name)s: %(message)s")
    console_handler.setFormatter(console_fmt)
    logger.addHandler(console_handler)

    if out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(out_dir / "run.log", encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_fmt = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d): %(message)s"
        )
        file_handler.setFormatter(file_fmt)
        logger.addHandler(file_handler)

    return logger


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser supporting Phase 1 and Phase 2 commands."""
    parser = argparse.ArgumentParser(
        prog="veridata",
        description="VeriData Agentic Data Scientist CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # veridata run
    run_parser = subparsers.add_parser("run", help="Run Phase 1 pipeline on a single CSV")
    run_parser.add_argument("--input", required=True, help="Path to input CSV file")
    run_parser.add_argument("--name", required=True, help="Dataset identifier name")
    run_parser.add_argument("--target", default=None, help="Optional target column")
    run_parser.add_argument("--no-llm", action="store_true", help="Disable LLM (fully offline/deterministic)")
    run_parser.add_argument("--force", action="store_true", help="Force re-computation")
    run_parser.add_argument("--use-graph", action="store_true", help="Run via LangGraph batch graph")
    run_parser.add_argument("--config", default=None, help="Optional dataset YAML config path")
    run_parser.add_argument("--out", default=None, help="Output directory (default: outputs/<name>)")
    run_parser.add_argument(
        "--cleaned-dir",
        default="data/cleaned",
        help="Directory for cleaned CSV outputs (default: data/cleaned)",
    )

    # veridata run-all
    run_all_parser = subparsers.add_parser(
        "run-all", help="Run Phase 1 pipeline on all configured datasets"
    )
    run_all_parser.add_argument(
        "--configs-dir",
        default="configs/datasets",
        help="Directory containing per-dataset YAML configs",
    )

    # veridata make-messy
    messy_parser = subparsers.add_parser(
        "make-messy", help="Generate messy synthetic dataset and ground-truth manifest"
    )
    messy_parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
    messy_parser.add_argument("--rows", type=int, default=2000, help="Number of base rows")

    # veridata llm-baseline
    llm_parser = subparsers.add_parser("llm-baseline", help="Run LLM baseline comparison")
    llm_parser.add_argument(
        "--mode", choices=["a", "b", "both"], default="both", help="LLM baseline mode"
    )
    llm_parser.add_argument("--repeats", type=int, default=3, help="Number of repeats per run")
    llm_parser.add_argument("--force", action="store_true", help="Ignore cached LLM responses")

    # veridata compare
    subparsers.add_parser("compare", help="Score pipeline vs LLM baseline and generate tables/plots")

    # veridata report  (no --dataset: Phase 1 final report; --dataset: Phase 5 findings report)
    rep_parser = subparsers.add_parser(
        "report", help="Phase 5 findings report for --dataset (or, without it, assemble final_report/PHASE1_REPORT.md)"
    )
    rep_parser.add_argument("--dataset", default=None, help="Dataset name (needs outputs/<dataset>/findings.json)")
    rep_parser.add_argument("--narration", choices=["llm_slots", "template_only"], default="template_only")
    rep_parser.add_argument("--max-findings", type=int, default=None)
    rep_parser.add_argument("--format", default="md,html", help="Comma-separated: md,html")
    rep_parser.add_argument("--date", default="", help="Date shown in the title block (YYYY-MM-DD)")
    rep_parser.add_argument("--allow-violations", action="store_true", help="Debug: write the report even if the gate fails")
    rep_parser.add_argument("--out", default=None, help="Output folder (default: outputs/<dataset>/report)")

    # veridata verify-text (Phase 5 debugging tool)
    vt_parser = subparsers.add_parser("verify-text", help="Check the numbers in a text against a facts.json file")
    vt_parser.add_argument("--facts", required=True, help="JSON list of Fact objects (key, value, display, unit, source)")
    vt_parser.add_argument("--text", required=True)

    # veridata hypotheses (Phase 2)
    hyp_parser = subparsers.add_parser(
        "hypotheses", help="Generate Phase 2 testable hypotheses and family manifest"
    )
    hyp_parser.add_argument("--dataset", required=True, help="Dataset identifier name")
    hyp_parser.add_argument(
        "--mode",
        choices=["exhaustive", "target_focused", "llm_prioritized"],
        default=None,
        help="Hypothesis generation mode",
    )
    hyp_parser.add_argument("--target", default=None, help="Optional target column override")
    hyp_parser.add_argument(
        "--no-llm", action="store_true", help="Disable LLM proposals (strictly offline)"
    )
    hyp_parser.add_argument(
        "--out", default=None, help="Output directory (default: outputs/<dataset>)"
    )

    # veridata parse-hypothesis (Phase 2)
    parse_parser = subparsers.add_parser(
        "parse-hypothesis", help="Parse a natural-language question into a structured Hypothesis"
    )
    parse_parser.add_argument("--dataset", required=True, help="Dataset identifier name")
    parse_parser.add_argument("--text", required=True, help="Natural-language hypothesis text")
    parse_parser.add_argument(
        "--no-llm", action="store_true", help="Use offline fuzzy fallback only"
    )

    # veridata test (Phase 3)
    test_parser = subparsers.add_parser(
        "test", help="Run Phase 3 statistical testing and validation on Phase 2 hypotheses"
    )
    test_parser.add_argument("--dataset", required=True, help="Dataset identifier name")
    test_parser.add_argument("--alpha", type=float, default=None, help="FDR/FWER alpha level")
    test_parser.add_argument(
        "--correction",
        choices=["bh", "by", "holm", "bonferroni", "none"],
        default=None,
        help="Multiple-testing correction method",
    )
    test_parser.add_argument(
        "--no-effect-floor",
        action="store_true",
        help="Disable standardized effect-size floor (ablation)",
    )
    test_parser.add_argument(
        "--no-assumption-selection",
        action="store_true",
        help="Disable assumption-aware test selection (ablation)",
    )
    test_parser.add_argument(
        "--no-stage-b", action="store_true", help="Skip Stage B bootstrap CIs and sensitivity checks"
    )
    test_parser.add_argument(
        "--n-jobs", type=int, default=-1, help="Parallel worker count (-1 = all cores, 1 = serial)"
    )
    test_parser.add_argument(
        "--out", default=None, help="Output directory (default: outputs/<dataset>)"
    )

    # veridata validate (Phase 3)
    val_parser = subparsers.add_parser(
        "validate", help="Re-run Phase 3 validation over an existing ledger.jsonl"
    )
    val_parser.add_argument("--dataset", required=True, help="Dataset identifier name")
    val_parser.add_argument("--alpha", type=float, default=None, help="Override alpha level")
    val_parser.add_argument(
        "--correction",
        choices=["bh", "by", "holm", "bonferroni", "none"],
        default=None,
        help="Override correction method",
    )
    val_parser.add_argument(
        "--no-effect-floor", action="store_true", help="Disable effect-size floor"
    )

    # veridata chat (Phase 6)
    chat_parser = subparsers.add_parser(
        "chat", help="Start an interactive chat session with a dataset (Phase 6)"
    )
    chat_parser.add_argument("--dataset", required=True, help="Dataset identifier name")
    chat_parser.add_argument("--input", default=None, help="Optional path to input CSV file")
    chat_parser.add_argument("--no-llm", action="store_true", help="Run offline without LLM")

    # veridata bench ... (Phase 4)
    from veridata.benchmark.cli import add_bench_parser

    add_bench_parser(subparsers)

    # veridata eval ... (Phase 8)
    eval_parser = subparsers.add_parser(
        "eval", help="Phase 8 evaluation: plan, run, tables, figures, freeze"
    )
    eval_parser.add_argument(
        "action", choices=["plan", "run", "tables", "figures", "freeze"]
    )
    eval_parser.add_argument("--experiment", default="all", help="all | e1..e8 (comma-separated)")
    eval_parser.add_argument("--suite", default="core60", help="smoke | core60")
    eval_parser.add_argument("--split", default="dev", choices=["dev", "test"])
    eval_parser.add_argument("--n-jobs", type=int, default=2)
    eval_parser.add_argument("--confirm-final", action="store_true")
    eval_parser.add_argument("--no-llm", action="store_true", help="Skip LLM baselines completely")
    eval_parser.add_argument(
        "--skip-unavailable-llm",
        action="store_true",
        default=True,
        help="Skip LLM baselines gracefully when API key is missing",
    )
    eval_parser.add_argument(
        "--require-llm",
        action="store_true",
        help="Fail instead of skipping if no LLM API key is configured",
    )

    # veridata final-report (Phase 8)
    fr_parser = subparsers.add_parser(
        "final-report", help="Assemble final_report/FINAL_REPORT.md and HTML from cached Phase 8 outputs"
    )
    fr_parser.add_argument("--suite", default="core60", help="smoke | core60")
    fr_parser.add_argument("--split", default="dev", choices=["dev", "test"])

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Entrypoint for the CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        out_dir = Path(args.out) if args.out else Path("outputs") / args.name
        logger = setup_logging(out_dir)
        try:
            auto_cfg_path = Path("configs/datasets") / f"{args.name}.yaml"
            cfg_path = args.config or (auto_cfg_path if auto_cfg_path.exists() else None)
            cfg = load_config(
                dataset_config_path=cfg_path,
                cli_overrides={"name": args.name, "file": args.input},
            )
            if getattr(args, "use_graph", False):
                from veridata.agent.session import create_session
                df = pd.read_csv(args.input)
                sess = create_session(df, cfg, out_dir=out_dir)
                b_res = sess.run_batch(progress_callback=lambda m: logger.info(m))
                return 0 if b_res.get("status") == "done" else 1

            run_phase1(
                input_csv=args.input,
                dataset_name=args.name,
                out_dir=out_dir,
                config=cfg,
                cleaned_dir=Path(args.cleaned_dir),
            )
            return 0
        finally:
            close_logging(logger)

    if args.command == "run-all":
        logger = setup_logging()
        try:
            configs_dir = Path(args.configs_dir)
            yaml_files = sorted(configs_dir.glob("*.yaml"))
            for yf in yaml_files:
                cfg = load_config(dataset_config_path=yf)
                if not cfg.file:
                    continue
                input_path = Path(cfg.file)
                if not input_path.exists():
                    logger.warning(
                        "Skipping dataset '%s': raw file not found at '%s'.",
                        cfg.name,
                        input_path,
                    )
                    continue
                ds_out = Path("outputs") / cfg.name
                run_phase1(
                    input_csv=input_path,
                    dataset_name=cfg.name,
                    out_dir=ds_out,
                    config=cfg,
                )
            return 0
        finally:
            close_logging(logger)

    if args.command == "make-messy":
        logger = setup_logging()
        try:
            from veridata.synthetic.messy_injector import generate_and_save_messy_dataset

            paths = generate_and_save_messy_dataset(
                out_dir=Path("data/synthetic"),
                n_rows=args.rows,
                seed=args.seed,
            )
            logger.info("Generated messy synthetic dataset -> %s", paths["messy_csv"])
            return 0
        finally:
            close_logging(logger)

    if args.command == "report" and args.dataset:
        from veridata.reporting.cli import run_findings_report

        return run_findings_report(args)

    if args.command == "verify-text":
        from veridata.reporting.cli import run_verify_text

        return run_verify_text(args)

    if args.command == "report":
        logger = setup_logging()
        try:
            script_path = Path("scripts/build_report.py")
            if script_path.exists():
                res = subprocess.run([sys.executable, str(script_path)], check=False)
                return res.returncode
            logger.info("Command 'report' registered.")
            return 0
        finally:
            close_logging(logger)

    if args.command == "hypotheses":
        from veridata.agent.llm import get_llm_client
        from veridata.hypotheses import generate_hypotheses, save_hypothesis_outputs
        from veridata.schemas import ColumnSchemaEntry, DataProfile

        ds = args.dataset
        out_dir = Path(args.out) if args.out else Path("outputs") / ds
        logger = setup_logging(out_dir)
        try:
            auto_cfg = Path("configs/datasets") / f"{ds}.yaml"
            cfg = load_config(dataset_config_path=auto_cfg if auto_cfg.exists() else None)
            cleaned_csv = Path("data/cleaned") / f"{ds}_cleaned.csv"
            schema_path = Path("outputs") / ds / "column_schema.json"
            profile_path = Path("outputs") / ds / "profile_cleaned.json"
            if not profile_path.exists():
                profile_path = Path("outputs") / ds / "profile.json"

            if not cleaned_csv.exists() or not schema_path.exists():
                logger.error(
                    "Phase 1 artifacts not found for '%s' (expected %s and %s). Run Phase 1 first.",
                    ds,
                    cleaned_csv,
                    schema_path,
                )
                return 1

            df = pd.read_csv(cleaned_csv)
            raw_schema = json.loads(schema_path.read_text(encoding="utf-8"))
            schema = {k: ColumnSchemaEntry.model_validate(v) for k, v in raw_schema.items()}
            profile = (
                DataProfile.model_validate(json.loads(profile_path.read_text(encoding="utf-8")))
                if profile_path.exists()
                else None
            )

            llm = (
                None
                if args.no_llm
                else get_llm_client(cfg.llm, log_path=out_dir / "llm_calls.jsonl")
            )
            hset = generate_hypotheses(
                df=df,
                schema=schema,
                profile=profile,
                config=cfg,
                llm=llm,
                target=args.target,
                mode=args.mode,
                dataset_name=ds,
            )
            paths = save_hypothesis_outputs(hset, out_dir)
            logger.info(
                "Generated %d feasible hypotheses (%d infeasible, %d pruned) -> %s",
                hset.manifest.n_in_family_planned,
                hset.manifest.n_infeasible,
                hset.manifest.n_pruned,
                paths["hypotheses_json"],
            )
            return 0
        finally:
            close_logging(logger)

    if args.command == "parse-hypothesis":
        from veridata.agent.llm import get_llm_client
        from veridata.hypotheses import parse_nl_hypothesis
        from veridata.schemas import ColumnSchemaEntry, DataProfile

        ds = args.dataset
        logger = setup_logging()
        try:
            auto_cfg = Path("configs/datasets") / f"{ds}.yaml"
            cfg = load_config(dataset_config_path=auto_cfg if auto_cfg.exists() else None)
            cleaned_csv = Path("data/cleaned") / f"{ds}_cleaned.csv"
            schema_path = Path("outputs") / ds / "column_schema.json"
            profile_path = Path("outputs") / ds / "profile_cleaned.json"
            if not cleaned_csv.exists() or not schema_path.exists():
                logger.error("Phase 1 artifacts not found for '%s'.", ds)
                return 1

            df = pd.read_csv(cleaned_csv)
            raw_schema = json.loads(schema_path.read_text(encoding="utf-8"))
            schema = {k: ColumnSchemaEntry.model_validate(v) for k, v in raw_schema.items()}
            profile = (
                DataProfile.model_validate(json.loads(profile_path.read_text(encoding="utf-8")))
                if profile_path.exists()
                else None
            )
            llm = None if args.no_llm else get_llm_client(cfg.llm)
            outcome = parse_nl_hypothesis(
                text=args.text,
                df=df,
                schema=schema,
                llm=llm,
                config=cfg,
                profile=profile,
            )
            sys.stdout.write(json.dumps(outcome.model_dump(mode="json"), indent=2) + "\n")
            return 0
        finally:
            close_logging(logger)

    if args.command == "test":
        from veridata.contracts.hypothesis import Hypothesis, HypothesisManifest, HypothesisSet
        from veridata.stats.runner import run_all

        ds = args.dataset
        out_dir = Path(args.out) if args.out else Path("outputs") / ds
        logger = setup_logging(out_dir)
        try:
            auto_cfg = Path("configs/datasets") / f"{ds}.yaml"
            cfg = load_config(dataset_config_path=auto_cfg if auto_cfg.exists() else None)
            if args.alpha is not None:
                cfg.stats.alpha = args.alpha
            if args.correction is not None:
                cfg.stats.correction = args.correction
            if args.no_effect_floor:
                cfg.effect_floor.enabled = False
            if args.no_assumption_selection:
                cfg.stats.assumption_aware_selection = False

            cleaned_csv = Path("data/cleaned") / f"{ds}_cleaned.csv"
            hyps_path = Path("outputs") / ds / "hypotheses.json"
            manifest_path = Path("outputs") / ds / "hypothesis_manifest.json"
            profile_path = Path("outputs") / ds / "profile.json"

            if not cleaned_csv.exists() or not hyps_path.exists() or not manifest_path.exists():
                logger.error(
                    "Missing Phase 1/2 artifacts for '%s'. Run `veridata hypotheses --dataset %s` first.",
                    ds,
                    ds,
                )
                return 1

            df = pd.read_csv(cleaned_csv)
            hyps = [
                Hypothesis.model_validate(item)
                for item in json.loads(hyps_path.read_text(encoding="utf-8"))
            ]
            manifest = HypothesisManifest.model_validate(
                json.loads(manifest_path.read_text(encoding="utf-8"))
            )
            sha256 = ""
            if profile_path.exists():
                sha256 = str(json.loads(profile_path.read_text(encoding="utf-8")).get("sha256", ""))

            hset = HypothesisSet(hypotheses=hyps, manifest=manifest)
            run_out = run_all(
                hset,
                df,
                cfg,
                n_jobs=args.n_jobs,
                stage_b=not args.no_stage_b,
                out_dir=out_dir,
                dataset_sha256=sha256,
            )
            logger.info(
                "Tested m=%d hypotheses for '%s': %d raw sig -> %d BH sig -> %d accepted (%.2fs)",
                run_out.summary["m_tested"],
                ds,
                run_out.summary["n_raw_sig"],
                run_out.summary["n_bh_sig"],
                run_out.summary["n_accepted"],
                run_out.summary["runtime_seconds"],
            )
            return 0
        finally:
            close_logging(logger)

    if args.command == "validate":
        from veridata.contracts.hypothesis import Hypothesis
        from veridata.validation.ledger import SessionLedger
        from veridata.validation.validator import build_findings

        ds = args.dataset
        out_dir = Path("outputs") / ds
        logger = setup_logging(out_dir)
        try:
            auto_cfg = Path("configs/datasets") / f"{ds}.yaml"
            cfg = load_config(dataset_config_path=auto_cfg if auto_cfg.exists() else None)
            if args.alpha is not None:
                cfg.stats.alpha = args.alpha
            if args.correction is not None:
                cfg.stats.correction = args.correction
            if args.no_effect_floor:
                cfg.effect_floor.enabled = False

            ledger_path = out_dir / "ledger.jsonl"
            hyps_path = out_dir / "hypotheses.json"
            if not ledger_path.exists() or not hyps_path.exists():
                logger.error("Ledger or hypotheses not found for '%s'. Run `veridata test` first.", ds)
                return 1

            hyps = {
                h.id: h
                for h in (
                    Hypothesis.model_validate(x)
                    for x in json.loads(hyps_path.read_text(encoding="utf-8"))
                )
            }
            ledger = SessionLedger.load_jsonl(ledger_path)
            decisions, _ = ledger.revalidate(hyps, cfg, family_id="session")
            results = [e.test for e in ledger.entries]
            findings = build_findings(hyps, results, decisions)

            (out_dir / "decisions.json").write_text(
                json.dumps([d.model_dump(mode="json") for d in decisions], indent=2, sort_keys=True)
                + "\n",
                encoding="utf-8",
            )
            (out_dir / "findings.json").write_text(
                json.dumps([f.model_dump(mode="json") for f in findings], indent=2, sort_keys=True)
                + "\n",
                encoding="utf-8",
            )
            n_acc = sum(1 for d in decisions if d.accepted)
            logger.info(
                "Revalidated %d ledger entries for '%s' (%s, alpha=%.3f): %d accepted.",
                len(decisions),
                ds,
                cfg.stats.correction,
                cfg.stats.alpha,
                n_acc,
            )
            return 0
        finally:
            close_logging(logger)

    if args.command == "chat":
        logger = setup_logging()
        try:
            auto_cfg_path = Path("configs/datasets") / f"{args.dataset}.yaml"
            cfg = load_config(dataset_config_path=auto_cfg_path if auto_cfg_path.exists() else None)
            input_file = args.input or cfg.file
            if not input_file or not Path(input_file).exists():
                logger.error("Dataset CSV file not found.")
                return 1
            df = pd.read_csv(input_file)
            from veridata.agent.session import create_session
            sess = create_session(df, cfg)
            print(f"=== VeriData Chat: {args.dataset} (type 'exit' to quit) ===")
            while True:
                try:
                    q = input("\nUser: ").strip()
                    if not q or q.lower() in ("exit", "quit"):
                        break
                    ans = sess.ask(q)
                    print(f"Assistant: {ans.text}")
                    if ans.followups:
                        print("Suggestions:", [f["label"] for f in ans.followups])
                except (EOFError, KeyboardInterrupt):
                    break
            return 0
        finally:
            close_logging(logger)

    if args.command == "bench":
        from veridata.benchmark.cli import run_bench

        return run_bench(args)

    if args.command == "eval":
        from veridata.evaluation.figures import generate_all_figures
        from veridata.evaluation.run_all import (
            freeze_eval_protocol,
            plan_evaluation,
            run_evaluation,
        )
        from veridata.evaluation.tables import generate_all_tables

        logger = setup_logging()
        try:
            if args.action == "plan":
                plan = plan_evaluation(
                    suite=args.suite,
                    split=args.split,
                    experiment=args.experiment,
                    confirm_final=args.confirm_final,
                )
                print(json.dumps(plan, indent=2))
                return 0
            if args.action == "freeze":
                changed = freeze_eval_protocol()
                print("Protocol frozen." if changed else "Protocol already frozen.")
                return 0
            if args.action == "tables":
                res = generate_all_tables(suite=args.suite, split=args.split)
                print(json.dumps({k: str(v) for k, v in res.items()}, indent=2))
                return 0
            if args.action == "figures":
                res = generate_all_figures(suite=args.suite, split=args.split)
                print(json.dumps({k: str(v) for k, v in res.items()}, indent=2))
                return 0
            if args.action == "run":
                out = run_evaluation(
                    experiment=args.experiment,
                    suite=args.suite,
                    split=args.split,
                    n_jobs=args.n_jobs,
                    confirm_final=args.confirm_final,
                    skip_unavailable_llm=not args.require_llm,
                    with_llm=not args.no_llm,
                )
                print(json.dumps(out, indent=2))
                return 0
            return 2
        finally:
            close_logging(logger)

    if args.command == "final-report":
        from veridata.evaluation.final_report import build_final_report

        logger = setup_logging()
        try:
            paths = build_final_report(suite=args.suite, split=args.split)
            print(json.dumps({k: str(v) for k, v in paths.items()}, indent=2))
            return 0
        finally:
            close_logging(logger)

    logger = setup_logging()
    try:
        logger.info("Command '%s' registered.", args.command)
        return 0
    finally:
        close_logging(logger)


def app() -> None:
    """Console script entrypoint."""
    sys.exit(main())


if __name__ == "__main__":
    app()
