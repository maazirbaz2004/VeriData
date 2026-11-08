"""Robust CSV ingestion module (Section 7.1)."""

from __future__ import annotations

import csv
import hashlib
import io
import logging
from pathlib import Path

import pandas as pd

from ads.config import PipelineConfig, load_config
from ads.schemas import IngestionMetadata, IngestionResult

logger = logging.getLogger("ads.ingestion")


def compute_sha256(path: Path) -> str:
    """Compute SHA-256 hex digest of a file."""
    hasher = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def detect_encoding(
    raw_bytes: bytes, encodings_to_try: list[str]
) -> tuple[str, str, bool]:
    """Detect encoding of raw bytes by trying configured encodings in order.

    Returns:
        (decoded_text, encoding_used, fallback_used)
    """
    # If UTF-8 BOM is present, prefer utf-8-sig so BOM is stripped cleanly
    if raw_bytes.startswith(b"\xef\xbb\xbf") and "utf-8-sig" in encodings_to_try:
        try:
            return raw_bytes.decode("utf-8-sig"), "utf-8-sig", False
        except UnicodeDecodeError:
            pass

    primary_encodings = {"utf-8", "utf-8-sig"}
    for enc in encodings_to_try:
        try:
            text = raw_bytes.decode(enc)
            fallback_used = enc.lower() not in primary_encodings
            return text, enc, fallback_used
        except UnicodeDecodeError:
            continue

    # Ultimate fallback with replacement if all configured encodings fail
    text = raw_bytes.decode("latin-1", errors="replace")
    return text, "latin-1", True


def detect_delimiter(sample_text: str, candidate_delimiters: list[str]) -> str:
    """Detect delimiter using csv.Sniffer with frequency heuristic fallback."""
    lines = [line for line in sample_text.splitlines() if line.strip()][:25]
    if not lines:
        return ","

    sample = "\n".join(lines)
    delims_str = "".join(candidate_delimiters)

    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=delims_str)
        if dialect.delimiter in candidate_delimiters:
            return dialect.delimiter
    except csv.Error:
        pass

    # Fallback heuristic: pick delimiter that appears consistently across sample lines
    best_delim = ","
    best_score = 0.0
    for delim in candidate_delimiters:
        counts = [line.count(delim) for line in lines]
        if counts and min(counts) > 0:
            # Prefer consistent non-zero count per line
            consistency = sum(1 for c in counts if c == counts[0]) / len(counts)
            score = consistency * counts[0]
            if score > best_score:
                best_score = score
                best_delim = delim

    return best_delim


def _normalize_headers(
    raw_headers: list[str],
) -> tuple[list[str], dict[str, str], list[str]]:
    """Strip BOM/whitespace, name empty columns unnamed_<i>, and suffix duplicates (.1, .2).

    Returns:
        (normalized_headers, column_name_changes, warnings)
    """
    normalized: list[str] = []
    name_changes: dict[str, str] = {}
    warnings: list[str] = []
    seen_counts: dict[str, int] = {}

    for idx, raw_name in enumerate(raw_headers):
        cleaned = raw_name.replace("\ufeff", "").strip()

        if cleaned == "":
            cleaned = f"unnamed_{idx}"
            msg = f"Empty column header at index {idx} renamed to '{cleaned}'."
            warnings.append(msg)
            name_changes[f"<empty_{idx}>"] = cleaned
        elif cleaned != raw_name:
            msg = f"Column header whitespace/BOM stripped: {raw_name!r} -> {cleaned!r}."
            warnings.append(msg)
            name_changes[raw_name] = cleaned

        if cleaned in seen_counts:
            seen_counts[cleaned] += 1
            suffixed = f"{cleaned}.{seen_counts[cleaned]}"
            msg = f"Duplicate column header {cleaned!r} at index {idx} renamed to {suffixed!r}."
            warnings.append(msg)
            name_changes[f"{raw_name} (col {idx})"] = suffixed
            normalized.append(suffixed)
        else:
            seen_counts[cleaned] = 0
            normalized.append(cleaned)

        if cleaned.lower().startswith("unnamed:"):
            warnings.append(
                f"Column {cleaned!r} matches exported index pattern ('Unnamed: ...')."
            )

    return normalized, name_changes, warnings


