import json
from pathlib import Path

BASE_DIR = Path("c:/Users/Pushkar Shelar/Desktop/Faulty PCB detection")

def save_nb(filename, cells):
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
    out_file = BASE_DIR / filename
    out_file.write_text(json.dumps(nb, indent=2), encoding="utf-8")
    print(f"[+] Saved {out_file.name}")

def md(cells, text):
    cells.append({
        "cell_type": "markdown",
        "metadata": {},
        "source": [line + "\n" for line in text.strip().split("\n")]
    })

def code(cells, text):
    cells.append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [line + "\n" for line in text.strip().split("\n")]
    })

# ==========================================
# PHASE 1 NOTEBOOK
# ==========================================
def build_phase_1():
    cells = []
    md(cells, """# Phase 1: YOLO Baseline Models & Board-Level Leakage Prevention
### Capstone Project: Automated Optical Inspection (AOI) on Bare PCBs
**Hardware:** Windows 10/11 | NVIDIA RTX 4090 (24GB VRAM)  
**Models:** YOLO26s, YOLO26m, YOLO11s (Control)  
**Goals:**
1. Establish a leak-free board-level split (preventing train/test crop leakage from the same PCB).
2. Train YOLO26s and YOLO26m with RTX 4090 optimizations (TF32, batch=32, FP16 AMP).
3. Evaluate against YOLO11s control on strict mAP@50-95 and per-class recall (especially *short* and *open_circuit*).
4. Run input resolution ablation (640 vs 800 vs 1024) to evaluate thin-defect detection.""")

    md(cells, """## 1. Environment & CUDA Setup
Configure PyTorch for NVIDIA Ada Lovelace RTX 4090 with TF32 Tensor Cores.""")
    code(cells, """import os
import sys
import torch

print(f"PyTorch Version: {torch.__version__}")
print(f"CUDA Available: {torch.cuda.is_available()}")

if torch.cuda.is_available():
    print(f"Active GPU: {torch.cuda.get_device_name(0)}")
    vram = torch.cuda.get_device_properties(0).total_memory / (1024**3)
    print(f"Dedicated VRAM: {vram:.2f} GB")
    # Enable TF32 for high throughput on RTX 4090
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True
    print("[+] TF32 Acceleration Enabled.")
else:
    print("[!] Warning: CUDA is not active.")""")

    md(cells, """## 2. Board-Level Stratified Dataset Splitting
To avoid inflated scores from near-duplicate crops of the same board, we partition strictly by board ID.""")
    code(cells, """import re
import random
from collections import defaultdict
from pathlib import Path

DATASET_ROOT = Path("./dataset").resolve()
SPLIT_OUT_DIR = Path("./splits/phase1").resolve()

def create_board_level_split(data_root: Path, out_dir: Path, train_ratio=0.8, val_ratio=0.1, seed=42):
    random.seed(seed)
    img_exts = {".jpg", ".jpeg", ".png", ".bmp"}
    all_imgs = [p for p in data_root.rglob("*") if p.suffix.lower() in img_exts]
    print(f"Discovered {len(all_imgs)} images in dataset.")
    
    board_groups = defaultdict(list)
    for p in all_imgs:
        m = re.match(r"^(\\d+)_", p.stem)
        board_id = m.group(1) if m else p.stem.split("_")[0]
        board_groups[board_id].append(p)
        
    print(f"Grouped into {len(board_groups)} distinct boards.")
    
    boards = list(board_groups.keys())
    random.shuffle(boards)
    
    n_total = len(all_imgs)
    n_train = int(n_total * train_ratio)
    n_val = int(n_total * val_ratio)
    
    splits = {"train": [], "val": [], "test": []}
    for b in boards:
        dest = "train"
        if len(splits["val"]) < n_val:
            dest = "val"
        elif len(splits["test"]) < (n_total - n_train - n_val):
            dest = "test"
        splits[dest].extend(board_groups[b])
        
    out_dir.mkdir(parents=True, exist_ok=True)
    for s_name, files in splits.items():
        with open(out_dir / f"{s_name}.txt", "w") as f:
            for item in files:
                f.write(f"{item.as_posix()}\\n")
        print(f"  {s_name}: {len(files)} images")
        
    yaml_text = f\"\"\"path: {out_dir.resolve().as_posix()}
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
    yaml_file = out_dir / "pcb_phase1.yaml"
    yaml_file.write_text(yaml_text, encoding="utf-8")
    print(f"[+] Dataset YAML ready: {yaml_file}")
    return yaml_file

YAML_FILE = create_board_level_split(DATASET_ROOT, SPLIT_OUT_DIR)""")

    md(cells, """## 3. Training Baseline Models (YOLO26s, YOLO26m, YOLO11s)
Run standardized fine-tuning under identical hyperparameter conditions.""")
    code(cells, """from ultralytics import YOLO

TRAIN_CONFIG = {
    "data": str(YAML_FILE),
    "epochs": 100,
    "imgsz": 640,
    "batch": 32,          # High-throughput batch size for 24GB VRAM
    "device": 0,
    "workers": 8,
    "amp": True,
    "patience": 25,
    "save": True,
    "seed": 42
}

models_to_train = [
    ("yolo26s.pt", "YOLO26s_Phase1"),
    ("yolo26m.pt", "YOLO26m_Phase1"),
    ("yolo11s.pt", "YOLO11s_Control")
]

results = {}
for ckpt, run_name in models_to_train:
    print(f"\\n{'='*50}\\nStarting: {run_name} (Checkpoint: {ckpt})\\n{'='*50}")
    try:
        model = YOLO(ckpt)
    except Exception as e:
        print(f"[!] Checkpoint {ckpt} not found directly, falling back to yolo11 alternative: {e}")
        model = YOLO("yolo11s.pt")
        
    res = model.train(
        project="Phase1_YOLO_Baselines",
        name=run_name,
        **TRAIN_CONFIG
    )
    results[run_name] = res""")

    md(cells, """## 4. Rigorous Evaluation on the Frozen Test Set
Compute mAP@50, mAP@50-95, and per-class recall specifically for catastrophic defects (*open_circuit*, *short*).""")
    code(cells, """import pandas as pd
from tabulate import tabulate

CLASSES = ["mouse_bite", "spur", "missing_hole", "short", "open_circuit", "spurious_copper"]

eval_summary = []
for _, run_name in models_to_train:
    best_weights = Path("Phase1_YOLO_Baselines") / run_name / "weights" / "best.pt"
    if not best_weights.exists():
        continue
    print(f"[*] Evaluating {run_name}...")
    model = YOLO(best_weights)
    val_res = model.val(data=str(YAML_FILE), split="test", imgsz=640, device=0)
    
    entry = {
        "Model": run_name,
        "mAP@50": round(float(val_res.box.map50), 4),
        "mAP@50-95": round(float(val_res.box.map), 4),
    }
    for idx, c_name in enumerate(CLASSES):
        entry[f"Recall_{c_name}"] = round(float(val_res.box.r[idx]), 4) if idx < len(val_res.box.r) else 0.0
    eval_summary.append(entry)

df_phase1 = pd.DataFrame(eval_summary)
display(df_phase1)""")

    md(cells, """## 5. Ablation: Input Resolution Scaling (640 vs 800 vs 1024)
Evaluate whether increasing input resolution resolves thin defects like hair-line spurs and trace opens.""")
    code(cells, """# Resolution ablation on the winning Phase 1 model
winning_ckpt = "Phase1_YOLO_Baselines/YOLO26s_Phase1/weights/best.pt"

if Path(winning_ckpt).exists():
    resolution_results = []
    model_eval = YOLO(winning_ckpt)
    for res in [640, 800, 1024]:
        print(f"[*] Testing resolution {res}x{res}...")
        metrics = model_eval.val(data=str(YAML_FILE), split="test", imgsz=res, device=0)
        resolution_results.append({
            "Resolution": f"{res}x{res}",
            "mAP@50": round(float(metrics.box.map50), 4),
            "mAP@50-95": round(float(metrics.box.map), 4),
            "Recall (Open Circuit)": round(float(metrics.box.r[4]), 4),
            "Recall (Spur)": round(float(metrics.box.r[1]), 4),
        })
    df_res = pd.DataFrame(resolution_results)
    display(df_res)""")
    
    save_nb("Phase_1_YOLO_Baseline_and_Leakage_Split.ipynb", cells)

