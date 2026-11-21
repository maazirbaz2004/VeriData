"""Command-Line Interface for VeriData Agentic Data Scientist."""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import Sequence

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

    # veridata report
    subparsers.add_parser("report", help="Assemble final_report/PHASE1_REPORT.md")

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
