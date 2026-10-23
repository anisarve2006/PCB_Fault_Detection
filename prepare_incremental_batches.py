#!/usr/bin/env python3
"""
Board-Level Incremental Batch Splitter for PCB Defect Detection.
- Fixed Test Set: Board 09 (1,056 images, ~10%)
- Fixed Val Set:  Board 05 (948 images, ~9%)
- 5 Sequential Training Stages:
  Stage 1 (10%): Board 01 (1,000 images, 9.4%)
  Stage 2 (20%): Boards 01, 06 (2,016 images, 18.9%)
  Stage 3 (30%): Boards 01, 06, 07 (3,036 images, 28.5%)
  Stage 4 (40%): Boards 01, 06, 07, 12 (4,128 images, 38.7%)
  Stage 5 (50%): Boards 01, 06, 07, 12, 11 (5,268 images, 49.4%)
"""

import os
import re
from collections import defaultdict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATASET_DIR = BASE_DIR / "dataset"
SPLITS_DIR = BASE_DIR / "splits" / "incremental"

CLASSES = [
    "mouse_bite",
    "spur",
    "missing_hole",
    "short",
    "open_circuit",
    "spurious_copper",
]

DEFECTS_REGEX = r"(\d{2})_(?:missing_hole|mouse_bite|open_circuit|short|spurious_copper|spur)"

def parse_board_id(filename: str) -> str:
    m = re.search(DEFECTS_REGEX, filename)
    if m:
        return m.group(1)
    return "unknown"

def build_splits():
    SPLITS_DIR.mkdir(parents=True, exist_ok=True)
    img_exts = {".jpg", ".jpeg", ".png", ".bmp"}
    images = [p for p in DATASET_DIR.rglob("*") if p.suffix.lower() in img_exts]
    print(f"[+] Total images found: {len(images)}")
    
    board_groups = defaultdict(list)
    for p in images:
        b_id = parse_board_id(p.name)
        board_groups[b_id].append(p)
        
    for b_id in sorted(board_groups.keys()):
        print(f"  - Board {b_id}: {len(board_groups[b_id])} images")
        
    # Defined partitions:
    test_boards = ["09"]
    val_boards = ["05"]
    stage_additions = [
        ["01"],        # Stage 1: ~10% (1000)
        ["06"],        # Stage 2: +1016 -> ~2016 (20%)
        ["07"],        # Stage 3: +1020 -> ~3036 (30%)
        ["12"],        # Stage 4: +1092 -> ~4128 (40%)
        ["11"],        # Stage 5: +1140 -> ~5268 (50%)
    ]
    
    # Save Fixed Test Set
    test_imgs = [p for b in test_boards for p in board_groups[b]]
    test_txt = SPLITS_DIR / "test.txt"
    test_txt.write_text("\n".join(str(p.resolve()) for p in test_imgs), encoding="utf-8")
    print(f"\n[+] Fixed Test Set: {len(test_imgs)} images (Board {test_boards}) -> {test_txt.name}")
    
    # Save Fixed Val Set
    val_imgs = [p for b in val_boards for p in board_groups[b]]
    val_txt = SPLITS_DIR / "val.txt"
    val_txt.write_text("\n".join(str(p.resolve()) for p in val_imgs), encoding="utf-8")
    print(f"[+] Fixed Val Set:  {len(val_imgs)} images (Board {val_boards}) -> {val_txt.name}")
    
    # Build 5 Cumulative Training Stages
    accumulated_boards = []
    accumulated_imgs = []
    
    for stage_idx, extra_boards in enumerate(stage_additions, start=1):
        accumulated_boards.extend(extra_boards)
        stage_new_imgs = [p for b in extra_boards for p in board_groups[b]]
        accumulated_imgs.extend(stage_new_imgs)
        pct = stage_idx * 10
        
        train_txt = SPLITS_DIR / f"train_{pct}pct.txt"
        train_txt.write_text("\n".join(str(p.resolve()) for p in accumulated_imgs), encoding="utf-8")
        
        yaml_path = SPLITS_DIR / f"pcb_stage{stage_idx}_{pct}pct.yaml"
        yaml_content = f"""# PCB Defect Detection - Stage {stage_idx} ({pct}% Data)
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
        actual_pct = (len(accumulated_imgs) / len(images)) * 100
        print(f"[+] Stage {stage_idx} ({pct}% Target): {len(accumulated_imgs)} images ({actual_pct:.1f}% actual) | Boards: {accumulated_boards} -> {yaml_path.name}")
        
    print("\n[+] All incremental splits and YAML configs successfully generated.")

if __name__ == "__main__":
    build_splits()
