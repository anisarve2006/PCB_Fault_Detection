@echo off
title PCBVision AOI Launcher (Using Z: Drive Storage)
echo ============================================================
echo   Starting PCB Defect Inspection in Chrome (Z: Drive Storage)
echo ============================================================

set TEMP=Z:\tmp
set TMP=Z:\tmp
set PYTHONIOENCODING=utf-8

:: Check if server is running on port 8000
netstat -ano | findstr :8000 >nul
if %errorlevel% neq 0 (
    echo [*] Starting Python AOI backend on port 8000...
    start /min "PCBVision Backend" cmd /c "Z:\python.exe \"Z:\PCB fault Detection\Faulty PCB detection\Faulty PCB detection\run_ui.py\" --port 8000 --host 127.0.0.1"
    timeout /t 3 >nul
) else (
    echo [+] Server is already online on port 8000.
)

:: Launch Chrome configured with user-data and cache on Z: (bypassing full C: drive)
echo [*] Launching Google Chrome redirected to Z: drive...
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --user-data-dir="Z:\chrome_user_data" --disk-cache-dir="Z:\chrome_cache" --disable-gpu-shader-disk-cache http://127.0.0.1:8000/

echo [+] Opened http://127.0.0.1:8000 in Chrome!
