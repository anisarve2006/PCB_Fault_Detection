#!/usr/bin/env python3
"""
Live Terminal Monitor for Active PCB Defect Stage 4 Incremental Training.
Streams GPU metrics, real-time power, temperature, and epoch progress.
"""

import os
import sys
import time
from pathlib import Path

LOG_FILE = Path(r"C:\Users\24102A0044\.gemini\antigravity-ide\brain\70fab9bf-8720-4046-8e04-c9d3b922ef76\.system_generated\tasks\task-90.log")
RESULTS_CSV = Path(__file__).resolve().parent / "runs" / "incremental_training" / "Stage_4_60pct" / "results.csv"

def tail_f(file_path):
    print("=" * 70)
    print("  🚀 PCB DEFECT STAGE 4 TRAINING - LIVE TERMINAL MONITOR (75% CAP)")
    print("=" * 70)
    print(f"[*] Streaming live from: {file_path}")
    print("[*] Press Ctrl+C at any time to exit monitor (training continues unaffected)\n")

    if not file_path.exists():
        print(f"[!] Log file not found at: {file_path}")
        return

    # Print the last 40 lines first
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
        for line in lines[-40:]:
            sys.stdout.write(line)
        sys.stdout.flush()

        # Continuous tailing
        while True:
            line = f.readline()
            if line:
                sys.stdout.write(line)
                sys.stdout.flush()
            else:
                time.sleep(0.4)

if __name__ == "__main__":
    try:
        tail_f(LOG_FILE)
    except KeyboardInterrupt:
        print("\n\n[+] Exited monitor. Training is still running safely in the background.")
