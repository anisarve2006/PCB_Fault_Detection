#!/usr/bin/env python3
"""
Comprehensive Model Testing & Deep Statistical Evaluation Script.
Evaluates the Phase 5 Champion model on test data, computing:
1. Overall mAP@50, mAP@50-95, Precision, Recall, F1
2. Per-class metrics across all 6 IPC defect classes
3. Latency & throughput on NVIDIA RTX 4090 (FPS)
4. Confusion matrix analysis & misclassification breakdown
5. IPC-A-610 safety & quality severity impact analysis
6. Comparison against historical incremental training phases
"""

import os
import sys
import json
import time
from pathlib import Path
import numpy as np
import pandas as pd

# Prevent OpenMP conflict
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import torch
from ultralytics import YOLO

ROOT_DIR = Path(__file__).resolve().parent
WEIGHTS_PATH = ROOT_DIR / "champion_weights.pt"
DATA_YAML = ROOT_DIR / "splits" / "incremental" / "pcb_stage_full.yaml"
HOLDOUT_YAML = ROOT_DIR / "splits" / "incremental" / "pcb_holdout_test.yaml"
METRICS_CSV = ROOT_DIR / "runs" / "incremental_training" / "incremental_metrics_summary.csv"

CLASS_NAMES = [
    "mouse_bite",
    "spur",
    "missing_hole",
    "short",
    "open_circuit",
    "spurious_copper",
]

CLASS_SEVERITY = {
    "short": "CRITICAL",
    "open_circuit": "CRITICAL",
    "missing_hole": "MAJOR",
    "mouse_bite": "MINOR",
    "spur": "MINOR",
    "spurious_copper": "MINOR",
}

def run_evaluation(data_config: Path, split_name: str = "test", project_name: str = "test_eval"):
    print("\n" + "=" * 70)
    print(f"  [*] RUNNING COMPREHENSIVE TEST ON DATASET: {split_name.upper()} SPLIT")
    print(f"  [+] Data Config: {data_config.resolve()}")
    print(f"  [+] Model Weights: {WEIGHTS_PATH.resolve()}")
    device = 0 if torch.cuda.is_available() else "cpu"
    dev_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU"
    print(f"  [+] Hardware Device: {dev_name} (device={device})")
    print("=" * 70 + "\n")

    model = YOLO(str(WEIGHTS_PATH))

    t0 = time.time()
    results = model.val(
        data=str(data_config),
        split=split_name,
        batch=32,
        device=device,
        project=str(ROOT_DIR / "runs" / project_name),
        name=f"eval_{split_name}_{int(time.time())}",
        plots=True,
        save_json=True,
        verbose=True
    )
    total_eval_time = time.time() - t0

    # Extract metrics
    metrics_dict = results.results_dict
    speed = results.speed # {'preprocess': ..., 'inference': ..., 'loss': ..., 'postprocess': ...}
    total_latency_ms = sum(speed.values())
    fps = 1000.0 / total_latency_ms if total_latency_ms > 0 else 0.0

    # Per-class metrics
    per_class_data = []
    box = results.box
    
    # Class mapping
    names = results.names
    p_curve = box.p # precision array per class
    r_curve = box.r # recall array per class
    ap50 = box.ap50 # AP@50 per class
    ap = box.ap # AP@50-95 per class
    f1 = box.f1 # F1 curve / max F1 per class

    for idx, cname in names.items():
        c_p = float(box.p[idx]) if idx < len(box.p) else 0.0
        c_r = float(box.r[idx]) if idx < len(box.r) else 0.0
        c_ap50 = float(box.ap50[idx]) if idx < len(box.ap50) else 0.0
        c_ap = float(box.ap[idx]) if idx < len(box.ap) else 0.0
        c_f1 = (2 * c_p * c_r) / (c_p + c_r) if (c_p + c_r) > 0 else 0.0
        
        per_class_data.append({
            "class_id": int(idx),
            "class_name": cname,
            "severity": CLASS_SEVERITY.get(cname, "MINOR"),
            "precision": round(c_p * 100, 2),
            "recall": round(c_r * 100, 2),
            "f1_score": round(c_f1 * 100, 2),
            "map50": round(c_ap50 * 100, 2),
            "map50_95": round(c_ap * 100, 2)
        })

    summary = {
        "dataset_split": split_name,
        "config_file": str(data_config),
        "total_images_tested": len(results.seen) if hasattr(results, 'seen') else getattr(results, 'nt_per_image', 'N/A'),
        "evaluation_time_sec": round(total_eval_time, 2),
        "hardware": dev_name,
        "latency_breakdown_ms": {
            "preprocess": round(speed.get("preprocess", 0.0), 2),
            "inference": round(speed.get("inference", 0.0), 2),
            "loss": round(speed.get("loss", 0.0), 2),
            "postprocess": round(speed.get("postprocess", 0.0), 2),
            "total_latency_per_image": round(total_latency_ms, 2)
        },
        "throughput_fps": round(fps, 1),
        "overall_metrics": {
            "precision": round(float(box.mp) * 100, 2),
            "recall": round(float(box.mr) * 100, 2),
            "map50": round(float(box.map50) * 100, 2),
            "map50_95": round(float(box.map) * 100, 2),
            "f1_mean": round(float(np.mean([c["f1_score"] for c in per_class_data])), 2)
        },
        "per_class": per_class_data
    }

    # Confusion matrix if available
    if hasattr(results, 'confusion_matrix') and results.confusion_matrix is not None:
        cm = results.confusion_matrix.matrix
        summary["confusion_matrix_raw"] = cm.tolist()
        # Compute background false positives & false negatives
        bg_idx = len(CLASS_NAMES) # background is last column/row
        if cm.shape[0] > bg_idx:
            summary["background_false_positives"] = int(np.sum(cm[bg_idx, :bg_idx]))
            summary["background_false_negatives"] = int(np.sum(cm[:bg_idx, bg_idx]))

    return summary, results

