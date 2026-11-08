"""Download and setup the 5 real benchmark datasets for Phase 1.

Supports:
1. Direct HTTP/HTTPS download and zip extraction (UCI & GitHub mirrors) - works out-of-the-box without API keys.
2. Optional Kaggle API download if kaggle credentials are configured.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

DATA_RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"

DATASET_SOURCES = {
    "insurance": {
        "dest_dir": DATA_RAW_DIR / "insurance",
        "dest_file": "insurance.csv",
        "primary_url": "https://raw.githubusercontent.com/stedy/Machine-Learning-with-R-datasets/master/insurance.csv",
        "kaggle_ref": "mirichoi0218/insurance",
        "description": "Medical Cost Personal Datasets (1,338 rows, 7 cols)",
    },
    "telco_churn": {
        "dest_dir": DATA_RAW_DIR / "telco_churn",
        "dest_file": "WA_Fn-UseC_-Telco-Customer-Churn.csv",
        "primary_url": "https://raw.githubusercontent.com/IBM/telco-customer-churn-on-icp4d/master/data/Telco-Customer-Churn.csv",
        "kaggle_ref": "blastchar/telco-customer-churn",
        "description": "Telco Customer Churn (7,043 rows, 21 cols)",
    },
    "heart_disease": {
        "dest_dir": DATA_RAW_DIR / "heart_disease",
        "dest_file": "heart.csv",
        "primary_url": "https://raw.githubusercontent.com/sharmaroshan/Heart-UCI-Dataset/master/heart.csv",
        "fallback_url": "https://archive.ics.uci.edu/static/public/45/heart+disease.zip",
        "kaggle_ref": "johnsmith88/heart-disease-dataset",
        "description": "Heart Disease UCI/Kaggle (303 rows, 14 cols)",
    },
    "student_performance": {
        "dest_dir": DATA_RAW_DIR / "student_performance",
        "dest_file": "student-mat.csv",
        "primary_url": "https://raw.githubusercontent.com/guipsamora/pandas_exercises/master/04_Apply/Students_Alcohol_Consumption/student-mat.csv",
        "fallback_url": "https://archive.ics.uci.edu/static/public/320/student+performance.zip",
        "description": "Student Performance (Math) UCI (395 rows, 33 cols, semicolon-delimited)",
    },
    "bank_marketing": {
        "dest_dir": DATA_RAW_DIR / "bank_marketing",
        "dest_file": "bank-additional-full.csv",
        "is_zip": True,
        "zip_target": "bank-additional/bank-additional-full.csv",
        "primary_url": "https://archive.ics.uci.edu/static/public/222/bank+marketing.zip",
        "nested_zip": "bank-additional.zip",
        "description": "Bank Marketing Full UCI (41,188 rows, 21 cols, semicolon-delimited)",
    },
}


def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def download_file_direct(url: str) -> bytes:
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) VeriData-Downloader/1.0"}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def download_dataset(name: str, force: bool = False) -> bool:
    info = DATASET_SOURCES.get(name)
    if not info:
        print(f"[-] Unknown dataset: '{name}'")
        return False

    dest_dir = Path(info["dest_dir"])
    dest_file = dest_dir / info["dest_file"]
    dest_dir.mkdir(parents=True, exist_ok=True)

    if dest_file.exists() and not force:
        print(f"[OK] '{name}' already present at: {dest_file} (SHA256: {compute_sha256(dest_file)[:12]}...)")
        return True

    print(f"\n[*] Downloading '{name}' ({info['description']})...")

    # Try direct URL download first
    primary_url = info.get("primary_url")
    is_zip = info.get("is_zip", False)

    if primary_url:
        try:
            print(f"    Fetching: {primary_url}")
            raw_bytes = download_file_direct(primary_url)

            if is_zip:
                with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zf:
                    if info.get("nested_zip"):
                        nested_name = info["nested_zip"]
                        nested_bytes = zf.read(nested_name)
                        with zipfile.ZipFile(io.BytesIO(nested_bytes)) as nested_zf:
                            content = nested_zf.read(info["zip_target"])
                    else:
                        content = zf.read(info["zip_target"])
                dest_file.write_bytes(content)
            else:
                dest_file.write_bytes(raw_bytes)

            sha = compute_sha256(dest_file)
            size_kb = dest_file.stat().st_size / 1024
            print(f"[+] Successfully saved {dest_file.name} ({size_kb:.1f} KB, SHA256: {sha})")
            return True
        except Exception as e:
            print(f"    Direct download failed: {e}")

    # Fallback to Kaggle API if available
    kaggle_ref = info.get("kaggle_ref")
    if kaggle_ref:
        print(f"    Trying Kaggle API download for '{kaggle_ref}'...")
        try:
            import kaggle
            kaggle.api.authenticate()
            kaggle.api.dataset_download_files(kaggle_ref, path=str(dest_dir), unzip=True)
            # Find matching csv
            matches = list(dest_dir.glob("*.csv"))
            if matches:
                # rename first match if needed
                if not dest_file.exists() and matches:
                    shutil.move(str(matches[0]), str(dest_file))
                if dest_file.exists():
                    print(f"[+] Downloaded from Kaggle: {dest_file.name}")
                    return True
        except Exception as ke:
            print(f"    Kaggle download failed or kaggle package/auth not configured: {ke}")

    print(f"[-] Could not automatically download '{name}'. Please download manually per scripts/download_datasets.md")
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Download real datasets for VeriData Phase 1.")
    parser.add_argument(
        "--datasets",
        nargs="+",
        default=list(DATASET_SOURCES.keys()),
        choices=list(DATASET_SOURCES.keys()) + ["partner1", "partner2", "all"],
        help="Datasets to download",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite existing files")
    args = parser.parse_args()

    targets = args.datasets
    if "all" in targets:
        targets = list(DATASET_SOURCES.keys())
    elif "partner1" in targets:
        targets = ["insurance", "telco_churn", "heart_disease"]
    elif "partner2" in targets:
        targets = ["student_performance", "bank_marketing"]

    success_count = 0
    for name in targets:
        if name in DATASET_SOURCES:
            if download_dataset(name, force=args.force):
                success_count += 1

    print(f"\nCompleted: {success_count}/{len(targets)} dataset(s) ready in {DATA_RAW_DIR}.")


if __name__ == "__main__":
    main()

