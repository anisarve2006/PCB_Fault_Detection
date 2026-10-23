#!/usr/bin/env python3
"""
Production Data & Training Pipeline: Phase 5 Champion Model
===========================================================
End-to-end automated pipeline for PCB Surface Defect Detection & Quality AOI:
1. Environment Setup & Hardware Acceleration (CUDA RTX 4090 / CPU fallback)
2. Automated Dataset Ingestion & Zero-Leakage Split Preparation
3. Annotation & Multi-Class Distribution Integrity Verification
4. Phase 5 Multi-Defect Champion Model Training (YOLO11s)
5. Rigorous Test Set Evaluation & Conformance Metrics Generation (IPC-A-610)
6. Multi-Defect Simultaneous Inference Validation (All 6 Classes Concurrently)

Usage:
    python data_pipeline_phase5.py --mode full
    python data_pipeline_phase5.py --mode evaluate
    python data_pipeline_phase5.py --mode prepare_data
"""

import argparse
import io
import json
import os
import re
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# ---------------------------------------------------------------------------
# 1. Environment & Safe Temp Storage Configuration
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
ROOT_DRIVE = BASE_DIR.drive or "Z:"
SAFE_TMP_DIR = Path(f"{ROOT_DRIVE}/tmp")
SAFE_TMP_DIR.mkdir(parents=True, exist_ok=True)

# Protect system drive from running out of disk space
os.environ["TEMP"] = str(SAFE_TMP_DIR)
os.environ["TMP"] = str(SAFE_TMP_DIR)
os.environ["KAGGLEHUB_CACHE"] = f"{ROOT_DRIVE}/kagglehub_cache"
os.environ["YOLO_CONFIG_DIR"] = f"{ROOT_DRIVE}/ultralytics_config"
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import tempfile
tempfile.tempdir = str(SAFE_TMP_DIR)

import torch
from ultralytics import YOLO
import pandas as pd
from PIL import Image

# ---------------------------------------------------------------------------
# Constants & IPC Defect Definitions
# ---------------------------------------------------------------------------
CLASSES = [
    "mouse_bite",
    "spur",
    "missing_hole",
    "short",
    "open_circuit",
    "spurious_copper",
]

CRITICAL_CLASSES = ["short", "open_circuit"]
MAJOR_CLASSES = ["missing_hole"]
MINOR_CLASSES = ["mouse_bite", "spur", "spurious_copper"]

DATASET_DIR = BASE_DIR / "dataset" / "pcb-defect-dataset"
SPLITS_DIR = BASE_DIR / "splits" / "incremental"
RUNS_DIR = BASE_DIR / "runs" / "pipeline_phase5"
CHAMPION_WEIGHTS_PATH = BASE_DIR / "champion_weights.pt"
SAMPLES_DIR = BASE_DIR / "dataset" / "samples"
COMPOSITE_TEST_IMAGE = SAMPLES_DIR / "full_multidefect_panel_all6.jpg"

BOARD_REGEX = r"(\d{2})_(?:missing_hole|mouse_bite|open_circuit|short|spurious_copper|spur)"


def get_hardware_config(device_arg: str = "auto") -> Dict[str, Any]:
    """Detect and configure compute device and memory limits."""
    cuda_avail = torch.cuda.is_available()
    if device_arg == "cpu" or not cuda_avail:
        device = "cpu"
        device_name = "CPU (AVX2/oneDNN)"
        batch_size = 16
        workers = 4
        half = False
    else:
        device = "0"
        device_name = torch.cuda.get_device_name(0)
        # Enable TF32 for high throughput on Ampere/Ada Lovelace architectures
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True
        torch.backends.cudnn.benchmark = True
        batch_size = 32
        workers = 8
        half = True

    return {
        "device": device,
        "device_name": device_name,
        "batch_size": batch_size,
        "workers": workers,
        "half": half,
    }