def load_csv(
    path: Path | str,
    config: PipelineConfig | None = None,
) -> IngestionResult:
    """Robustly load a CSV file as raw strings plus a naive pandas parse (Section 7.1)."""
    cfg = config or load_config()
    file_path = Path(path)

    if not file_path.exists():
        raise FileNotFoundError(
            f"Input CSV file not found: '{file_path}'. "
            "Please verify the path or download the dataset per scripts/download_datasets.md."
        )
    if not file_path.is_file():
        raise ValueError(f"Input path is not a regular file: '{file_path}'.")

    file_size_bytes = file_path.stat().st_size
    file_size_mb = file_size_bytes / (1024 * 1024)
    max_mb = cfg.ingestion.max_file_size_mb
    if file_size_mb > max_mb:
        raise ValueError(
            f"File '{file_path}' is {file_size_mb:.2f} MB, exceeding max_file_size_mb={max_mb:.2f} MB."
        )
    if file_size_bytes == 0:
        raise ValueError(f"Input CSV file is empty (0 bytes): '{file_path}'.")

    sha256 = compute_sha256(file_path)
    raw_bytes = file_path.read_bytes()

    text, encoding_used, fallback_used = detect_encoding(
        raw_bytes, cfg.ingestion.encodings_to_try
    )
    # Normalize CRLF / CR line endings for cross-platform determinism
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if not text.strip():
        raise ValueError(f"Input CSV file contains only whitespace: '{file_path}'.")

    warnings: list[str] = []
    if fallback_used:
        msg = f"Non-UTF-8 encoding fallback '{encoding_used}' used for '{file_path.name}'."
        warnings.append(msg)
        logger.warning(msg)

    sample_text = text[:65536]
    delimiter = detect_delimiter(sample_text, cfg.ingestion.delimiters_to_try)

    # Parse rows with C-backed csv.reader to deterministically handle quoted newlines,
    # trailing delimiters, and ragged rows without silent truncation.
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    try:
        raw_headers = next(reader)
    except StopIteration as exc:
        raise ValueError(f"Input CSV file has no header row: '{file_path}'.") from exc

    normalized_headers, name_changes, header_warnings = _normalize_headers(raw_headers)
    warnings.extend(header_warnings)
    for w in header_warnings:
        logger.warning(w)

    n_cols_expected = len(normalized_headers)
    valid_rows: list[list[str]] = []
    n_bad_lines = 0

    for row in reader:
        if len(row) == 0:
            # Blank trailing line
            continue
        if len(row) == n_cols_expected:
            valid_rows.append(row)
        elif len(row) == n_cols_expected + 1 and row[-1].strip() == "":
            # Trailing delimiter at end of line
            valid_rows.append(row[:n_cols_expected])
        else:
            # Ragged / malformed row (too many or too few fields)
            n_bad_lines += 1

    if n_bad_lines > 0:
        msg = f"Skipped {n_bad_lines} malformed/ragged row(s) while loading '{file_path.name}'."
        warnings.append(msg)
        logger.warning(msg)

    # 1. Build df_raw_str (all strings, zero silent NA/type coercion)
    df_raw_str = pd.DataFrame(valid_rows, columns=normalized_headers, dtype=str)

    # 2. Build df_naive (pandas default type inference on the valid rows, used to record raw_dtype)
    if valid_rows:
        buf = io.StringIO()
        writer = csv.writer(buf, delimiter=",")
        writer.writerow(normalized_headers)
        writer.writerows(valid_rows)
        buf.seek(0)
        df_naive = pd.read_csv(buf, keep_default_na=True)
    else:
        df_naive = pd.DataFrame(columns=normalized_headers)

    metadata = IngestionMetadata(
        source_file=str(file_path),
        sha256=sha256,
        file_size_mb=round(file_size_mb, 6),
        encoding=encoding_used,
        encoding_fallback_used=fallback_used,
        delimiter=delimiter,
        n_bad_lines=n_bad_lines,
        n_rows=int(len(df_raw_str)),
        n_cols=int(len(df_raw_str.columns)),
        column_name_changes=name_changes,
        warnings=warnings,
    )

    logger.info(
        "Loaded '%s': %d rows x %d cols (encoding=%s, delimiter=%r, bad_lines=%d)",
        file_path.name,
        metadata.n_rows,
        metadata.n_cols,
        metadata.encoding,
        metadata.delimiter,
        metadata.n_bad_lines,
    )

    return IngestionResult(
        df_raw_str=df_raw_str,
        df_naive=df_naive,
        metadata=metadata,
    )