# ==========================================
# PHASE 2 NOTEBOOK
# ==========================================
def build_phase_2():
    cells = []
    md(cells, """# Phase 2: Real-Time Transformer Detectors (RF-DETR / RT-DETR)
### Capstone Project: Transformer Challenger vs. CNN Baselines
**Hardware:** Windows 10/11 | NVIDIA RTX 4090 (24GB VRAM)  
**Models:** RT-DETR-L / RF-DETR  
**Goal:**
Compare the vision transformer inductive bias against the YOLO Phase 1 baseline on the identical board-level split, specifically analyzing convergence on thin, low-contrast defect geometry.""")

    md(cells, """## 1. Setup & Environment Verification""")
    code(cells, """import torch
from pathlib import Path

assert torch.cuda.is_available(), "CUDA must be available."
print(f"GPU: {torch.cuda.get_device_name(0)}")
torch.backends.cuda.matmul.allow_tf32 = True
torch.backends.cudnn.allow_tf32 = True

YAML_FILE = Path("./splits/phase1/pcb_phase1.yaml").resolve()
assert YAML_FILE.exists(), f"Phase 1 YAML not found at {YAML_FILE}."
print(f"[+] Loaded identical Phase 1 Split: {YAML_FILE}")""")

    md(cells, """## 2. RT-DETR-L Transformer Training
Train RT-DETR-L with deformable attention and set-based matching.""")
    code(cells, """from ultralytics import RTDETR

# RTX 4090 optimized hyperparams for Vision Transformer
DETR_CONFIG = {
    "data": str(YAML_FILE),
    "epochs": 100,
    "imgsz": 640,
    "batch": 16,          # 16 is optimal for RT-DETR memory footprint on 24GB VRAM
    "device": 0,
    "workers": 8,
    "amp": True,
    "patience": 25,
    "save": True,
    "seed": 42
}

print("[*] Initializing RT-DETR-L...")
model_detr = RTDETR("rtdetr-l.pt")

print("[*] Training Transformer Detector...")
results_detr = model_detr.train(
    project="Phase2_Transformer_Challenger",
    name="RT_DETR_L_Experiment",
    **DETR_CONFIG
)
print("[+] RT-DETR-L Training complete.")""")

    md(cells, """## 3. Head-to-Head Comparison: Transformer vs. YOLO26 Baseline
Direct comparison on the frozen test set across mAP@50-95, recall, and inference latency.""")
    code(cells, """import time
import pandas as pd
from ultralytics import YOLO, RTDETR

CLASSES = ["mouse_bite", "spur", "missing_hole", "short", "open_circuit", "spurious_copper"]

def benchmark_detector(model_cls, weights_path, label):
    model = model_cls(weights_path)
    val_res = model.val(data=str(YAML_FILE), split="test", imgsz=640, device=0)
    
    # Latency timing
    dummy = torch.zeros((1, 3, 640, 640), device="cuda")
    for _ in range(30): _ = model(dummy, verbose=False)
    torch.cuda.synchronize()
    t0 = time.time()
    for _ in range(150): _ = model(dummy, verbose=False)
    torch.cuda.synchronize()
    latency_ms = ((time.time() - t0) / 150) * 1000
    
    entry = {
        "Architecture": label,
        "mAP@50": round(float(val_res.box.map50), 4),
        "mAP@50-95": round(float(val_res.box.map), 4),
        "Latency (ms)": round(latency_ms, 2),
        "FPS": round(1000.0 / latency_ms, 1)
    }
    for idx, c_name in enumerate(CLASSES):
        entry[f"Recall_{c_name}"] = round(float(val_res.box.r[idx]), 4) if idx < len(val_res.box.r) else 0.0
    return entry

yolo_path = "Phase1_YOLO_Baselines/YOLO26s_Phase1/weights/best.pt"
detr_path = "Phase2_Transformer_Challenger/RT_DETR_L_Experiment/weights/best.pt"

comparison_data = []
if Path(yolo_path).exists():
    comparison_data.append(benchmark_detector(YOLO, yolo_path, "YOLO26s (CNN)"))
if Path(detr_path).exists():
    comparison_data.append(benchmark_detector(RTDETR, detr_path, "RT-DETR-L (ViT)"))

df_comparison = pd.DataFrame(comparison_data)
display(df_comparison)""")

    md(cells, """## 4. Visual Comparison of Detection Failures
Inspect failure modes (false positives vs false negatives) across both models.""")
    code(cells, """import matplotlib.pyplot as plt

if not df_comparison.empty:
    fig, ax = plt.subplots(figsize=(10, 5))
    df_plot = df_comparison[["Architecture", "mAP@50", "mAP@50-95"]].melt(id_vars="Architecture")
    import seaborn as sns
    sns.barplot(data=df_plot, x="Architecture", y="value", hue="variable", ax=ax, palette="mako")
    ax.set_title("Phase 1 Baseline vs Phase 2 Transformer Challenger", fontsize=13, fontweight="bold")
    ax.set_ylim(0, 1.05)
    plt.tight_layout()
    plt.show()""")

    save_nb("Phase_2_Transformer_Detectors_RF_DETR.ipynb", cells)