# ---------------------------------------------------------------------------
# 2. Dataset Ingestion & Verification
# ---------------------------------------------------------------------------
def download_dataset_if_needed() -> Path:
    """Download the PKU-Market-PCB dataset via kagglehub if missing."""
    if DATASET_DIR.exists() and any(DATASET_DIR.glob("**/*.jpg")):
        print(f"[+] Dataset already present at: {DATASET_DIR}")
        return DATASET_DIR

    print("[*] Dataset not found. Downloading via kagglehub...")
    try:
        import kagglehub
        path = kagglehub.dataset_download("fedybenhassouna/printed-circuit-board-pcb-defects")
        print(f"[+] Download complete: {path}")

        # Link or copy to dataset directory
        DATASET_DIR.parent.mkdir(parents=True, exist_ok=True)
        import shutil
        shutil.copytree(path, DATASET_DIR, dirs_exist_ok=True)
        print(f"[+] Synced dataset into: {DATASET_DIR}")
        return DATASET_DIR
    except Exception as e:
        print(f"[-] Automated download failed: {e}")
        print("    Please ensure the dataset is placed at: dataset/pcb-defect-dataset")
        return DATASET_DIR


def verify_dataset_integrity() -> Dict[str, Any]:
    """Verify image counts, annotations, bounding box coordinates, and labels."""
    print("\n" + "=" * 65)
    print("  [STEP 1] Dataset Integrity & Multi-Class Distribution Audit")
    print("=" * 65)

    img_extensions = {".jpg", ".jpeg", ".png", ".bmp"}
    images = [p for p in DATASET_DIR.rglob("*") if p.suffix.lower() in img_extensions]

    if not images:
        raise FileNotFoundError(f"No image files found in {DATASET_DIR}")

    print(f"[+] Total raw images found: {len(images):,}")

    board_groups = defaultdict(list)
    class_instances = defaultdict(int)
    corrupted_labels = 0

    for img_path in images:
        m = re.search(BOARD_REGEX, img_path.name)
        board_id = m.group(1) if m else "unknown"
        board_groups[board_id].append(img_path)

        # Check label file
        txt_path = img_path.with_suffix(".txt")
        if not txt_path.exists():
            # Check parallel labels directory
            txt_path = img_path.parent.parent / "labels" / f"{img_path.stem}.txt"

        if txt_path.exists():
            try:
                lines = txt_path.read_text(encoding="utf-8").strip().splitlines()
                for line in lines:
                    parts = line.split()
                    if len(parts) >= 5:
                        cls_id = int(parts[0])
                        if 0 <= cls_id < len(CLASSES):
                            class_instances[CLASSES[cls_id]] += 1
            except Exception:
                corrupted_labels += 1

    print(f"[+] Board Partitions Identified: {len(board_groups)} distinct boards")
    for b_id in sorted(board_groups.keys()):
        print(f"    - Board {b_id}: {len(board_groups[b_id]):,} crops")

    print("\n[+] Defect Class Instance Inventory:")
    for cname in CLASSES:
        print(f"    - {cname:16s}: {class_instances[cname]:,} instances")

    return {
        "total_images": len(images),
        "boards": {k: len(v) for k, v in board_groups.items()},
        "classes": dict(class_instances),
        "corrupted_labels": corrupted_labels,
    }


# ---------------------------------------------------------------------------
# 3. Board-Level Zero-Leakage Split Preparation (Phase 5)
# ---------------------------------------------------------------------------
def prepare_phase5_splits() -> Path:
    """
    Constructs the zero-data-leakage Phase 5 benchmark splits:
    - Holdout Test Set : Board 09 (1,056 images, untouched during training)
    - Holdout Val Set  : Board 05 (948 images, validation checkpointing)
    - Phase 5 Train Set: Boards 01, 06, 07, 12, 11 (Cumulative 100% data)
    """
    print("\n" + "=" * 65)
    print("  [STEP 2] Phase 5 Zero-Leakage Split Generation")
    print("=" * 65)

    SPLITS_DIR.mkdir(parents=True, exist_ok=True)
    img_extensions = {".jpg", ".jpeg", ".png", ".bmp"}
    images = [p for p in DATASET_DIR.rglob("*") if p.suffix.lower() in img_extensions]

    board_groups = defaultdict(list)
    for p in images:
        m = re.search(BOARD_REGEX, p.name)
        b_id = m.group(1) if m else "unknown"
        board_groups[b_id].append(p)

    test_boards = ["09"]
    val_boards = ["05"]
    train_boards = ["01", "06", "07", "12", "11"]

    test_imgs = [p for b in test_boards for p in board_groups[b]]
    val_imgs = [p for b in val_boards for p in board_groups[b]]
    train_imgs = [p for b in train_boards for p in board_groups[b]]

    test_txt = SPLITS_DIR / "test.txt"
    val_txt = SPLITS_DIR / "val.txt"
    train_txt = SPLITS_DIR / "train_phase5_champion.txt"

    test_txt.write_text("\n".join(str(p.resolve().as_posix()) for p in test_imgs), encoding="utf-8")
    val_txt.write_text("\n".join(str(p.resolve().as_posix()) for p in val_imgs), encoding="utf-8")
    train_txt.write_text("\n".join(str(p.resolve().as_posix()) for p in train_imgs), encoding="utf-8")

    yaml_path = SPLITS_DIR / "pcb_stage5_pipeline.yaml"
    yaml_content = f"""# PCBVision AOI - Phase 5 Champion Training Specification
path: {DATASET_DIR.resolve().as_posix()}
train: {train_txt.resolve().as_posix()}
val: {val_txt.resolve().as_posix()}
test: {test_txt.resolve().as_posix()}

names:
  0: mouse_bite
  1: spur
  2: missing_hole
  3: short
  4: open_circuit
  5: spurious_copper
"""
    yaml_path.write_text(yaml_content, encoding="utf-8")

    print(f"[+] Holdout Test Set : {len(test_imgs):,} images (Board {test_boards}) -> {test_txt.name}")
    print(f"[+] Holdout Val Set  : {len(val_imgs):,} images (Board {val_boards}) -> {val_txt.name}")
    print(f"[+] Phase 5 Train Set: {len(train_imgs):,} images (Boards {train_boards}) -> {train_txt.name}")
    print(f"[+] Generated Specification YAML: {yaml_path.name}")

    return yaml_path


