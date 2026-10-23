#!/usr/bin/env python3
"""Generate the Jupyter Notebook for Incremental PCB Defect Detection Training."""

import json
from pathlib import Path

BASE_DIR = Path("c:/Users/Pushkar Shelar/Desktop/Faulty PCB detection")

def build_notebook():
    cells = []

    def md(text):
        cells.append({
            "cell_type": "markdown",
            "metadata": {},
            "source": [line + "\n" for line in text.strip().split("\n")]
        })

    def code(text):
        cells.append({
            "cell_type": "code",
            "execution_count": None,
            "metadata": {},
            "outputs": [],
            "source": [line + "\n" for line in text.strip().split("\n")]
        })

    # Header
    md("""# Sequential Incremental Training & Learning Curve Analysis (YOLO11s)
### Automated Optical Inspection (AOI) on Bare PCBs — CPU Optimization Mode
**Hardware Profile:** Intel Core i7-12700H (14 cores / 20 threads) | PyTorch CPU Multi-threading  
**Model Architecture:** Ultralytics YOLO11s (9.4M Parameters)  
**Strategy:** Sequential Incremental Fine-Tuning across 5 Cumulative Data Stages:
- **Stage 1 (10% Data):** Board 01 (1,000 images, 9.4% actual)
- **Stage 2 (20% Data):** Boards 01, 06 (2,016 images, 18.9% actual)
- **Stage 3 (30% Data):** Boards 01, 06, 07 (3,036 images, 28.5% actual)
- **Stage 4 (40% Data):** Boards 01, 06, 07, 12 (4,128 images, 38.7% actual)
- **Stage 5 (50% Data):** Boards 01, 06, 07, 12, 11 (5,268 images, 49.4% actual)

**Zero Data Leakage:** Fixed Test Set (Board 09, 1,056 images) and Fixed Validation Set (Board 05, 948 images) remain completely isolated across all 5 stages.""")

    # Cell 1: Environment & CPU Setup
    md("""## 1. System Environment & CPU Optimization
Configure PyTorch to utilize the full performance cores of your Intel i7-12700H CPU.""")
    code("""import os
import sys
import torch
import pandas as pd
from pathlib import Path

print(f"Python Version: {sys.version.split()[0]}")
print(f"PyTorch Version: {torch.__version__}")
print(f"CPU Physical/Logical Cores: {os.cpu_count()}")

# Allocate 18 threads out of 20 for maximum CPU compute
torch.set_num_threads(18)
os.environ["OMP_NUM_THREADS"] = "18"
os.environ["MKL_NUM_THREADS"] = "18"
os.environ["OPENBLAS_NUM_THREADS"] = "18"
if torch.backends.mkldnn.is_available():
    torch.backends.mkldnn.enabled = True
print(f"[+] PyTorch active CPU threads: {torch.get_num_threads()} / {os.cpu_count()}")""")

    # Cell 2: Dataset Verification
    md("""## 2. Verify Incremental Batches & YAML Configurations
Ensure all 5 incremental stage configs are loaded and valid.""")
    code("""SPLITS_DIR = Path("./splits/incremental").resolve()

for stage_idx in range(1, 6):
    pct = stage_idx * 10
    yaml_file = SPLITS_DIR / f"pcb_stage{stage_idx}_{pct}pct.yaml"
    train_txt = SPLITS_DIR / f"train_{pct}pct.txt"
    with open(train_txt, "r") as f:
        img_count = len(f.readlines())
    print(f"Stage {stage_idx} ({pct}% Data): {img_count} images | Config: {yaml_file.name}")""")

    # Cell 3: Sequential Training Harness
    md("""## 3. Sequential Incremental Training Pipeline (Stages 1 to 5)
Run sequential training or individual stages directly.""")
    code("""from ultralytics import YOLO
import time

CLASSES = ["mouse_bite", "spur", "missing_hole", "short", "open_circuit", "spurious_copper"]
RUNS_DIR = Path("./runs/incremental_training").resolve()

def run_stage(stage_idx, epochs=12, batch_size=16, imgsz=640, workers=4, base_checkpoint=None):
    pct = stage_idx * 10
    yaml_path = SPLITS_DIR / f"pcb_stage{stage_idx}_{pct}pct.yaml"
    
    if base_checkpoint is None:
        if stage_idx == 1:
            base_checkpoint = "yolo11s.pt"
        else:
            base_checkpoint = str(RUNS_DIR / f"Stage_{stage_idx-1}_{(stage_idx-1)*10}pct" / "weights" / "best.pt")
            
    stage_name = f"Stage_{stage_idx}_{pct}pct"
    print(f"\\n{'='*60}\\nStarting Stage {stage_idx} ({pct}% Data) from {base_checkpoint}\\n{'='*60}")
    
    model = YOLO(base_checkpoint)
    t0 = time.time()
    
    train_res = model.train(
        data=str(yaml_path),
        epochs=epochs,
        batch=batch_size,
        imgsz=imgsz,
        device="cpu",
        workers=workers,
        project=str(RUNS_DIR),
        name=stage_name,
        patience=5,
        save=True,
        val=True
    )
    duration_min = (time.time() - t0) / 60.0
    
    best_weights = RUNS_DIR / stage_name / "weights" / "best.pt"
    print(f"[+] Stage {stage_idx} completed in {duration_min:.2f} min. Best weights: {best_weights}")
    
    # Evaluate strictly on the untouched test set (Board 09)
    eval_model = YOLO(str(best_weights))
    val_res = eval_model.val(data=str(yaml_path), split="test", imgsz=imgsz, device="cpu", batch=16, verbose=False)
    
    stage_metrics = {
        "Stage": stage_idx,
        "Data_Pct": f"{pct}%",
        "Train_Time_Min": round(duration_min, 2),
        "mAP@50": round(float(val_res.box.map50), 4),
        "mAP@50-95": round(float(val_res.box.map), 4),
    }
    for idx, c in enumerate(CLASSES):
        stage_metrics[f"Recall_{c}"] = round(float(val_res.box.r[idx]), 4) if idx < len(val_res.box.r) else 0.0
        
    return str(best_weights), stage_metrics""")

    # Cell 4: Execute Stage 1
    md("""## 4. Run Stage 1 (10% Data Batch)
Train the initial baseline on Board 01 (1,000 images).""")
    code("""# Execute Stage 1
stage1_weights, stage1_metrics = run_stage(stage_idx=1, epochs=12, batch_size=8, imgsz=640)
df_results = pd.DataFrame([stage1_metrics])
display(df_results)""")

    # Cell 5: Comparative Learning Curve Plot
    md("""## 5. Learning Curve & Sample Efficiency Visualization
Plot the progression of mAP and critical defect recalls as data volume increases from 10% to 50%.""")
    code("""import matplotlib.pyplot as plt

summary_csv = RUNS_DIR / "incremental_metrics_summary.csv"
if summary_csv.exists():
    df = pd.read_csv(summary_csv)
    display(df)
    
    fig, ax1 = plt.subplots(figsize=(10, 5))
    ax1.plot(df["Data_Percentage"], df["mAP@50"], marker="o", label="mAP@50", color="#1f77b4", linewidth=2)
    ax1.plot(df["Data_Percentage"], df["mAP@50-95"], marker="s", label="mAP@50-95", color="#ff7f0e", linewidth=2)
    ax1.plot(df["Data_Percentage"], df["Recall_short"], marker="^", label="Recall: Short", color="#d62728", linestyle="--")
    ax1.plot(df["Data_Percentage"], df["Recall_open_circuit"], marker="d", label="Recall: Open Circuit", color="#2ca02c", linestyle="--")
    
    ax1.set_xlabel("Dataset Volume (Cumulative)")
    ax1.set_ylabel("Metric Score (0.0 - 1.0)")
    ax1.set_title("PCB Defect Detection — Data Scaling & Learning Curve (YOLO11s)")
    ax1.grid(True, linestyle=":", alpha=0.6)
    ax1.legend(loc="lower right")
    plt.tight_layout()
    plt.show()
else:
    print("[*] Run the training stages above to generate the metrics summary.")""")

    nb = {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3"
            },
            "language_info": {
                "name": "python",
                "version": "3.13.7"
            }
        },
        "nbformat": 4,
        "nbformat_minor": 4
    }
    out_file = BASE_DIR / "Incremental_PCB_Training_YOLO11s.ipynb"
    out_file.write_text(json.dumps(nb, indent=2), encoding="utf-8")
    print(f"[+] Saved notebook: {out_file.name}")

if __name__ == "__main__":
    build_notebook()