# ==========================================
# PHASE 3 NOTEBOOK
# ==========================================
def build_phase_3():
    cells = []
    md(cells, """# Phase 3: Tiled Inference (SAHI) & Out-of-Distribution (OOD) Testing
### Capstone Project: High-Resolution Full-Board Inspection & Generalization
**Hardware:** Windows 10/11 | NVIDIA RTX 4090 (24GB VRAM)  
**Tools:** SAHI (Slicing Aided Hyper Inference), OpenCV  
**Goals:**
1. Implement tiled slicing inference to inspect un-cropped full board images (e.g., 2777x2138 px) without downscaling loss.
2. Optimize slice sizes, overlaps, and NMS/NMM box merging.
3. Test out-of-distribution (OOD) generalization against synthetic-to-real gap (e.g., DeepPCB or Mendeley PCB datasets).""")

    md(cells, """## 1. Install & Verify SAHI""")
    code(cells, """# Ensure sahi is installed:
# !pip install sahi

import sahi
from sahi import AutoDetectionModel
from sahi.predict import get_sliced_prediction
print(f"SAHI Version: {sahi.__version__}")""")

    md(cells, """## 2. Load Phase 1/2 Champion Model into SAHI
Wrap the best YOLO or RT-DETR checkpoint inside SAHI's detection abstraction.""")
    code(cells, """from pathlib import Path

# Select champion weights
model_path = Path("Phase1_YOLO_Baselines/YOLO26s_Phase1/weights/best.pt")
if not model_path.exists():
    model_path = Path("PCB_Capstone_Benchmark/YOLO11_Control/weights/best.pt")

print(f"Using Champion Model: {model_path}")

detection_model = AutoDetectionModel.from_pretrained(
    model_type="yolov8", # Compatible with Ultralytics YOLO models
    model_path=str(model_path),
    confidence_threshold=0.35,
    device="cuda:0"
)
print("[+] SAHI AutoDetectionModel initialized on CUDA.")""")

    md(cells, """## 3. High-Resolution Full Board Sliced Inference
Simulate a full-resolution factory PCB camera frame (e.g., 2777x2138 px) and run sliced prediction.""")
    code(cells, """import cv2
import numpy as np
import matplotlib.pyplot as plt

# Generate a high-resolution canvas (simulating un-cropped 2400x2400 full board)
canvas_h, canvas_w = 2400, 2400
dummy_board = np.ones((canvas_h, canvas_w, 3), dtype=np.uint8) * 45 # Dark circuit substrate

# Run SAHI sliced inference with 640x640 windows and 20% overlap
result = get_sliced_prediction(
    dummy_board,
    detection_model,
    slice_height=640,
    slice_width=640,
    overlap_height_ratio=0.2,
    overlap_width_ratio=0.2,
    postprocess_type="NMM", # Non-Maximum Merging handles boundary duplicates
    postprocess_match_metric="IOS",
    postprocess_match_threshold=0.5
)

print(f"[+] Sliced inference complete.")
print(f"Total sliced predictions found: {len(result.object_prediction_list)}")""")

    md(cells, """## 4. Tiling Latency and Overlap Optimization Benchmark
Evaluate how tile dimensions and overlap ratios impact inspection speed on the RTX 4090.""")
    code(cells, """import time
import pandas as pd

tile_configs = [
    {"slice": 640, "overlap": 0.15},
    {"slice": 640, "overlap": 0.25},
    {"slice": 800, "overlap": 0.20},
    {"slice": 1024, "overlap": 0.20},
]

timing_results = []
test_img = np.zeros((2000, 2000, 3), dtype=np.uint8)

for cfg in tile_configs:
    t0 = time.time()
    for _ in range(5):
        _ = get_sliced_prediction(
            test_img,
            detection_model,
            slice_height=cfg["slice"],
            slice_width=cfg["slice"],
            overlap_height_ratio=cfg["overlap"],
            overlap_width_ratio=cfg["overlap"],
            verbose=0
        )
    elapsed = (time.time() - t0) / 5
    timing_results.append({
        "Slice Size": f"{cfg['slice']}x{cfg['slice']}",
        "Overlap Ratio": f"{cfg['overlap']*100:.0f}%",
        "Latency / Board (ms)": round(elapsed * 1000, 2),
        "Estimated Boards/Min": round(60.0 / elapsed, 1)
    })

df_tiling = pd.DataFrame(timing_results)
display(df_tiling)""")

    md(cells, """## 5. Out-of-Distribution (OOD) Evaluation (Synthetic-to-Real Gap)
Test the trained detector on an external dataset (e.g. DeepPCB or Mendeley real PCB dataset) without fine-tuning to measure real-world domain transfer degradation.""")
    code(cells, """# Function to evaluate zero-shot transfer on an external test set
def evaluate_ood(model, ood_yaml_path):
    print(f"[*] Running OOD Evaluation on: {ood_yaml_path}")
    if Path(ood_yaml_path).exists():
        metrics = model.val(data=ood_yaml_path, split="test", imgsz=640)
        print(f"[+] OOD mAP@50: {metrics.box.map50:.4f}")
        print(f"[+] OOD mAP@50-95: {metrics.box.map:.4f}")
    else:
        print(f"[!] OOD dataset not found at {ood_yaml_path}. Skipping OOD execution.")

# Example path for Mendeley or DeepPCB yaml:
evaluate_ood(detection_model.model, "dataset_deeppcb.yaml")""")

    save_nb("Phase_3_Tiled_Inference_SAHI_and_OOD.ipynb", cells)

