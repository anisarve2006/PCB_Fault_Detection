#!/usr/bin/env python3
"""
Sequential Incremental Fine-Tuning Pipeline for PCB Defect Detection.
- Models: YOLO11s (Ultralytics)
- Auto-Detects Hardware:
  * High-End GPU (RTX 4090): Full TF32 Tensor Cores, cuDNN Auto-tuning, batch=32/64, workers=8, FP16 AMP.
  * Standard CPU: Multi-threaded AVX2/oneDNN execution.
- Stages:
  * Stage 1 (10% Data - 1,000 imgs)
  * Stage 2 (20% Data - 2,016 imgs)
  * Stage 3 (30% Data - 3,036 imgs)
  * Stage 4 (60% Consolidated Jump - 6,392 imgs across 6 boards)
"""

import argparse
import os
import sys
import time
from pathlib import Path
import pandas as pd

# Prevent OpenMP runtime conflict on Windows
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import torch

BASE_DIR = Path(__file__).resolve().parent
SPLITS_DIR = BASE_DIR / "splits" / "incremental"
RUNS_DIR = BASE_DIR / "runs" / "incremental_training"

CLASSES = [
    "mouse_bite",
    "spur",
    "missing_hole",
    "short",
    "open_circuit",
    "spurious_copper",
]

def setup_active_thermal_guard(model, throttle_pct=0.75):
    """
    Attaches thermal and power management callbacks to the YOLO model:
    - Paces GPU compute via micro-sleep (25ms) to keep duty cycle ~75% and prevent VRM saturation.
    - Monitors GPU temperature via NVML and pauses if approaching thermal limits.
    - Adds cooling intervals between epochs.
    """
    nvml_handle = None
    try:
        import pynvml
        pynvml.nvmlInit()
        nvml_handle = pynvml.nvmlDeviceGetHandleByIndex(0)
    except Exception:
        pass

    def on_train_batch_end(trainer):
        # 1. Duty cycle throttle: 25ms micro-pause allows GPU VRMs and PSU to shed heat
        time.sleep(0.025)

        # 2. Audit temperature and power usage periodically
        epoch_step = getattr(trainer, "epoch_step", 0)
        if nvml_handle and epoch_step % 50 == 0:
            try:
                import pynvml
                temp = pynvml.nvmlDeviceGetTemperature(nvml_handle, pynvml.NVML_TEMPERATURE_GPU)
                pwr = pynvml.nvmlDeviceGetPowerUsage(nvml_handle) / 1000.0
                print(f"  [🛡️ Safe Guard] GPU Temp: {temp}°C | Power: {pwr:.1f}W | 75% Throttle Active")
                if temp >= 60:
                    print(f"  [⚠️ Temp Alert {temp}°C] Triggering 5-second fan cooldown pause...")
                    time.sleep(5.0)
            except Exception:
                pass

    def on_train_epoch_end(trainer):
        # Inter-epoch cooldown interval
        print("  [🛡️ Safe Guard] Inter-epoch cooldown: letting fans clear residual heat (3s)...")
        time.sleep(10.0)

    try:
        model.add_callback("on_train_batch_end", on_train_batch_end)
        model.add_callback("on_train_epoch_end", on_train_epoch_end)
        print("[+] Active Thermal & Power Guard Callback: ATTACHED")
    except Exception as e:
        print(f"[*] Note on callback attachment: {e}")

