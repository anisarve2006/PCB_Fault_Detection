#!/usr/bin/env python3
"""
PCB Defect Detection & Measurement AOI Web Backend
FastAPI server providing real-time inference, physical dimension measurement,
IPC-A-610 quality triage, and incremental training metrics.
"""

import io
import os
import tempfile
import time
from pathlib import Path
from typing import Optional, List, Dict, Any

# Ensure all temporary spooling/uploads go to Z:\tmp because C:\ has 0 bytes free
os.makedirs("Z:\\tmp", exist_ok=True)
os.environ["TEMP"] = "Z:\\tmp"
os.environ["TMP"] = "Z:\\tmp"
os.environ["YOLO_CONFIG_DIR"] = "Z:\\ultralytics_config"
tempfile.tempdir = "Z:\\tmp"

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image
import pandas as pd
import torch
from ultralytics import YOLO

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "app" / "static"
DATASET_DIR = BASE_DIR / "dataset"
RUNS_DIR = BASE_DIR / "runs" / "incremental_training"

app = FastAPI(title="PCBVision AOI System", version="1.0.0")

# Cached models dictionary
LOADED_MODELS: Dict[str, YOLO] = {}

CLASSES = [
    "mouse_bite",
    "spur",
    "missing_hole",
    "short",
    "open_circuit",
    "spurious_copper",
]

CLASS_COLORS = {
    "missing_hole": "#EAB308",     # Gold / Amber
    "mouse_bite": "#A855F7",       # Purple
    "open_circuit": "#EF4444",     # Crimson Red (Critical)
    "short": "#F43F5E",            # Neon Pink / Red (Critical)
    "spur": "#06B6D4",             # Cyan / Teal
    "spurious_copper": "#F97316",   # Orange
    "multi": "#8B5CF6",            # Violet / Multi-defect
}

CLASS_SEVERITY = {
    "short": "CRITICAL",
    "open_circuit": "CRITICAL",
    "missing_hole": "MAJOR",
    "mouse_bite": "MINOR",
    "spur": "MINOR",
    "spurious_copper": "MINOR",
    "multi": "CRITICAL",
}

SAMPLE_IMAGES = {
    "all_defects_panel": {
        "id": "all_defects_panel",
        "name": "Full Multi-Defect Panel (All 6 Classes Concurrently)",
        "class": "multi",
        "severity": "CRITICAL",
        "description": "Composite inspection panel with Short, Open Circuit, Missing Hole, Spur, Mouse Bite & Spurious Copper all detected at once.",
        "path": DATASET_DIR / "samples" / "full_multidefect_panel_all6.jpg",
    },
    "critical_dual_fault": {
        "id": "critical_dual_fault",
        "name": "Dual Critical Faults (Short + Open Circuit Concurrently)",
        "class": "multi",
        "severity": "CRITICAL",
        "description": "Simultaneous catastrophic electrical defects: conductor bridge (short) and broken trace (open circuit) together.",
        "path": DATASET_DIR / "samples" / "critical_dual_fault_pcb.jpg",
    },
    "structural_geometric": {
        "id": "structural_geometric",
        "name": "Multi-Defect Geometry (Via + Mouse Bite + Spur)",
        "class": "multi",
        "severity": "MAJOR",
        "description": "Multiple structural flaws: blocked via hole, conductor edge mouse bite, and copper spur whisker together.",
        "path": DATASET_DIR / "samples" / "structural_geometric_multidefect.jpg",
    },
    "copper_isolation": {
        "id": "copper_isolation",
        "name": "Conductor & Copper Cluster (Short + Spur + Stray Copper)",
        "class": "multi",
        "severity": "CRITICAL",
        "description": "Multiple etching/isolation failures: short circuit, spur protrusion, and stray spurious copper particles at once.",
        "path": DATASET_DIR / "samples" / "copper_isolation_multidefect.jpg",
    },
    "missing_hole": {
        "id": "missing_hole",
        "name": "Missing / Blocked Via Hole",
        "class": "missing_hole",
        "severity": "MAJOR",
        "description": "Drill hole completely missing or blocked by resin/solder mask.",
        "path": DATASET_DIR / "pcb-defect-dataset" / "val" / "images" / "light_01_missing_hole_02_2_600.jpg",
    },
    "mouse_bite": {
        "id": "mouse_bite",
        "name": "Trace Edge Mouse Bite",
        "class": "mouse_bite",
        "severity": "MINOR",
        "description": "Crescent-shaped copper erosion nicks along conductor trace edge.",
        "path": DATASET_DIR / "pcb-defect-dataset" / "val" / "images" / "light_01_mouse_bite_02_2_600.jpg",
    },
    "open_circuit": {
        "id": "open_circuit",
        "name": "Open Circuit (Broken Trace)",
        "class": "open_circuit",
        "severity": "CRITICAL",
        "description": "Total electrical discontinuity across conductor path.",
        "path": DATASET_DIR / "pcb-defect-dataset" / "val" / "images" / "light_01_open_circuit_12_2_600.jpg",
    },
    "short": {
        "id": "short",
        "name": "Short Circuit (Trace Bridge)",
        "class": "short",
        "severity": "CRITICAL",
        "description": "Accidental conductive copper bridge connecting two separate traces.",
        "path": DATASET_DIR / "pcb-defect-dataset" / "val" / "images" / "light_01_short_02_1_600.jpg",
    },
    "spur": {
        "id": "spur",
        "name": "Copper Spur Protrusion",
        "class": "spur",
        "severity": "MINOR",
        "description": "Thin, sharp copper whisker projecting outward from trace edge.",
        "path": DATASET_DIR / "pcb-defect-dataset" / "val" / "images" / "light_01_spur_06_1_600.jpg",
    },
    "spurious_copper": {
        "id": "spurious_copper",
        "name": "Spurious Copper Residue",
        "class": "spurious_copper",
        "severity": "MINOR",
        "description": "Isolated stray copper dots or islands left un-etched on substrate.",
        "path": DATASET_DIR / "pcb-defect-dataset" / "val" / "images" / "light_01_spurious_copper_01_1_600.jpg",
    },
}