def print_deep_analysis(report: dict):
    ov = report["overall_metrics"]
    classes = report["per_class"]
    lat = report["latency_breakdown_ms"]

    print("\n" + "=" * 75)
    print("  🏆 PHASE 5 CHAMPION MODEL — DEEP TEST EVALUATION REPORT")
    print("=" * 75)
    print(f"  Target Split:             {report['dataset_split'].upper()}")
    print(f"  Hardware Acceleration:    {report['hardware']}")
    print(f"  Average Inference Time:   {lat['inference']} ms per image")
    print(f"  Total Pipeline Latency:   {lat['total_latency_per_image']} ms ({report['throughput_fps']} FPS)")
    print("-" * 75)
    print(f"  OVERALL mAP@50:           {ov['map50']}%")
    print(f"  OVERALL mAP@50-95:        {ov['map50_95']}%")
    print(f"  Mean Precision (mP):      {ov['precision']}%")
    print(f"  Mean Recall (mR):         {ov['recall']}%")
    print(f"  Mean F1-Score:            {ov['f1_mean']}%")
    print("=" * 75)

    print("\n" + "-" * 75)
    print("  PER-CLASS DEFECT DETECTION BREAKDOWN")
    print("-" * 75)
    header = f"  {'Defect Class':<18} | {'Severity':<9} | {'Precision':<10} | {'Recall':<8} | {'F1-Score':<9} | {'mAP@50':<8} | {'mAP@50-95'}"
    print(header)
    print("  " + "-" * 73)
    for c in classes:
        print(f"  {c['class_name']:<18} | {c['severity']:<9} | {c['precision']:>9}% | {c['recall']:>7}% | {c['f1_score']:>8}% | {c['map50']:>7}% | {c['map50_95']:>7}%")
    print("-" * 75)

    # IPC-A-610 Triage Analysis
    crit = [c for c in classes if c["severity"] == "CRITICAL"]
    maj = [c for c in classes if c["severity"] == "MAJOR"]
    minor = [c for c in classes if c["severity"] == "MINOR"]

    crit_recall = np.mean([c["recall"] for c in crit])
    maj_recall = np.mean([c["recall"] for c in maj])
    minor_recall = np.mean([c["recall"] for c in minor])

    print("\n" + "=" * 75)
    print("  🔍 IPC-A-610 QUALITY TRIAGE & FAILURE ANALYSIS")
    print("=" * 75)
    print(f"  [1] CRITICAL DEFECTS (Short Circuit, Open Circuit):")
    print(f"      - Mean Recall: {crit_recall:.2f}% | Catastrophic Escape Risk: {100 - crit_recall:.2f}%")
    for c in crit:
        print(f"        * {c['class_name']}: Recall = {c['recall']}%, Precision = {c['precision']}%, mAP@50 = {c['map50']}%")
    print(f"      - Factory Verdict: {'ZERO-ESCAPE STANDARD MET' if crit_recall >= 98.0 else 'REVIEW REQUIRED'}")

    print(f"\n  [2] MAJOR DEFECTS (Missing / Blocked Via Holes):")
    print(f"      - Recall: {maj_recall:.2f}% | Interlayer / Pin Insertion Blockage Safety")
    for c in maj:
        print(f"        * {c['class_name']}: Recall = {c['recall']}%, Precision = {c['precision']}%, mAP@50 = {c['map50']}%")

    print(f"\n  [3] MINOR DEFECTS (Spur Protrusions, Mouse Bites, Spurious Copper):")
    print(f"      - Mean Recall: {minor_recall:.2f}%")
    for c in minor:
        print(f"        * {c['class_name']}: Recall = {c['recall']}%, Precision = {c['precision']}%, mAP@50 = {c['map50']}%")

    # Comparison with Training Milestones
    if METRICS_CSV.exists():
        df_hist = pd.read_csv(METRICS_CSV)
        print("\n" + "=" * 75)
        print("  📈 EVOLUTION: PROGRESSION ACROSS TRAINING PHASES")
        print("=" * 75)
        for _, row in df_hist.iterrows():
            print(f"  Stage {row['Stage']} ({row['Data_Percentage']}): mAP@50 = {float(row['mAP@50'])*100:.2f}% | mAP@50-95 = {float(row['mAP@50-95'])*100:.2f}% | Short Recall = {float(row['Recall_short'])*100:.1f}% | Open Recall = {float(row['Recall_open_circuit'])*100:.1f}%")
        print(f"  Test Split Evaluation: mAP@50 = {ov['map50']:.2f}% | mAP@50-95 = {ov['map50_95']:.2f}%")
    print("=" * 75 + "\n")

def main():
    print("[*] Starting Phase 5 Test Data Evaluation Pipeline...")
    report, _ = run_evaluation(DATA_YAML, split_name="test", project_name="test_evaluation")
    print_deep_analysis(report)

    def json_converter(o):
        if isinstance(o, (np.integer, int)):
            return int(o)
        elif isinstance(o, (np.floating, float)):
            return float(o)
        elif isinstance(o, np.ndarray):
            return o.tolist()
        return str(o)

    # Save to JSON
    out_file = ROOT_DIR / "runs" / "test_evaluation_report.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(report, indent=2, default=json_converter), encoding="utf-8")
    print(f"[+] Complete structured evaluation report saved to: {out_file.resolve()}")

if __name__ == "__main__":
    main()