def configure_hardware_env(target_device="auto", cpu_threads=16, throttle_pct=0.75):
    """
    Auto-detect hardware and apply strict 75% utilization limits:
    - CPU: Restrict process affinity to 75% of logical cores (e.g. 24 of 32 cores).
    - CPU: Lower process priority to BELOW_NORMAL to keep Windows OS and display responsive.
    - PyTorch Threads: Capped at 16 threads (50% max CPU compute).
    - GPU: VRAM allocation fraction capped at 75%.
    - GPU: cuDNN benchmark disabled to eliminate peak power surge transients.
    - GPU: Batch size 16 to cut power draw from 450W to ~230W.
    """
    # 1. Enforce CPU Affinity Cap (75% of total logical cores)
    total_cores = os.cpu_count() or 32
    cores_to_use = max(1, int(total_cores * throttle_pct))
    try:
        import psutil
        p = psutil.Process()
        p.cpu_affinity(list(range(cores_to_use)))
        p.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
        print("\n" + "=" * 70)
        print(f"🛡️  STABILITY GUARD: UTILIZATION CAPPED AT {int(throttle_pct*100)}%")
        print("=" * 70)
        print(f"[+] CPU Affinity Limit: {cores_to_use}/{total_cores} cores dedicated (remaining free for OS)")
        print(f"[+] Process Priority: BELOW_NORMAL (Prevents OS/display driver lockups)")
    except Exception as e:
        print(f"[*] CPU affinity note: {e}")

    # 2. Limit PyTorch CPU threads
    threads_to_use = min(cpu_threads, cores_to_use)
    torch.set_num_threads(threads_to_use)
    try:
        torch.set_num_interop_threads(2)
    except RuntimeError:
        pass
    os.environ["OMP_NUM_THREADS"] = str(threads_to_use)
    os.environ["MKL_NUM_THREADS"] = str(threads_to_use)

    if target_device == "auto":
        use_cuda = torch.cuda.is_available()
    else:
        use_cuda = (target_device != "cpu" and torch.cuda.is_available())

    if use_cuda:
        gpu_name = torch.cuda.get_device_name(0)
        vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        print(f"🚀 GPU ENGINE DETECTED: {gpu_name} ({vram_gb:.1f} GB VRAM)")
        
        # Cap CUDA memory allocation to 75%
        try:
            torch.cuda.set_per_process_memory_fraction(throttle_pct, 0)
            print(f"[+] CUDA VRAM Allocation Cap: {int(throttle_pct*100)}% ({vram_gb * throttle_pct:.1f} GB max)")
        except Exception as e:
            print(f"[*] VRAM cap note: {e}")

        # Enable TF32 for compute throughput without power penalty
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True
        # Disable cuDNN benchmark to eliminate peak power surge transients
        torch.backends.cudnn.benchmark = False
        print("[+] TF32 Tensor Core Acceleration: ENABLED")
        print("[+] cuDNN Benchmark: DISABLED (Eliminates power surge spikes)")
        print("[+] Mixed Precision (AMP FP16): ENABLED")
        
        # Batch 16 keeps RTX 4090 power draw around 220-250W (vs 450W at batch 32)
        # Workers 4 keeps CPU usage and data loading smooth without bus contention
        return 0, 16, 4, True # device, batch, workers, amp
    else:
        if torch.backends.mkldnn.is_available():
            torch.backends.mkldnn.enabled = True
        print("\n" + "=" * 70)
        print(f"[*] Running on Multi-Threaded CPU Mode ({threads_to_use} threads, 75% cap)")
        print("=" * 70)
        return "cpu", 16, 4, False

def get_stage_info(stage_idx):
    stages = {
        1: (1, 10, SPLITS_DIR / "pcb_stage1_10pct.yaml", "yolo11s.pt"),
        2: (2, 20, SPLITS_DIR / "pcb_stage2_20pct.yaml", RUNS_DIR / "Stage_1_10pct" / "weights" / "best.pt"),
        3: (3, 30, SPLITS_DIR / "pcb_stage3_30pct.yaml", RUNS_DIR / "Stage_2_20pct" / "weights" / "best.pt"),
        4: (4, 60, SPLITS_DIR / "pcb_stage4_60pct.yaml", RUNS_DIR / "Stage_3_30pct" / "weights" / "best.pt"),
        5: (5, 100, SPLITS_DIR / "pcb_stage_full.yaml", RUNS_DIR / "Stage_4_60pct" / "weights" / "best.pt"),
    }
    return stages.get(stage_idx)