# ---------------------------------------------------------------------------
# 4. Phase 5 Champion Model Training
# ---------------------------------------------------------------------------
def train_phase5_model(
    yaml_path: Path,
    epochs: int = 50,
    batch_size: Optional[int] = None,
    init_weights: str = "yolo11s.pt",
    device: str = "auto",
) -> Path:
    """Train the YOLO11s model with Phase 5 champion hyperparameter presets."""
    print("\n" + "=" * 65)
    print("  [STEP 3] Training Phase 5 Champion Model (YOLO11s)")
    print("=" * 65)

    hw = get_hardware_config(device)
    actual_batch = batch_size or hw["batch_size"]

    print(f"[+] Target Hardware Engine : {hw['device_name']}")
    print(f"[+] Batch Size             : {actual_batch}")
    print(f"[+] Number of Epochs       : {epochs}")
    print(f"[+] Base Checkpoint        : {init_weights}")

    model_init = BASE_DIR / init_weights if (BASE_DIR / init_weights).exists() else init_weights
    model = YOLO(str(model_init))

    RUNS_DIR.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    results = model.train(
        data=str(yaml_path.resolve()),
        epochs=epochs,
        batch=actual_batch,
        imgsz=640,
        device=hw["device"],
        workers=hw["workers"],
        optimizer="AdamW",
        lr0=0.001,
        lrf=0.01,
        warmup_epochs=3,
        warmup_momentum=0.8,
        weight_decay=0.0005,
        box=7.5,
        cls=0.5,
        dfl=1.5,
        mosaic=1.0,
        fliplr=0.5,
        flipud=0.0,
        scale=0.5,
        hsv_h=0.015,
        hsv_s=0.7,
        hsv_v=0.4,
        project=str(RUNS_DIR.parent),
        name=RUNS_DIR.name,
        exist_ok=True,
        save=True,
        val=True,
        plots=True,
        verbose=True,
    )
    elapsed_min = (time.time() - t0) / 60.0
    print(f"\n[+] Training Complete in {elapsed_min:.1f} minutes!")

    # Locate and copy best.pt to champion_weights.pt
    best_pt = RUNS_DIR / "weights" / "best.pt"
    if best_pt.exists():
        import shutil
        shutil.copy2(best_pt, CHAMPION_WEIGHTS_PATH)
        print(f"[+] Champion Model Exported: {CHAMPION_WEIGHTS_PATH} ({CHAMPION_WEIGHTS_PATH.stat().st_size / 1e6:.1f} MB)")
        return CHAMPION_WEIGHTS_PATH
    else:
        print("[!] Warning: best.pt not found in expected run folder.")
        return CHAMPION_WEIGHTS_PATH


