@echo off
title PCBVision AOI System - Phase 5
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
echo =================================================================
echo   PCBVision AOI - Quality Inspection System (Phase 5 Champion)
echo   Hardware Engine: NVIDIA RTX 4090 GPU (CUDA Enabled)
echo =================================================================
echo.
echo Launching UI at http://127.0.0.1:8000 ...
Z:\python.exe run_ui.py --host 127.0.0.1 --port 8000
pause