def resolve_model_path(model_key: str = "champion") -> Path:
    """Find the best available model checkpoint."""
    if model_key == "stage5":
        p = RUNS_DIR / "Stage_5_100pct" / "weights" / "best.pt"
        if p.exists(): return p
        p2 = BASE_DIR / "champion_weights_stage5.pt"
        if p2.exists(): return p2
    elif model_key == "stage4":
        p = RUNS_DIR / "Stage_4_60pct" / "weights" / "best.pt"
        if p.exists(): return p
        p2 = BASE_DIR / "champion_weights_stage4.pt"
        if p2.exists(): return p2
    elif model_key == "stage3":
        p = RUNS_DIR / "Stage_3_30pct" / "weights" / "best.pt"
        if p.exists(): return p
    elif model_key == "stage2":
        p = RUNS_DIR / "Stage_2_20pct" / "weights" / "best.pt"
        if p.exists(): return p
    elif model_key == "stage1":
        p = RUNS_DIR / "Stage_1_10pct" / "weights" / "best.pt"
        if p.exists(): return p

    # Default to champion_weights.pt or latest available (Phase 5)
    root_champ = BASE_DIR / "champion_weights.pt"
    if root_champ.exists():
        return root_champ

    for s in ["Stage_5_100pct", "Stage_4_60pct", "Stage_3_30pct", "Stage_2_20pct", "Stage_1_10pct"]:
        candidate = RUNS_DIR / s / "weights" / "best.pt"
        if candidate.exists():
            return candidate

    return BASE_DIR / "yolo11s.pt"

def get_yolo(model_key: str = "champion") -> YOLO:
    path = resolve_model_path(model_key)
    path_str = str(path.resolve())
    if path_str not in LOADED_MODELS:
        print(f"[*] Loading model into cache: {path.name} ({path})")
        LOADED_MODELS[path_str] = YOLO(path_str)
    return LOADED_MODELS[path_str]

@app.get("/api/status")
def get_system_status():
    """Return model inventory and active training stage."""
    active_path = resolve_model_path("champion")
    
    models_available = []
    if (BASE_DIR / "champion_weights.pt").exists():
        models_available.append({"id": "champion", "name": "Phase 5 Champion (Stage 5 - 98.81% mAP@50)", "active": True})
    if (RUNS_DIR / "Stage_5_100pct" / "weights" / "best.pt").exists() or (BASE_DIR / "champion_weights_stage5.pt").exists():
        models_available.append({"id": "stage5", "name": "Stage 5 Model (100% Data - 98.81% mAP@50)", "active": False})
    if (RUNS_DIR / "Stage_4_60pct" / "weights" / "best.pt").exists() or (BASE_DIR / "champion_weights_stage4.pt").exists():
        models_available.append({"id": "stage4", "name": "Stage 4 Model (60% Data - 96.86% mAP@50)", "active": False})
    if (RUNS_DIR / "Stage_3_30pct" / "weights" / "best.pt").exists():
        models_available.append({"id": "stage3", "name": "Stage 3 Model (30% Data - 95.27% mAP@50)", "active": False})
    if (RUNS_DIR / "Stage_2_20pct" / "weights" / "best.pt").exists():
        models_available.append({"id": "stage2", "name": "Stage 2 Model (20% Data - 92.96% mAP@50)", "active": False})
    if (RUNS_DIR / "Stage_1_10pct" / "weights" / "best.pt").exists():
        models_available.append({"id": "stage1", "name": "Stage 1 Model (10% Data - 79.24% mAP@50)", "active": False})

    hw_desc = "NVIDIA GeForce RTX 4090 (24GB VRAM)" if (torch.cuda.is_available() and "4090" in torch.cuda.get_device_name(0)) else (torch.cuda.get_device_name(0) if torch.cuda.is_available() else "Intel i7 CPU (AVX2 / oneDNN)")

    return {
        "status": "online",
        "active_model": "Phase 5 Champion (98.81% mAP@50)",
        "active_model_full": str(active_path),
        "stage_complete": "Stage 5 (100% Data - 98.81% mAP@50)",
        "hardware": hw_desc,
        "stage3_in_training": False,
        "stage4_in_training": False,
        "stage5_in_training": False,
        "models_available": models_available,
        "classes": CLASSES,
        "colors": CLASS_COLORS,
        "severities": CLASS_SEVERITY
    }