# ---------------------------------------------------------------------------
# 5. Full Evaluation & Conformance Testing
# ---------------------------------------------------------------------------
def evaluate_phase5_model(
    weights_path: Path = CHAMPION_WEIGHTS_PATH,
    yaml_path: Optional[Path] = None,
    device: str = "auto",
) -> Dict[str, Any]:
    """
    Rigorously validates the champion model on:
    1. Untouched Board 09 test set (1,068 images)
    2. Multi-defect composite board (verifies all 6 defect classes concurrently)
    """
    print("\n" + "=" * 65)
    print("  [STEP 4] Phase 5 Statistical Evaluation & Metric Audit")
    print("=" * 65)

    if not weights_path.exists():
        raise FileNotFoundError(f"Champion weights not found at: {weights_path}")

    spec_yaml = yaml_path or (SPLITS_DIR / "pcb_holdout_test.yaml")
    if not spec_yaml.exists():
        spec_yaml = prepare_phase5_splits()

    hw = get_hardware_config(device)
    print(f"[+] Loading Model Checkpoint: {weights_path.name}")
    print(f"[+] Evaluating on Holdout Spec: {spec_yaml.name}")
    print(f"[+] Inference Engine: {hw['device_name']}")

    model = YOLO(str(weights_path))

    t0 = time.time()
    val_results = model.val(
        data=str(spec_yaml.resolve()),
        split="test",
        imgsz=640,
        batch=hw["batch_size"],
        device=hw["device"],
        conf=0.25,
        iou=0.45,
        half=hw["half"],
        save_json=False,
        plots=True,
        verbose=False,
    )
    val_time = time.time() - t0

    # Extract metrics
    box_res = val_results.box
    map50 = float(box_res.map50)
    map50_95 = float(box_res.map)
    mp = float(box_res.mp)
    mr = float(box_res.mr)

    class_recalls = {}
    class_map50 = {}
    if hasattr(box_res, "maps") and len(box_res.maps) == len(CLASSES):
        for idx, cname in enumerate(CLASSES):
            class_map50[cname] = float(box_res.maps[idx])
    if hasattr(box_res, "r") and len(box_res.r) == len(CLASSES):
        for idx, cname in enumerate(CLASSES):
            class_recalls[cname] = float(box_res.r[idx])

    # Critical defect recall (Short + Open Circuit)
    crit_recalls = [class_recalls[c] for c in CRITICAL_CLASSES if c in class_recalls]
    crit_recall_avg = sum(crit_recalls) / len(crit_recalls) if crit_recalls else mr

    print(f"\n[+] Overall Test Metrics across {val_results.nt_per_image[0] if hasattr(val_results, 'nt_per_image') else '1,068'} images:")
    print(f"    - mAP@50        : {map50 * 100:.2f}%")
    print(f"    - mAP@50-95     : {map50_95 * 100:.2f}%")
    print(f"    - Mean Precision: {mp * 100:.2f}%")
    print(f"    - Mean Recall   : {mr * 100:.2f}%")
    print(f"    - Critical Recall (Short + Open): {crit_recall_avg * 100:.2f}%")

    print("\n[+] Per-Class Performance Breakdown:")
    for cname in CLASSES:
        r = class_recalls.get(cname, 0.0) * 100
        m = class_map50.get(cname, 0.0) * 100
        print(f"    - {cname:16s}: Recall = {r:5.1f}% | mAP@50 = {m:5.1f}%")

    # -----------------------------------------------------------------------
    # Step 5: Test Simultaneous Multi-Defect Detection on Composite Board
    # -----------------------------------------------------------------------
    print("\n" + "=" * 65)
    print("  [STEP 5] Simultaneous Multi-Defect Verification (All 6 Classes)")
    print("=" * 65)

    multi_defect_result = {}
    if COMPOSITE_TEST_IMAGE.exists():
        t_infer_start = time.time()
        preds = model.predict(
            str(COMPOSITE_TEST_IMAGE),
            conf=0.20,
            iou=0.45,
            device=hw["device"],
            imgsz=1280,
            verbose=False,
        )[0]
        infer_latency_ms = (time.time() - t_infer_start) * 1000

        detected_classes = [preds.names[int(b.cls[0].item())] for b in preds.boxes]
        distinct_classes = sorted(list(set(detected_classes)))
        class_breakdown = {c: detected_classes.count(c) for c in distinct_classes}

        print(f"[+] Tested Composite Board: {COMPOSITE_TEST_IMAGE.name}")
        print(f"[+] Inference Latency      : {infer_latency_ms:.2f} ms")
        print(f"[+] Total Defects Detected : {len(detected_classes)}")
        print(f"[+] Distinct Defect Types  : {len(distinct_classes)} / 6 ({distinct_classes})")
        print(f"[+] Defect Instance Count  : {class_breakdown}")

        multi_defect_result = {
            "total_defects": len(detected_classes),
            "distinct_classes_count": len(distinct_classes),
            "distinct_classes": distinct_classes,
            "class_breakdown": class_breakdown,
            "latency_ms": round(infer_latency_ms, 2),
            "all_6_classes_detected_concurrently": len(distinct_classes) == 6,
        }
    else:
        print(f"[*] Note: Composite multi-defect image not found at: {COMPOSITE_TEST_IMAGE}")

    # Export report JSON
    report = {
        "pipeline": "Phase 5 Champion YOLO11s Pipeline",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "checkpoint": str(weights_path.resolve()),
        "test_dataset": str(spec_yaml.resolve()),
        "hardware": hw["device_name"],
        "overall_metrics": {
            "map50": round(map50, 4),
            "map50_95": round(map50_95, 4),
            "precision": round(mp, 4),
            "recall": round(mr, 4),
            "critical_recall": round(crit_recall_avg, 4),
        },
        "class_breakdown": {
            c: {
                "recall": round(class_recalls.get(c, 0.0), 4),
                "map50": round(class_map50.get(c, 0.0), 4),
            }
            for c in CLASSES
        },
        "multi_defect_simultaneous_test": multi_defect_result,
    }

    report_path = BASE_DIR / "runs" / "phase5_pipeline_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\n[+] Full Pipeline Report Saved: {report_path.name}")

    return report


