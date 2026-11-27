"""AST-checked restricted Python subprocess sandbox for LLM code-mode baselines (Phase 8)."""

from __future__ import annotations

import ast
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

ALLOWED_IMPORT_ROOTS = {
    "pandas",
    "numpy",
    "scipy",
    "math",
    "statistics",
    "collections",
    "itertools",
    "json",
}

FORBIDDEN_NAMES = {
    "open",
    "exec",
    "eval",
    "compile",
    "__import__",
    "input",
    "breakpoint",
    "globals",
    "locals",
    "vars",
    "os",
    "sys",
    "subprocess",
    "pathlib",
    "shutil",
    "socket",
    "urllib",
    "requests",
    "httpx",
}

FORBIDDEN_ATTRS = {
    "__subclasses__",
    "__globals__",
    "__builtins__",
    "__code__",
    "__closure__",
    "system",
    "popen",
    "read_text",
    "write_text",
}


def validate_and_inspect_code(code: str) -> tuple[bool, str | None, list[str]]:
    """Validate AST safety and extract statistical calls (e.g., ttest_ind, pearsonr)."""
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return False, f"SyntaxError: {exc}", []

    tests_detected: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root not in ALLOWED_IMPORT_ROOTS:
                    return False, f"Disallowed import: {alias.name}", []
        elif isinstance(node, ast.ImportFrom):
            mod = (node.module or "").split(".")[0]
            if mod not in ALLOWED_IMPORT_ROOTS:
                return False, f"Disallowed import-from: {node.module}", []
        elif isinstance(node, ast.Name):
            if node.id in FORBIDDEN_NAMES:
                return False, f"Disallowed identifier: {node.id}", []
        elif isinstance(node, ast.Attribute):
            if node.attr in FORBIDDEN_ATTRS:
                return False, f"Disallowed attribute access: {node.attr}", []
            if node.attr in {
                "ttest_ind",
                "mannwhitneyu",
                "f_oneway",
                "kruskal",
                "pearsonr",
                "spearmanr",
                "chi2_contingency",
                "fisher_exact",
                "shapiro",
                "levene",
                "false_discovery_control",
            }:
                tests_detected.append(node.attr)

    return True, None, sorted(set(tests_detected))


def run_sandboxed_code(
    code: str,
    csv_path: Path | str,
    *,
    timeout_s: float = 15.0,
) -> dict[str, Any]:
    """Execute validated analysis code against ``df`` in an isolated subprocess."""
    ok, err, tests_detected = validate_and_inspect_code(code)
    if not ok:
        return {
            "ok": False,
            "stdout": "",
            "error": err,
            "runtime_ms": 0.0,
            "tests_detected": [],
        }

    csv_abs = str(Path(csv_path).resolve())
    with tempfile.TemporaryDirectory(prefix="vd_sandbox_") as tmpdir:
        runner_path = Path(tmpdir) / "run_snippet.py"
        user_code_path = Path(tmpdir) / "snippet.py"
        user_code_path.write_text(code, encoding="utf-8")

        harness = (
            "import json, math, statistics, collections, itertools\n"
            "import numpy as np\n"
            "import pandas as pd\n"
            "import scipy\n"
            "from scipy import stats\n"
            f"df = pd.read_csv({csv_abs!r})\n"
            f"_code = open({str(user_code_path)!r}, 'r', encoding='utf-8').read()\n"
            "_ns = {'df': df, 'pd': pd, 'np': np, 'scipy': scipy, 'stats': stats, "
            "'json': json, 'math': math, 'statistics': statistics}\n"
            "exec(compile(_code, '<sandbox>', 'exec'), _ns)\n"
        )
        runner_path.write_text(harness, encoding="utf-8")

        t0 = time.perf_counter()
        try:
            proc = subprocess.run(
                [sys.executable, "-I", str(runner_path)],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                timeout=timeout_s,
                check=False,
            )
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            stdout = proc.stdout[:12000]
            stderr = proc.stderr[:4000]
            if proc.returncode != 0:
                return {
                    "ok": False,
                    "stdout": stdout,
                    "error": stderr or f"Exited with code {proc.returncode}",
                    "runtime_ms": round(elapsed_ms, 2),
                    "tests_detected": tests_detected,
                }
            return {
                "ok": True,
                "stdout": stdout,
                "error": None,
                "runtime_ms": round(elapsed_ms, 2),
                "tests_detected": tests_detected,
            }
        except subprocess.TimeoutExpired:
            return {
                "ok": False,
                "stdout": "",
                "error": f"Sandbox execution timed out after {timeout_s}s.",
                "runtime_ms": round(timeout_s * 1000.0, 2),
                "tests_detected": tests_detected,
            }