@app.get("/api/samples")
def list_samples():
    """Return list of pre-configured sample defective PCB images."""
    out = []
    for k, v in SAMPLE_IMAGES.items():
        out.append({
            "id": v["id"],
            "name": v["name"],
            "class": v["class"],
            "severity": v["severity"],
            "description": v["description"],
            "available": v["path"].exists()
        })
    return out

@app.get("/api/samples/{sample_id}/image")
def get_sample_image(sample_id: str):
    """Serve sample image file."""
    if sample_id not in SAMPLE_IMAGES:
        raise HTTPException(status_code=404, detail="Sample not found")
    path = SAMPLE_IMAGES[sample_id]["path"]
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Image file missing on disk: {path}")
    return FileResponse(str(path), media_type="image/jpeg")

@app.get("/api/metrics")
def get_incremental_metrics():
    """Return historical performance data across training stages."""
    csv_path = RUNS_DIR / "incremental_metrics_summary.csv"
    if not csv_path.exists():
        return {"stages": []}
    df = pd.read_csv(csv_path)
    return {"stages": df.to_dict(orient="records")}

@app.post("/api/detect")
async def detect_pcb(
    file: Optional[UploadFile] = File(None),
    sample_id: Optional[str] = Form(None),
    confidence: float = Form(0.35),
    iou: float = Form(0.45),
    scale_um: float = Form(15.0), # Microns per pixel
    model_choice: str = Form("champion")
):
    """
    Run object detection, compute bounding boxes, calculate physical micron measurements,
    and evaluate IPC-A-610 standards compliance.
    """
    # 1. Load Image
    if file and file.filename:
        content = await file.read()
        image = Image.open(io.BytesIO(content)).convert("RGB")
        img_name = file.filename
    elif sample_id and sample_id in SAMPLE_IMAGES:
        sample_path = SAMPLE_IMAGES[sample_id]["path"]
        if not sample_path.exists():
            raise HTTPException(status_code=404, detail="Sample image not found on disk")
        image = Image.open(sample_path).convert("RGB")
        img_name = sample_path.name
    else:
        raise HTTPException(status_code=400, detail="Must provide an image upload or valid sample_id")

    img_w, img_h = image.size

    # 2. Run Inference with dynamic multi-resolution scaling
    model = get_yolo(model_choice)
    t0 = time.time()
    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    # Auto-scale imgsz up to 1280 for high-res/composite boards so all defect types are resolved at once
    max_dim = max(img_w, img_h)
    dynamic_imgsz = 1280 if max_dim >= 1000 else (960 if max_dim >= 700 else 640)
    
    results = model.predict(
        image,
        conf=confidence,
        iou=iou,
        device=device,
        imgsz=dynamic_imgsz,
        verbose=False
    )[0]
    inference_time_ms = round((time.time() - t0) * 1000, 2)

    # 3. Extract and Measure Defects
    detections = []
    has_critical = False
    has_major = False
    has_minor = False

    for box in results.boxes:
        cls_idx = int(box.cls[0].item())
        cls_name = results.names[cls_idx]
        conf_score = float(box.conf[0].item())
        
        xyxy = box.xyxy[0].cpu().numpy().tolist()
        x1, y1, x2, y2 = xyxy
        
        w_px = max(1.0, x2 - x1)
        h_px = max(1.0, y2 - y1)
        area_px = w_px * h_px
        
        # Physical calibrated measurements in microns (um)
        w_um = round(w_px * scale_um, 2)
        h_um = round(h_px * scale_um, 2)
        area_um2 = round(area_px * (scale_um ** 2), 2)
        
        severity = CLASS_SEVERITY.get(cls_name, "MINOR")
        if severity == "CRITICAL": has_critical = True
        elif severity == "MAJOR": has_major = True
        elif severity == "MINOR": has_minor = True

        # Defect-specific diagnostic measurements
        diag_value = ""
        diag_label = ""
        ipc_violation = ""

        if cls_name == "open_circuit":
            gap_um = round(min(w_um, h_um), 2)
            diag_label = "Trace Break Gap"
            diag_value = f"{gap_um} µm"
            ipc_violation = "IPC Class 1/2/3 Total Discontinuity Failure"
        elif cls_name == "short":
            bridge_um = round(min(w_um, h_um), 2)
            diag_label = "Bridge Conductor Width"
            diag_value = f"{bridge_um} µm"
            ipc_violation = "IPC Class 1/2/3 Spacing Violation (Short Circuit)"
        elif cls_name == "spur":
            protrusion_um = round(max(w_um, h_um), 2)
            diag_label = "Protrusion Length"
            diag_value = f"{protrusion_um} µm"
            ipc_violation = "Potential dielectric clearance reduction"
        elif cls_name == "mouse_bite":
            nick_depth_um = round(min(w_um, h_um), 2)
            diag_label = "Edge Notch Depth"
            diag_value = f"{nick_depth_um} µm"
            ipc_violation = "Check remaining conductor width (>= 70% required)"
        elif cls_name == "missing_hole":
            hole_diam_um = round((w_um + h_um) / 2.0, 2)
            diag_label = "Via / Hole Span"
            diag_value = f"{hole_diam_um} µm"
            ipc_violation = "Component pin insertion / interlayer via blocked"
        elif cls_name == "spurious_copper":
            diag_label = "Particle Surface Area"
            diag_value = f"{area_um2} µm²"
            ipc_violation = "Residual copper isolation hazard"

        detections.append({
            "class_id": cls_idx,
            "class_name": cls_name,
            "confidence": round(conf_score * 100, 2),
            "severity": severity,
            "color": CLASS_COLORS.get(cls_name, "#3B82F6"),
            "bbox": {
                "x1": round(x1, 1),
                "y1": round(y1, 1),
                "x2": round(x2, 1),
                "y2": round(y2, 1),
                "width_px": round(w_px, 1),
                "height_px": round(h_px, 1),
                "area_px": round(area_px, 1)
            },
            "physical": {
                "width_um": w_um,
                "height_um": h_um,
                "area_um2": area_um2,
                "scale_um_per_px": scale_um
            },
            "diagnostic": {
                "label": diag_label,
                "value": diag_value,
                "ipc_rule": ipc_violation
            }
        })

    # Overall Quality Verdict
    if len(detections) == 0:
        verdict = "PASS"
        verdict_badge = "QUALITY APPROVED"
        verdict_color = "#10B981" # Green
        verdict_desc = "No manufacturing defects detected. Board complies with visual inspection criteria."
    elif has_critical:
        verdict = "REJECT"
        verdict_badge = "CRITICAL REJECT"
        verdict_color = "#EF4444" # Red
        verdict_desc = "Board contains catastrophic electrical flaws (Short or Open Circuit). Routing to scrap/repair station."
    elif has_major:
        verdict = "REJECT"
        verdict_badge = "MAJOR DEFECT"
        verdict_color = "#F59E0B" # Amber
        verdict_desc = "Blocked or missing vias detected. Secondary drilling or manual rework required."
    else:
        verdict = "REVIEW"
        verdict_badge = "OPERATOR REVIEW"
        verdict_color = "#3B82F6" # Blue
        verdict_desc = "Minor cosmetic or non-fatal copper imperfections found. Verify IPC clearance limits."

    distinct_classes = list(dict.fromkeys(d["class_name"] for d in detections))
    class_breakdown = {c: sum(1 for d in detections if d["class_name"] == c) for c in distinct_classes}

    return {
        "image_name": img_name,
        "image_dimensions": {"width": img_w, "height": img_h},
        "model_used": Path(str(model.model.pt_path if hasattr(model.model, 'pt_path') else model_choice)).name,
        "inference_time_ms": inference_time_ms,
        "verdict": verdict,
        "verdict_badge": verdict_badge,
        "verdict_color": verdict_color,
        "verdict_description": verdict_desc,
        "distinct_classes": distinct_classes,
        "class_breakdown": class_breakdown,
        "summary": {
            "total_defects": len(detections),
            "distinct_classes_count": len(distinct_classes),
            "critical_count": sum(1 for d in detections if d["severity"] == "CRITICAL"),
            "major_count": sum(1 for d in detections if d["severity"] == "MAJOR"),
            "minor_count": sum(1 for d in detections if d["severity"] == "MINOR"),
        },
        "detections": detections
    }

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/")
def index():
    index_file = STATIC_DIR / "index.html"
    return HTMLResponse(content=index_file.read_text(encoding="utf-8"))

if __name__ == "__main__":
    import uvicorn
    print("[*] Launching PCBVision AOI Server at http://127.0.0.1:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000)
