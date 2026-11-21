"""Synthetic base and messy dataset generation package (Section 12)."""

from __future__ import annotations

from veridata.synthetic.base_generator import generate_base_truth_metadata, make_clean_base
from veridata.synthetic.messy_injector import (
    generate_and_save_messy_dataset,
    inject_problems,
)

__all__ = [
    "make_clean_base",
    "generate_base_truth_metadata",
    "inject_problems",
    "generate_and_save_messy_dataset",
]