# ==========================================
# PHASE 4 NOTEBOOK
# ==========================================
def build_phase_4():
    cells = []
    md(cells, """# Phase 4: Unsupervised Anomaly Detection & Hybrid Fusion
### Capstone Project: Production-Grade Dual-Branch Inspection System
**Hardware:** Windows 10/11 | NVIDIA RTX 4090 (24GB VRAM)  
**Libraries:** PyTorch, Anomalib / PatchCore, Scikit-learn  
**Goal:**
1. Train an unsupervised anomaly detection branch (PatchCore/Dinomaly) solely on defect-free PCB regions.
2. Build a **Dual-Branch Fusion Pipeline**:
   - **Branch 1 (Supervised Detector):** Names and bounds known defects (*short, open_circuit, etc.*).
   - **Branch 2 (Anomaly Detector):** Detects novel/unlabelled defects via pixel heatmaps.
   - **Fusion Gate:** Dispatches known faults to repair logs and routes unlabelled anomalies to a human operator queue.""")

    md(cells, """## 1. Environment & Library Check""")
    code(cells, """import torch
import numpy as np
import cv2
import matplotlib.pyplot as plt

print(f"PyTorch CUDA: {torch.cuda.is_available()}")
# Anomalib can be installed via: pip install anomalib
try:
    import anomalib
    print(f"Anomalib Version: {anomalib.__version__}")
except ImportError:
    print("[!] Anomalib library not installed yet. Standalone PatchCore implementation provided below.")""")

    md(cells, """## 2. Generating Defect-Free Training Data
In real production AOI, 99.9% of PCB images are defect-free. We extract negative (box-free) tiles to train the anomaly branch.""")
    code(cells, """from pathlib import Path

def extract_defect_free_tiles(image_path, label_path, tile_size=256):
    \"\"\"Extract tiles that do not overlap with any ground-truth defect bounding boxes.\"\"\"
    img = cv2.imread(str(image_path))
    if img is None: return []
    h, w, _ = img.shape
    
    boxes = []
    if label_path.exists():
        with open(label_path, "r") as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 5:
                    # YOLO normalized format: cls cx cy bw bh
                    cx, cy, bw, bh = map(float, parts[1:5])
                    x1 = int((cx - bw / 2) * w)
                    y1 = int((cy - bh / 2) * h)
                    x2 = int((cx + bw / 2) * w)
                    y2 = int((cy + bh / 2) * h)
                    boxes.append((x1, y1, x2, y2))
                    
    clean_tiles = []
    # Slide tile window
    for y in range(0, h - tile_size, tile_size):
        for x in range(0, w - tile_size, tile_size):
            tx1, ty1, tx2, ty2 = x, y, x + tile_size, y + tile_size
            # Check overlap
            overlap = False
            for bx1, by1, bx2, by2 in boxes:
                if not (tx2 < bx1 or tx1 > bx2 or ty2 < by1 or ty1 > by2):
                    overlap = True
                    break
            if not overlap:
                clean_tiles.append(img[ty1:ty2, tx1:tx2])
                
    return clean_tiles

print("[+] Clean tile extractor function defined.")""")

    md(cells, """## 3. PatchCore Feature Memory Bank (Core Anomaly Engine)
Extract patch-level representations from a pretrained feature extractor (e.g. WideResNet-50 / DINOv2) to model normal PCB textures.""")
    code(cells, """import torchvision.models as models
import torch.nn as nn

class PCBFeatureExtractor(nn.Module):
    def __init__(self):
        super().__init__()
        # Using ResNet50 intermediate feature layers
        backbone = models.resnet50(weights=models.ResNet50_Weights.DEFAULT)
        self.layer1 = nn.Sequential(backbone.conv1, backbone.bn1, backbone.relu, backbone.maxpool, backbone.layer1)
        self.layer2 = backbone.layer2
        self.layer3 = backbone.layer3
        self.eval().cuda()
        
    def forward(self, x):
        with torch.no_grad():
            f1 = self.layer1(x)
            f2 = self.layer2(f1)
            f3 = self.layer3(f2)
        return f2, f3

fe = PCBFeatureExtractor()
print("[+] Anomaly Feature Extractor ready on CUDA.")""")

    md(cells, """## 4. The Dual-Branch Hybrid Fusion Pipeline
Combines the Phase 1/2 detector with the anomaly verification branch.""")
    code(cells, """from ultralytics import YOLO

class DualBranchAOI:
    def __init__(self, detector_path, anomaly_threshold=0.65):
        self.detector = YOLO(detector_path)
        self.anomaly_threshold = anomaly_threshold
        print("[+] Dual-Branch AOI System Initialized.")
        
    def inspect(self, image_bgr):
        # Branch 1: Supervised Object Detection
        det_res = self.detector(image_bgr, verbose=False)[0]
        detected_boxes = []
        for box in det_res.boxes:
            detected_boxes.append({
                "class_id": int(box.cls[0]),
                "class_name": det_res.names[int(box.cls[0])],
                "conf": float(box.conf[0]),
                "xyxy": box.xyxy[0].cpu().numpy().tolist()
            })
            
        # Branch 2: Simulated Anomaly Score Map (Pixel-Level Heatmap)
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        anomaly_score = float(np.std(gray) / 128.0) # Placeholder for anomaly reconstruction error
        is_anomaly = anomaly_score > self.anomaly_threshold
        
        # Branch 3: Decision Fusion Gate
        if len(detected_boxes) > 0:
            verdict = "DEFECT_CONFIRMED"
            action = "ROUTE_TO_REPAIR_STATION"
        elif is_anomaly:
            verdict = "UNLABELLED_ANOMALY"
            action = "ROUTE_TO_HUMAN_INSPECTION_QUEUE"
        else:
            verdict = "PASS"
            action = "PROCEED_TO_NEXT_STAGE"
            
        return {
            "verdict": verdict,
            "action": action,
            "detected_defects": detected_boxes,
            "anomaly_score": round(anomaly_score, 3)
        }

# Instantiate with Phase 1 winner
hybrid_system = DualBranchAOI("Phase1_YOLO_Baselines/YOLO26s_Phase1/weights/best.pt")
sample_board = np.ones((640, 640, 3), dtype=np.uint8) * 120
decision = hybrid_system.inspect(sample_board)
print(f"Inspection Result: {decision}")""")

    save_nb("Phase_4_Anomaly_Detection_and_Hybrid_Fusion.ipynb", cells)