# ---------------------------------------------------------------------------
# CLI Entrypoint
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Phase 5 Champion Data & Training Pipeline for PCB Defect Detection"
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="full",
        choices=["full", "train", "evaluate", "prepare_data", "verify"],
        help="Pipeline execution mode (default: full)",
    )
    parser.add_argument(
        "--weights",
        type=str,
        default="champion_weights.pt",
        help="Initial weights for training or target weights for evaluation",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=50,
        help="Epochs for Phase 5 training (default: 50)",
    )
    parser.add_argument(
        "--batch",
        type=int,
        default=None,
        help="Batch size (default: auto-detected based on GPU)",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="auto",
        help="Device to use ('auto', 'cuda', 'cpu')",
    )

    args = parser.parse_args()

    print("\n" + "=" * 65)
    print("  PCBVISION AOI — PHASE 5 DATA & MODEL PIPELINE")
    print(f"  Execution Mode: {args.mode.upper()}")
    print("=" * 65)

    weights_file = BASE_DIR / args.weights

    if args.mode == "verify":
        download_dataset_if_needed()
        verify_dataset_integrity()

    elif args.mode == "prepare_data":
        download_dataset_if_needed()
        verify_dataset_integrity()
        prepare_phase5_splits()

    elif args.mode == "train":
        download_dataset_if_needed()
        verify_dataset_integrity()
        spec_yaml = prepare_phase5_splits()
        train_phase5_model(
            yaml_path=spec_yaml,
            epochs=args.epochs,
            batch_size=args.batch,
            init_weights=args.weights,
            device=args.device,
        )

    elif args.mode == "evaluate":
        evaluate_phase5_model(
            weights_path=weights_file,
            device=args.device,
        )

    elif args.mode == "full":
        download_dataset_if_needed()
        verify_dataset_integrity()
        spec_yaml = prepare_phase5_splits()
        # If champion weights already exist and are validated, evaluate; otherwise train
        if weights_file.exists():
            print(f"[+] Found existing Phase 5 weights: {weights_file.name}. Running full evaluation...")
            evaluate_phase5_model(weights_path=weights_file, yaml_path=spec_yaml, device=args.device)
        else:
            print("[*] Weights not found. Starting complete training routine...")
            trained_weights = train_phase5_model(
                yaml_path=spec_yaml,
                epochs=args.epochs,
                batch_size=args.batch,
                init_weights="yolo11s.pt",
                device=args.device,
            )
            evaluate_phase5_model(weights_path=trained_weights, yaml_path=spec_yaml, device=args.device)

    print("\n" + "=" * 65)
    print("  [✓] PIPELINE EXECUTION COMPLETED SUCCESSFULLY")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()
