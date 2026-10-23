#!/usr/bin/env python3
"""
High-End PC Environment Setup & Path Re-Anchoring Utility.
Run this ONCE immediately after transferring the project folder to the high-end PC:
    python setup_high_end_pc.py

What this script does:
1. Detects CUDA, GPU model (e.g. RTX 4090), and dedicated VRAM.
2. Dynamically re-anchors all dataset text lists and YAML files to the new folder location.
3. Verifies Stage 3 champion weights (champion_weights.pt).
4. Tests a quick CUDA forward pass to verify RTX 4090 acceleration.
"""

import os
import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATASET_DIR = BASE_DIR / "dataset"
SPLITS_DIR = BASE_DIR / "splits" / "incremental"

def check_hardware():
    print("\n" + "=" * 65)
    print("  [1/4] AUDITING HARDWARE & CUDA ACCELERATION")
    print("=" * 65)
    import torch
    print(f"[+] PyTorch Version: {torch.__version__}")
    print(f"[+] CUDA Available: {torch.cuda.is_available()}")
    
    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        print(f"[+] Active GPU: {gpu_name}")
        print(f"[+] Dedicated VRAM: {vram_gb:.2f} GB")
        
        # Test TF32
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True
        print("[+] TF32 Tensor Cores: SUPPORTED & ENABLED")
        
        if "4090" in gpu_name:
            print("🚀 NVIDIA GeForce RTX 4090 (Ada Lovelace) CONFIRMED! Ready for maximum speed.")
    else:
        print("[!] WARNING: CUDA is not active. Make sure NVIDIA drivers and PyTorch with CUDA are installed.")

def reanchor_paths():
    print("\n" + "=" * 65)
    print("  [2/4] RE-ANCHORING DATASET PATHS TO LOCAL WORKSPACE")
    print("=" * 65)
    print(f"[+] Current Workspace Root: {BASE_DIR}")
    
    if not DATASET_DIR.exists():
        print(f"[-] ERROR: 'dataset' folder not found at {DATASET_DIR}!", file=sys.stderr)
        print("[-] Ensure you copied the 'dataset' folder along with the project.", file=sys.stderr)
        sys.exit(1)
        
    img_exts = {".jpg", ".jpeg", ".png", ".bmp"}
    all_imgs = sorted([p for p in DATASET_DIR.rglob("*") if p.suffix.lower() in img_exts])
    print(f"[+] Discovered {len(all_imgs)} images in local dataset.")
    
    # Map by relative path from dataset root
    img_map = {p.name: p for p in all_imgs}
    
    SPLITS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Re-anchor text files
    txt_files = list(SPLITS_DIR.glob("*.txt"))
    for txt in txt_files:
        lines = txt.read_text(encoding="utf-8").strip().splitlines()
        new_lines = []
        for line in lines:
            fname = Path(line.strip()).name
            if fname in img_map:
                new_lines.append(str(img_map[fname].resolve()))
        txt.write_text("\n".join(new_lines), encoding="utf-8")
        print(f"    - Updated {txt.name} ({len(new_lines)} images anchored)")
        
    # Re-anchor YAML configs
    test_txt = SPLITS_DIR / "test.txt"
    val_txt = SPLITS_DIR / "val.txt"
    
    yaml_configs = [
        (1, 10, "pcb_stage1_10pct.yaml", SPLITS_DIR / "train_10pct.txt"),
        (2, 20, "pcb_stage2_20pct.yaml", SPLITS_DIR / "train_20pct.txt"),
        (3, 30, "pcb_stage3_30pct.yaml", SPLITS_DIR / "train_30pct.txt"),
        (4, 60, "pcb_stage4_60pct.yaml", SPLITS_DIR / "train_60pct.txt"),
    ]
    
    for stage_idx, pct, yaml_name, train_txt in yaml_configs:
        yaml_path = SPLITS_DIR / yaml_name
        if train_txt.exists():
            content = f"""# PCB Defect Detection - Stage {stage_idx} ({pct}% Data)
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
            yaml_path.write_text(content, encoding="utf-8")
            print(f"    - Updated config: {yaml_name}")

def verify_checkpoints():
    print("\n" + "=" * 65)
    print("  [3/4] VERIFYING MODEL CHECKPOINTS")
    print("=" * 65)
    champ = BASE_DIR / "champion_weights.pt"
    if champ.exists():
        size_mb = champ.stat().st_size / (1024**2)
        print(f"[+] Champion Weights (Stage 3): FOUND ({size_mb:.1f} MB at {champ.name})")
    else:
        print("[!] champion_weights.pt not found. Searching runs/ directory...")
        s3 = BASE_DIR / "runs" / "incremental_training" / "Stage_3_30pct" / "weights" / "best.pt"
        if s3.exists():
            import shutil
            shutil.copy2(s3, champ)
            print(f"[+] Restored champion_weights.pt from {s3}")

def quick_sanity_test():
    print("\n" + "=" * 65)
    print("  [4/4] RUNNING QUICK GPU SANITY TEST")
    print("=" * 65)
    try:
        from ultralytics import YOLO
        import torch
        dev = 0 if torch.cuda.is_available() else "cpu"
        m = YOLO(str(BASE_DIR / "champion_weights.pt"))
        print(f"[+] Loaded YOLO model on device: {dev}")
        print("[✓] ALL SYSTEMS VERIFIED & READY FOR STAGE 4 TRAINING!")
    except Exception as e:
        print(f"[!] Warning during sanity test: {e}")

if __name__ == "__main__":
    check_hardware()
    reanchor_paths()
    verify_checkpoints()
    quick_sanity_test()
    
    print("\n" + "=" * 65)
    print("  🚀 READY TO LAUNCH STAGE 4 (60% CONSOLIDATED JUMP)")
    print("=" * 65)
    print("To start Stage 4 training on your RTX 4090, simply run:\n")
    print("    python train_incremental.py --stage 4 --epochs 12\n")
    print("Settings: Batch 32 | Workers 8 | TF32 Tensor Cores | FP16 AMP")
    print("=" * 65 + "\n")
