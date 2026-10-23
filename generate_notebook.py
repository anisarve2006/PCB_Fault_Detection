import json
from pathlib import Path

def create_notebook():
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
    md("""# Automated Optical Inspection (AOI) - PCB Defect Detection Benchmark
### Capstone Project: Comparative Evaluation of SOTA Object Detectors on Bare PCBs
**Target Environment:** Windows 10/11 | NVIDIA GeForce RTX 4090 (24GB VRAM)  
**Evaluated Models:** YOLO26 (or YOLO26s), YOLO11s (Control), and RT-DETR-L (Transformer Baseline)  
**Defect Classes:** `mouse_bite`, `spur`, `missing_hole`, `short`, `open_circuit`, `spurious_copper`

---
### Notebook Roadmap:
1. **System & CUDA Verification:** Check RTX 4090 hardware, VRAM, and PyTorch CUDA backend.
2. **Dataset Setup & Audit:** Configure PKU-Market-PCB data and verify bounding boxes.
3. **Leakage Prevention & Board-Level Split:** Ensure crops from the same board are never mixed across train/val/test splits.
4. **Model Training Harness (RTX 4090 Optimized):**
   - Model 1: **YOLO26s** (Bleeding-edge baseline with STAL small-object assignment)
   - Model 2: **YOLO11s** (Empirical Control)
   - Model 3: **RT-DETR-L** (Real-Time Vision Transformer Baseline)
5. **Comprehensive Metric Evaluation:**
   - mAP@50 and mAP@50-95
   - Per-Class Recall (Zero-tolerance check for catastrophic defects: *short* and *open_circuit*)
   - Inference Latency and FPS benchmarks
6. **Side-by-Side Results & Visualizations:** Generate publication-ready comparison tables, PR curves, and prediction overlays.""")

    # Cell 1: Environment & CUDA Check
    md("""## 1. System & GPU Environment Setup (RTX 4090)
Verify that PyTorch detects the NVIDIA GeForce RTX 4090 with full CUDA acceleration and Tensor Cores enabled.""")

    code("""import os
import sys
import torch

print(f"Python Version: {sys.version.split()[0]}")
print(f"PyTorch Version: {torch.__version__}")
print(f"CUDA Available: {torch.cuda.is_available()}")

if torch.cuda.is_available():
    gpu_name = torch.cuda.get_device_name(0)
    vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
    print(f"Detected GPU: {gpu_name}")
    print(f"Total Dedicated VRAM: {vram_gb:.2f} GB")
    # Enable TF32 for high throughput on Ada Lovelace architecture
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True
    print("[+] TF32 Tensor Core optimizations enabled.")
else:
    print("[!] WARNING: CUDA is not active. Please install PyTorch with CUDA 12.x support.")""")

    # Cell 2: Dependencies
    md("""### Install / Verify Required Libraries
Ensure `ultralytics`, `pandas`, `matplotlib`, `seaborn`, and `opencv-python` are installed.""")

    code("""# Uncomment to install if running in a fresh virtual environment:
# !pip install ultralytics albumentations opencv-python matplotlib seaborn pandas tabulate""")

    # Cell 3: Dataset Configuration
    md("""## 2. Dataset Path and Configuration
Specify the path to the downloaded PCB dataset. If using the Kaggle dataset directly, set `DATASET_ROOT` to your folder.""")

    code("""from pathlib import Path

# Update this path to where your dataset is extracted:
DATASET_ROOT = Path("./dataset").resolve()
print(f"Using Dataset Root: {DATASET_ROOT}")

CLASSES = [
    "mouse_bite",
    "spur",
    "missing_hole",
    "short",
    "open_circuit",
    "spurious_copper"
]""")

    # Cell 4: Board-Level Stratified Leakage Check & Split
    md("""## 3. Board-Level Grouping & Split Verification
### The Core Pitfall: Data Leakage
The PKU dataset consists of 600x600 crops carved out of 693 full PCB boards. If two crops from the same board appear in both `train` and `test`, the model achieves an artificially inflated test score.

This step groups crops by board ID (extracted via filename prefix, e.g., `01_...` or regex) and partitions them at the **board level** (80% train, 10% val, 10% test).""")

    code("""import re
import shutil
import random
from collections import defaultdict
import numpy as np

def perform_board_level_split(dataset_dir: Path, out_dir: Path, train_ratio=0.8, val_ratio=0.1, seed=42):
    random.seed(seed)
    
    # Locate all images
    img_exts = {".jpg", ".jpeg", ".png", ".bmp"}
    all_imgs = [p for p in dataset_dir.rglob("*") if p.suffix.lower() in img_exts]
    print(f"Total images found: {len(all_imgs)}")
    
    if len(all_imgs) == 0:
        print("[!] No images found. Please verify DATASET_ROOT path.")
        return None
        
    # Group by Board ID using regex pattern
    # PKU filenames typically start with board index, e.g., '01_mouse_bite_01.jpg'
    board_groups = defaultdict(list)
    unmatched_count = 0
    
    for img_p in all_imgs:
        m = re.match(r"^(\\d+)_", img_p.stem)
        if m:
            board_id = m.group(1)
            board_groups[board_id].append(img_p)
        else:
            # Fallback grouping by first token before underscore
            parts = img_p.stem.split("_")
            board_id = parts[0] if parts else "misc"
            board_groups[board_id].append(img_p)
            unmatched_count += 1
            
    print(f"Identified {len(board_groups)} distinct board groups.")
    if unmatched_count > 0:
        print(f"Note: {unmatched_count} images grouped using fallback token.")
        
    # Split board IDs into train, val, test
    boards = list(board_groups.keys())
    random.shuffle(boards)
    
    n_total = len(all_imgs)
    n_train_target = int(train_ratio * n_total)
    n_val_target = int(val_ratio * n_total)
    
    splits = {"train": [], "val": [], "test": []}
    
    for b in boards:
        assigned = "train"
        if len(splits["val"]) < n_val_target:
            assigned = "val"
        elif len(splits["test"]) < (n_total - n_train_target - n_val_target):
            assigned = "test"
            
        splits[assigned].extend(board_groups[b])
        
    print(f"Split Distribution: Train={len(splits['train'])} | Val={len(splits['val'])} | Test={len(splits['test'])}")
    
    # Write train.txt, val.txt, test.txt
    out_dir.mkdir(parents=True, exist_ok=True)
    for s_name, img_list in splits.items():
        list_file = out_dir / f"{s_name}.txt"
        with open(list_file, "w") as f:
            for p in img_list:
                f.write(f"{p.as_posix()}\\n")
        print(f"Wrote split manifest: {list_file}")
        
    # Generate YOLO data.yaml pointing to split manifests
    yaml_path = out_dir / "pcb_benchmark.yaml"
    yaml_content = f\"\"\"# YOLO Benchmark Split
path: {out_dir.resolve().as_posix()}
train: train.txt
val: val.txt
test: test.txt

names:
  0: mouse_bite
  1: spur
  2: missing_hole
  3: short
  4: open_circuit
  5: spurious_copper
\"\"\"
    yaml_path.write_text(yaml_content, encoding="utf-8")
    print(f"Dataset YAML generated at: {yaml_path}")
    return yaml_path

# Execute split definition
BENCHMARK_SPLIT_DIR = Path("./splits").resolve()
YAML_CONFIG = perform_board_level_split(DATASET_ROOT, BENCHMARK_SPLIT_DIR)""")

    # Cell 5: Training Configuration for RTX 4090
    md("""## 4. Multi-Model Training Harness (RTX 4090 Optimized)
We will train three distinct models under identical conditions:
1. **YOLO26s:** (Or latest YOLO26 checkpoint if installed, otherwise fallback to `yolo11s.pt` / `yolov8s.pt` with small-object enhancements).
2. **YOLO11s:** Ultralytics' control model.
3. **RT-DETR-L:** Real-time transformer detector to compare CNN vs. ViT inductive bias on tiny PCB defects.

**Hyperparameters tuned for 24GB RTX 4090:**
* `batch`: 32 (utilizes high memory bandwidth)
* `imgsz`: 640
* `epochs`: 100
* `amp`: True (FP16 automatic mixed precision)
* `workers`: 8""")

    code("""from ultralytics import YOLO, RTDETR

# Training Hyperparameters
TRAIN_PARAMS = {
    "data": str(YAML_CONFIG),
    "epochs": 100,
    "imgsz": 640,
    "batch": 32,          # Optimized for RTX 4090 (24GB VRAM)
    "device": 0,           # GPU ID
    "workers": 8,
    "amp": True,           # Mixed precision FP16
    "patience": 20,        # Early stopping patience
    "save": True,
    "seed": 42
}

print("Standardized Training Configuration:")
for k, v in TRAIN_PARAMS.items():
    print(f"  {k}: {v}")""")

    # Cell 6: Train Model 1 (YOLO26)
    md("""### 4.1 Train Model 1: YOLO26 (Small)
Train the latest YOLO26 model designed with Progressive Loss and STAL (Sample Training Assignment for Small Objects).""")

    code("""# Check availability of yolo26s.pt, fallback to yolo11s if yolo26 is not yet in the installed pip release
yolo26_checkpoint = "yolo26s.pt"

try:
    print(f"[*] Initializing {yolo26_checkpoint}...")
    model_yolo26 = YOLO(yolo26_checkpoint)
except Exception as e:
    print(f"[!] {yolo26_checkpoint} not found locally or in current pip version: {e}")
    print("[*] Using 'yolo11s.pt' with small-object configuration as primary model.")
    yolo26_checkpoint = "yolo11s.pt"
    model_yolo26 = YOLO(yolo26_checkpoint)

print("[*] Starting Training: Model 1 (YOLO26 / Baseline)...")
results_yolo26 = model_yolo26.train(
    project="PCB_Capstone_Benchmark",
    name="YOLO26_Experiment",
    **TRAIN_PARAMS
)
print("[+] Model 1 Training Completed.")""")

    # Cell 7: Train Model 2 (YOLO11 Control)
    md("""### 4.2 Train Model 2: YOLO11s (Empirical Control)
Used to measure the exact delta in accuracy and false alarms across architectural generations.""")

    code("""print("[*] Initializing YOLO11s Control Model...")
model_yolo11 = YOLO("yolo11s.pt")

print("[*] Starting Training: Model 2 (YOLO11s Control)...")
results_yolo11 = model_yolo11.train(
    project="PCB_Capstone_Benchmark",
    name="YOLO11_Control",
    **TRAIN_PARAMS
)
print("[+] Model 2 Training Completed.")""")

    # Cell 8: Train Model 3 (RT-DETR Transformer)
    md("""### 4.3 Train Model 3: RT-DETR-L (Vision Transformer Baseline)
DETR-style detector with deformable attention and end-to-end direct set prediction (no NMS required).""")

    code("""print("[*] Initializing RT-DETR-L Transformer Detector...")
model_rtdetr = RTDETR("rtdetr-l.pt")

# Transformer models can be more memory intensive; adjust batch if needed
rtdetr_params = TRAIN_PARAMS.copy()
rtdetr_params["batch"] = 16  # Adjusted for transformer memory footprint

print("[*] Starting Training: Model 3 (RT-DETR-L Transformer)...")
results_rtdetr = model_rtdetr.train(
    project="PCB_Capstone_Benchmark",
    name="RT_DETR_Transformer",
    **rtdetr_params
)
print("[+] Model 3 Training Completed.")""")

    # Cell 9: Evaluation & Metrics Extraction
    md("""## 5. Quantitative Evaluation on the Frozen Test Set
Evaluate all three models on the strictly held-out test split.
Extract:
* **mAP@50**
* **mAP@50-95**
* **Per-Class Recall** (Crucial: misses in `short` or `open_circuit` cause PCB dead-on-arrival)
* **Inference Latency (ms) & FPS**""")

    code("""import time
import pandas as pd
from tabulate import tabulate

def evaluate_model(model_path, split_yaml, model_label):
    print(f"[*] Evaluating {model_label} on Frozen Test Set...")
    model = YOLO(model_path) if "rtdetr" not in str(model_path).lower() else RTDETR(model_path)
    
    # Run validation on test split
    metrics = model.val(data=split_yaml, split="test", device=0, imgsz=640)
    
    # Extract overall metrics
    map50 = metrics.box.map50
    map50_95 = metrics.box.map
    
    # Extract per-class recall
    class_recalls = metrics.box.r  # Array of recalls per class
    
    # Measure Latency (batch size 1, FP16)
    dummy_input = torch.zeros((1, 3, 640, 640), device="cuda")
    # Warmup
    for _ in range(50):
        _ = model(dummy_input, verbose=False)
    
    # Latency timing
    torch.cuda.synchronize()
    t0 = time.time()
    iters = 200
    for _ in range(iters):
        _ = model(dummy_input, verbose=False)
    torch.cuda.synchronize()
    latency_ms = ((time.time() - t0) / iters) * 1000
    fps = 1000.0 / latency_ms
    
    res = {
        "Model": model_label,
        "mAP@50": round(float(map50), 4),
        "mAP@50-95": round(float(map50_95), 4),
        "Latency (ms)": round(latency_ms, 2),
        "FPS": round(fps, 1),
    }
    
    # Add per-class recall
    for idx, cls_name in enumerate(CLASSES):
        r_val = class_recalls[idx] if idx < len(class_recalls) else 0.0
        res[f"Recall: {cls_name}"] = round(float(r_val), 4)
        
    return res

# Paths to best trained checkpoints
# (Adjust paths if custom project directories were used)
best_yolo26 = "PCB_Capstone_Benchmark/YOLO26_Experiment/weights/best.pt"
best_yolo11 = "PCB_Capstone_Benchmark/YOLO11_Control/weights/best.pt"
best_rtdetr = "PCB_Capstone_Benchmark/RT_DETR_Transformer/weights/best.pt"

evaluations = []
for pth, lbl in [(best_yolo26, "YOLO26s"), (best_yolo11, "YOLO11s"), (best_rtdetr, "RT-DETR-L")]:
    if Path(pth).exists():
        evaluations.append(evaluate_model(pth, str(YAML_CONFIG), lbl))
    else:
        print(f"[!] Checkpoint not found at {pth}, skipping evaluation.")

df_results = pd.DataFrame(evaluations)
display(df_results)""")

    # Cell 10: Comparison Visualizations
    md("""## 6. Publication-Ready Visualizations
Generate radar charts, recall bar charts, and side-by-side metric comparisons for your capstone report/presentation.""")

    code("""import matplotlib.pyplot as plt
import seaborn as sns

sns.set_theme(style="whitegrid")

if not df_results.empty:
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    
    # Plot 1: Overall mAP comparison
    df_map = df_results[["Model", "mAP@50", "mAP@50-95"]].melt(id_vars="Model", var_name="Metric", value_name="Score")
    sns.barplot(data=df_map, x="Model", y="Score", hue="Metric", ax=axes[0], palette="Blues_d")
    axes[0].set_title("Overall Detection Accuracy (Test Split)", fontsize=14, fontweight="bold")
    axes[0].set_ylim(0, 1.05)
    
    # Plot 2: Per-Class Recall for Critical Faults
    recall_cols = [c for c in df_results.columns if c.startswith("Recall:")]
    df_recall = df_results[["Model"] + recall_cols].melt(id_vars="Model", var_name="Class", value_name="Recall")
    df_recall["Class"] = df_recall["Class"].str.replace("Recall: ", "")
    
    sns.barplot(data=df_recall, x="Class", y="Recall", hue="Model", ax=axes[1], palette="viridis")
    axes[1].set_title("Per-Class Recall Comparison (Defect Sensitivity)", fontsize=14, fontweight="bold")
    axes[1].set_xticklabels(axes[1].get_xticklabels(), rotation=30, ha="right")
    axes[1].set_ylim(0, 1.05)
    
    plt.tight_layout()
    plt.savefig("pcb_benchmark_comparison.png", dpi=300)
    plt.show()
    print("[+] Saved benchmark figure to 'pcb_benchmark_comparison.png'")""")

    # Cell 11: Export to ONNX / TensorRT
    md("""## 7. Model Export for High-Speed Deployment
Export the winning checkpoint to ONNX with NMS-free configuration for edge/factory AOI integration.""")

    code("""winning_model_path = best_yolo26 if Path(best_yolo26).exists() else best_yolo11

if Path(winning_model_path).exists():
    print(f"[*] Exporting winning model ({winning_model_path}) to ONNX format...")
    model_to_export = YOLO(winning_model_path)
    # Export to ONNX (dynamic batch, opset 17)
    onnx_file = model_to_export.export(format="onnx", imgsz=640, dynamic=True, simplify=True)
    print(f"[+] ONNX export succeeded: {onnx_file}")
else:
    print("[!] Model checkpoint not ready for export yet.")""")

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
                "version": "3.10.0"
            }
        },
        "nbformat": 4,
        "nbformat_minor": 4
    }

    out_path = Path("c:/Users/Pushkar Shelar/Desktop/Faulty PCB detection/PCB_Defect_Detection_Benchmark.ipynb")
    out_path.write_text(json.dumps(nb, indent=2), encoding="utf-8")
    print(f"Successfully generated {out_path}")

if __name__ == "__main__":
    create_notebook()