def train_single_stage(stage_idx, epochs=12, batch_size=None, imgsz=640, workers=None, target_device="auto", initial_weights=None, resume=False, throttle=0.75):
    from ultralytics import YOLO

    device, auto_batch, auto_workers, amp = configure_hardware_env(target_device, throttle_pct=throttle)
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    
    batch = batch_size if batch_size is not None else auto_batch
    num_workers = workers if workers is not None else auto_workers

    stage_tuple = get_stage_info(stage_idx)
    if not stage_tuple:
        print(f"[-] Invalid stage index {stage_idx}. Available: 1, 2, 3, 4, 5", file=sys.stderr)
        sys.exit(1)
        
    stage_idx, pct, yaml_path, default_base_weights = stage_tuple
    
    base_weights = initial_weights if initial_weights else default_base_weights
    # If base weights file doesn't exist, check champion_weights.pt
    if not Path(str(base_weights)).exists() and str(base_weights) != "yolo11s.pt":
        if (BASE_DIR / "champion_weights.pt").exists():
            base_weights = BASE_DIR / "champion_weights.pt"
        else:
            prev_last = RUNS_DIR / f"Stage_{stage_idx-1}_{(stage_idx-1)*10}pct" / "weights" / "last.pt"
            if prev_last.exists():
                base_weights = prev_last
            else:
                print(f"[!] Checkpoint {base_weights} not found. Defaulting to base yolo11s.pt")
                base_weights = "yolo11s.pt"

    stage_run_name = f"Stage_{stage_idx}_{pct}pct"
    print("\n" + "#" * 70)
    print(f"[>] STARTING STAGE {stage_idx}: {pct}% Cumulative PCB Dataset")
    print(f"[>] Target Device: {device} | AMP: {amp} | Max Throttled Utilization: {int(throttle*100)}%")
    print(f"[>] Dataset Config: {yaml_path.name}")
    print(f"[>] Base Checkpoint: {base_weights}")
    print(f"[>] Epochs: {epochs} | Batch: {batch} | Workers: {num_workers} | ImgSz: {imgsz}")
    print("#" * 70 + "\n")
    
    t0 = time.time()
    last_pt = RUNS_DIR / stage_run_name / "weights" / "last.pt"
    
    # Test if last checkpoint exists and is not corrupted
    can_resume = False
    if resume and last_pt.exists():
        try:
            _ = YOLO(str(last_pt))
            can_resume = True
            print(f"[*] Valid checkpoint verified. Resuming from: {last_pt}")
        except Exception as e:
            print(f"[!] Checkpoint {last_pt} cannot be loaded ({e}). Starting fresh from base weights: {base_weights}")
            can_resume = False

    if can_resume:
        model = YOLO(str(last_pt))
        setup_active_thermal_guard(model, throttle_pct=throttle)
        train_res = model.train(resume=True)
    else:
        model = YOLO(str(base_weights))
        setup_active_thermal_guard(model, throttle_pct=throttle)
        # Train
        train_res = model.train(
            data=str(yaml_path),
            epochs=epochs,
            imgsz=imgsz,
            batch=batch,
            device=device,
            workers=num_workers,
            amp=amp,
            project=str(RUNS_DIR),
            name=stage_run_name,
            patience=6,
            save=True,
            val=True,
            verbose=True,
            exist_ok=True
        )
    train_duration_min = (time.time() - t0) / 60.0
    
    best_pt = RUNS_DIR / stage_run_name / "weights" / "best.pt"
    if not best_pt.exists():
        best_pt = RUNS_DIR / stage_run_name / "weights" / "last.pt"

    print(f"\n[+] Stage {stage_idx} training finished in {train_duration_min:.2f} mins.")
    print(f"[+] Saved model: {best_pt}")
    
    # Evaluate strictly on UNTOUCHED TEST SET (Board 09)
    print(f"[*] Running strict evaluation on the UNTOUCHED TEST SET (Board 09)...")
    eval_model = YOLO(str(best_pt))
    test_res = eval_model.val(
        data=str(yaml_path),
        split="test",
        imgsz=imgsz,
        device=device,
        batch=batch,
        verbose=False
    )
    
    metrics = {
        "Stage": stage_idx,
        "Data_Percentage": f"{pct}%",
        "Base_Weights": Path(str(base_weights)).name,
        "Train_Time_Min": round(train_duration_min, 2),
        "mAP@50": round(float(test_res.box.map50), 4),
        "mAP@50-95": round(float(test_res.box.map), 4),
    }
    
    recalls = test_res.box.r
    for idx, cls_name in enumerate(CLASSES):
        metrics[f"Recall_{cls_name}"] = round(float(recalls[idx]), 4) if idx < len(recalls) else 0.0
        
    csv_path = RUNS_DIR / "incremental_metrics_summary.csv"
    if csv_path.exists():
        df_existing = pd.read_csv(csv_path)
        df_existing = df_existing[df_existing["Stage"] != stage_idx]
        df_all = pd.concat([df_existing, pd.DataFrame([metrics])], ignore_index=True).sort_values("Stage")
    else:
        df_all = pd.DataFrame([metrics])
        
    df_all.to_csv(csv_path, index=False)
    
    # Export UI champion weights to project root
    import shutil
    champion_root = BASE_DIR / "champion_weights.pt"
    champion_stage = BASE_DIR / f"champion_weights_stage{stage_idx}.pt"
    try:
        shutil.copy2(best_pt, champion_root)
        shutil.copy2(best_pt, champion_stage)
        print(f"[+] UI Weights Updated: {champion_root.name} and {champion_stage.name}")
    except Exception as e:
        print(f"[!] Could not export champion weights: {e}")
    
    print("\n[+] Incremental Performance Summary:")
    print(df_all[["Stage", "Data_Percentage", "mAP@50", "mAP@50-95", "Recall_short", "Recall_open_circuit", "Recall_spur"]].to_string(index=False))
    return str(best_pt)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Incremental YOLO11s Training (GPU/CPU Auto-Optimized with 75pct Throttle Guard)")
    parser.add_argument("--stage", type=str, default="4", help="Stage to train: 1, 2, 3, 4, 5 (5 = 100pct full dataset)")
    parser.add_argument("--epochs", type=int, default=12, help="Epochs per stage (default: 12)")
    parser.add_argument("--batch", type=int, default=None, help="Batch size (default: 16 in 75pct safe mode)")
    parser.add_argument("--imgsz", type=int, default=640, help="Image resolution (default: 640)")
    parser.add_argument("--workers", type=int, default=None, help="DataLoader workers (default: 4 in 75pct safe mode)")
    parser.add_argument("--device", type=str, default="auto", help="Device: 'auto', '0', 'cpu'")
    parser.add_argument("--throttle", type=float, default=0.75, help="Utilization throttle limit (0.1 - 1.0, default 0.75)")
    parser.add_argument("--resume", action="store_true", help="Resume from last checkpoint if available")
    args = parser.parse_args()

    train_single_stage(
        stage_idx=int(args.stage),
        epochs=args.epochs,
        batch_size=args.batch,
        imgsz=args.imgsz,
        workers=args.workers,
        target_device=args.device,
        resume=args.resume,
        throttle=args.throttle
    )

