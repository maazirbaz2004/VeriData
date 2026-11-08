"""Command-Line Interface for VeriData Agentic Data Scientist (Section 14.2)."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Sequence

from ads.config import load_config
from ads.pipeline import run_phase1


def close_logging(logger: logging.Logger) -> None:
    """Close and remove all handlers on the logger (prevents Windows file locks)."""
    for handler in list(logger.handlers):
        handler.flush()
        handler.close()
        logger.removeHandler(handler)


def setup_logging(out_dir: Path | None = None) -> logging.Logger:
    """Configure INFO to console and DEBUG to outputs/<name>/run.log (Section 14.3)."""
    logger = logging.getLogger("ads")
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
    """Build the CLI parser supporting all Section 14.2 commands."""
    parser = argparse.ArgumentParser(
        prog="ads",
        description="VeriData Agentic Data Scientist — Phase 1 CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # ads run
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

    # ads run-all
    run_all_parser = subparsers.add_parser(
        "run-all", help="Run Phase 1 pipeline on all configured datasets"
    )
    run_all_parser.add_argument(
        "--configs-dir",
        default="configs/datasets",
        help="Directory containing per-dataset YAML configs",
    )

    # ads make-messy
    messy_parser = subparsers.add_parser(
        "make-messy", help="Generate messy synthetic dataset and ground-truth manifest"
    )
    messy_parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
    messy_parser.add_argument("--rows", type=int, default=2000, help="Number of base rows")

    # ads llm-baseline
    llm_parser = subparsers.add_parser("llm-baseline", help="Run LLM baseline comparison")
    llm_parser.add_argument(
        "--mode", choices=["a", "b", "both"], default="both", help="LLM baseline mode"
    )
    llm_parser.add_argument("--repeats", type=int, default=3, help="Number of repeats per run")
    llm_parser.add_argument("--force", action="store_true", help="Ignore cached LLM responses")

    # ads compare
    subparsers.add_parser("compare", help="Score pipeline vs LLM baseline and generate tables/plots")

    # ads report
    subparsers.add_parser("report", help="Assemble final_report/PHASE1_REPORT.md")

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
            from ads.synthetic.messy_injector import generate_and_save_messy_dataset

            paths = generate_and_save_messy_dataset(
                out_dir=Path("data/synthetic"),
                n_rows=args.rows,
                seed=args.seed,
            )
            logger.info("Generated messy synthetic dataset -> %s", paths["messy_csv"])
            return 0
        finally:
            close_logging(logger)

    logger = setup_logging()
    try:
        logger.info("Command '%s' registered (Partner 2 comparison/report module).", args.command)
        return 0
    finally:
        close_logging(logger)


def app() -> None:
    """Console script entrypoint."""
    sys.exit(main())


if __name__ == "__main__":
    app()
