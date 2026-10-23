#!/usr/bin/env python3
"""Dataset Download and Environment Setup Script for PCB Defect Detection.

Designed for execution on the high-end training workstation.
DO NOT EXECUTE LOCALLY IF RUNNING ON LOW-END HARDWARE.

Usage:
    # 1. Using Kaggle API (requires ~/.kaggle/kaggle.json or KAGGLE_USERNAME / KAGGLE_KEY env vars):
    python dataset_setup.py --kaggle-dataset fedybenhassouna/printed-circuit-board-pcb-defects --dest-dir ./data

    # 2. If already downloaded as a zip file:
    python dataset_setup.py --zip-path /path/to/archive.zip --dest-dir ./data
"""

import argparse
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

CLASSES = [
    "mouse_bite",
    "spur",
    "missing_hole",
    "short",
    "open_circuit",
    "spurious_copper",
]


def download_kaggle(dataset_slug: str, target_dir: Path) -> Path:
    """Download dataset using Kaggle CLI."""
    print(f"[*] Downloading '{dataset_slug}' via Kaggle API...")
    target_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        "kaggle",
        "datasets",
        "download",
        "-d",
        dataset_slug,
        "-p",
        str(target_dir),
        "--unzip",
    ]
    try:
        subprocess.run(cmd, check=True)
        print("[+] Download and extraction complete.")
        return target_dir
    except (subprocess.CalledProcessError, FileNotFoundError) as err:
        print(f"[-] Kaggle CLI failed or not installed: {err}", file=sys.stderr)
        print(
            "[-] Ensure 'pip install kaggle' is run and ~/.kaggle/kaggle.json credentials exist.",
            file=sys.stderr,
        )
        sys.exit(1)


def extract_zip(zip_path: Path, target_dir: Path) -> Path:
    """Extract an existing local zip archive."""
    print(f"[*] Extracting {zip_path} -> {target_dir}...")
    target_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(target_dir)
    print("[+] Extraction complete.")
    return target_dir


def audit_extracted_structure(base_dir: Path):
    """Inspect dataset files, detect naming conventions, and check for board IDs."""
    print("\n" + "=" * 60)
    print("[*] AUDITING DATASET STRUCTURE & BOARD NAMING CONVENTION")
    print("=" * 60)

    image_extensions = {".jpg", ".jpeg", ".png", ".bmp"}
    images = [p for p in base_dir.rglob("*") if p.suffix.lower() in image_extensions]

    if not images:
        print(f"[-] No images found in {base_dir}!", file=sys.stderr)
        return

    print(f"[+] Total images discovered: {len(images)}")
    sample_names = [p.name for p in images[:10]]
    print("[+] Sample image filenames:")
    for name in sample_names:
        print(f"    - {name}")

    # Inspect labels
    label_files = list(base_dir.rglob("*.txt"))
    # Filter out split list files
    label_files = [p for p in label_files if p.name not in {"train.txt", "val.txt", "test.txt"}]
    print(f"[+] Total label annotation files found: {len(label_files)}")

    # Check for potential board ID prefixes (e.g., '01_', 'board_12_', etc.)
    import re
    match_board_id = sum(1 for p in images if re.search(r"^(\d+)_", p.stem))
    print(f"[+] Images matching numeric board prefix pattern r'^(\\d+)_': {match_board_id}/{len(images)}")

    return images


def create_yolo_yaml(dataset_dir: Path, out_path: Path):
    """Write standard YOLO data.yaml configuration."""
    content = f"""# PCB Defect Detection - Dataset Configuration
path: {dataset_dir.resolve().as_posix()}
train: train/images
val: val/images
test: test/images

names:
  0: mouse_bite
  1: spur
  2: missing_hole
  3: short
  4: open_circuit
  5: spurious_copper
"""
    out_path.write_text(content, encoding="utf-8")
    print(f"[+] Created YOLO dataset YAML at: {out_path.resolve()}")


def main():
    parser = argparse.ArgumentParser(description="PCB Dataset Download and Setup")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--kaggle-dataset",
        type=str,
        help="Kaggle dataset slug (e.g. fedybenhassouna/printed-circuit-board-pcb-defects)",
    )
    group.add_argument("--zip-path", type=Path, help="Path to pre-downloaded dataset zip")

    parser.add_argument(
        "--dest-dir",
        type=Path,
        default=Path("./dataset"),
        help="Target folder for dataset setup",
    )
    args = parser.parse_args()

    if args.kaggle_dataset:
        data_dir = download_kaggle(args.kaggle_dataset, args.dest_dir)
    else:
        data_dir = extract_zip(args.zip_path, args.dest_dir)

    audit_extracted_structure(data_dir)
    create_yolo_yaml(data_dir, data_dir / "pcb_data.yaml")
    print("\n[+] Setup script finished. Ready for leakage check and training.")


if __name__ == "__main__":
    main()