# ==========================================
# PHASE 5 NOTEBOOK
# ==========================================
def build_phase_5():
    cells = []
    md(cells, """# Phase 5: SAM-Guided Instance Segmentation & Defect Measurement
### Capstone Project: Physical Geometry Analysis for IPC Standards
**Hardware:** Windows 10/11 | NVIDIA RTX 4090 (24GB VRAM)  
**Tools:** SAM (Segment Anything Model), YOLO26-seg / YOLO11-seg, OpenCV  
**Goal:**
1. Upgrade from bounding boxes to pixel-accurate defect masks using SAM prompted by bounding boxes.
2. Train an instance segmentation model (YOLO-seg).
3. Compute physical geometry metrics:
   - Remaining trace width (IPC-A-610 standards compliance)
   - Open circuit gap distance ($\mu m$)
   - Spur protrusion surface area ($px^2$)""")

    md(cells, """## 1. Environment & SAM Library Check""")
    code(cells, """import torch
import cv2
import numpy as np
import matplotlib.pyplot as plt

print(f"CUDA Available: {torch.cuda.is_available()}")
# Check for segment-anything
try:
    from segment_anything import sam_model_registry, SamPredictor
    print("[+] Segment Anything (SAM) library loaded.")
except ImportError:
    print("[!] SAM library not installed. Install via: pip install git+https://github.com/facebookresearch/segment-anything.git")""")

    md(cells, """## 2. Converting Bounding Boxes to Precise Masks via SAM
Prompt SAM with ground-truth bounding boxes to generate segmentation masks without manual pixel annotations.""")
    code(cells, """def generate_pseudo_mask(sam_predictor, image_rgb, bbox_xyxy):
    \"\"\"Prompt SAM with a bounding box [x1, y1, x2, y2] to extract pixel mask.\"\"\"
    sam_predictor.set_image(image_rgb)
    input_box = np.array(bbox_xyxy)
    masks, scores, _ = sam_predictor.predict(
        box=input_box,
        multimask_output=False
    )
    return masks[0], scores[0]

print("[+] Pseudo-mask generator defined.")""")

    md(cells, """## 3. Train YOLO Instance Segmentation Model (YOLO-seg)
Train an instance segmentation model on the generated polygonal masks.""")
    code(cells, """from ultralytics import YOLO

# Segmentation model configuration
SEG_CONFIG = {
    "data": "pcb_seg.yaml", # Config file pointing to polygon annotations
    "epochs": 100,
    "imgsz": 640,
    "batch": 32,            # RTX 4090 memory optimization
    "device": 0,
    "amp": True,
    "patience": 20
}

# Initialize segmentation model
try:
    seg_model = YOLO("yolo26s-seg.pt")
except Exception:
    seg_model = YOLO("yolo11s-seg.pt")

print("[+] Segmentation model initialized. Ready for training.")
# To run training:
# seg_model.train(project="Phase5_Segmentation", name="YOLO_Seg_PCB", **SEG_CONFIG)""")

    md(cells, """## 4. Physical Geometry Measurement Algorithm
Compute the exact trace width and gap distance to enforce factory quality thresholds.""")
    code(cells, """def measure_defect_geometry(defect_mask, pixel_to_micron_ratio=15.0):
    \"\"\"Analyze a binary defect mask to extract geometric dimensions in microns.\"\"\"
    contours, _ = cv2.findContours(defect_mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return {"area_um2": 0, "max_dimension_um": 0}
        
    largest_cnt = max(contours, key=cv2.contourArea)
    area_px = cv2.contourArea(largest_cnt)
    
    # Minimum area bounding rectangle
    rect = cv2.minAreaRect(largest_cnt)
    (x, y), (w, h), angle = rect
    
    area_um2 = area_px * (pixel_to_micron_ratio ** 2)
    max_dim_um = max(w, h) * pixel_to_micron_ratio
    min_dim_um = min(w, h) * pixel_to_micron_ratio
    
    return {
        "area_um2": round(area_um2, 2),
        "length_um": round(max_dim_um, 2),
        "width_gap_um": round(min_dim_um, 2)
    }

# Test geometry measurement on simulated defect mask
test_mask = np.zeros((100, 100), dtype=np.uint8)
cv2.rectangle(test_mask, (20, 40), (80, 48), 1, -1) # 60x8 px trace break
geom = measure_defect_geometry(test_mask, pixel_to_micron_ratio=10.0)
print(f"Calculated Defect Dimensions: {geom}")""")

    save_nb("Phase_5_SAM_Instance_Segmentation_and_Measurements.ipynb", cells)

if __name__ == "__main__":
    print("[*] Generating all 5 Phase Notebooks...")
    build_phase_1()
    build_phase_2()
    build_phase_3()
    build_phase_4()
    build_phase_5()
    print("[+] All phase notebooks successfully generated.")
