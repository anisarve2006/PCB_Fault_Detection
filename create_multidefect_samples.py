#!/usr/bin/env python3
"""
Generate multi-defect composite PCB boards containing multiple distinct defect types
simultaneously (e.g. All 6 IPC classes concurrently on one single board).
"""

from pathlib import Path
import cv2
import numpy as np

def create_samples():
    base_dir = Path(__file__).resolve().parent
    val_dir = base_dir / "dataset" / "pcb-defect-dataset" / "val" / "images"
    samples_dir = base_dir / "dataset" / "samples"
    samples_dir.mkdir(parents=True, exist_ok=True)

    # Load high-quality examples of each class
    sh = cv2.imread(str(val_dir / "light_01_short_02_1_600.jpg"))
    oc = cv2.imread(str(val_dir / "light_01_open_circuit_12_2_600.jpg"))
    mh = cv2.imread(str(val_dir / "light_01_missing_hole_02_2_600.jpg"))
    sp = cv2.imread(str(val_dir / "light_01_spur_06_1_600.jpg"))
    mb = cv2.imread(str(val_dir / "light_01_mouse_bite_02_2_600.jpg"))
    sc = cv2.imread(str(val_dir / "light_01_spurious_copper_01_1_600.jpg"))

    # 1. Full Multi-Defect Panel (All 6 Classes Concurrently)
    # 2 rows x 3 columns: 1800 x 1200 px
    row1 = np.hstack([sh, oc, mh])
    row2 = np.hstack([sp, mb, sc])
    panel_all6 = np.vstack([row1, row2])
    cv2.imwrite(str(samples_dir / "full_multidefect_panel_all6.jpg"), panel_all6)
    print(f"[+] Created {samples_dir / 'full_multidefect_panel_all6.jpg'} ({panel_all6.shape[1]}x{panel_all6.shape[0]})")

    # 2. Critical Electrical Faults Board (Short + Open Circuit Concurrently)
    # 1200 x 600 px
    dual_crit = np.hstack([sh, oc])
    cv2.imwrite(str(samples_dir / "critical_dual_fault_pcb.jpg"), dual_crit)
    print(f"[+] Created {samples_dir / 'critical_dual_fault_pcb.jpg'} ({dual_crit.shape[1]}x{dual_crit.shape[0]})")

    # 3. Structural & Geometric Faults Board (Missing Via + Mouse Bite + Spur Concurrently)
    # 1800 x 600 px
    geo_faults = np.hstack([mh, mb, sp])
    cv2.imwrite(str(samples_dir / "structural_geometric_multidefect.jpg"), geo_faults)
    print(f"[+] Created {samples_dir / 'structural_geometric_multidefect.jpg'} ({geo_faults.shape[1]}x{geo_faults.shape[0]})")

    # 4. Stray Conductor & Copper Faults (Short + Spurious Copper + Spur)
    copper_faults = np.hstack([sh, sc, sp])
    cv2.imwrite(str(samples_dir / "copper_isolation_multidefect.jpg"), copper_faults)
    print(f"[+] Created {samples_dir / 'copper_isolation_multidefect.jpg'} ({copper_faults.shape[1]}x{copper_faults.shape[0]})")

if __name__ == "__main__":
    create_samples()
