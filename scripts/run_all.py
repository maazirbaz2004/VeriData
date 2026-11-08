"""Script to run Phase 1 pipeline on all datasets in configs/datasets/ (Section 4, Section 14.2)."""

from __future__ import annotations

import sys

from ads.cli import main

if __name__ == "__main__":
    sys.exit(main(["run-all", *sys.argv[1:]]))

