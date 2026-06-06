@echo off
title Brain Cluster Setup
echo ========================================
echo   Brain AI Cluster - Environment Setup
echo ========================================
echo.

REM === Check Python ===
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Install Python 3.11+ from https://python.org
    pause
    exit /b 1
)
echo [OK] Python found: 
python --version
echo.

REM === Install Python dependencies ===
echo [1/5] Installing Python packages...
pip install flask waitress --quiet
if %errorlevel% neq 0 (
    echo [WARN] Some packages failed to install, trying without --quiet...
    pip install flask waitress
)
echo [OK] Python packages installed
echo.

REM === Create directories ===
echo [2/5] Creating directories...
if not exist "output\logs" mkdir output\logs
if not exist "output\logs\gateway" mkdir output\logs\gateway
if not exist "output\logs\staroffice" mkdir output\logs\staroffice
if not exist "output\logs\grafana" mkdir output\logs\grafana
if not exist "output\logs\agents" mkdir output\logs\agents
if not exist "output\memory\daily" mkdir output\memory\daily
if not exist "output\memory\weekly" mkdir output\memory\weekly
if not exist "output\memory\monthly" mkdir output\memory\monthly
if not exist "output\memory\vector" mkdir output\memory\vector
if not exist "output\reports" mkdir output\reports
echo [OK] Directories created
echo.

REM === Hermes Agent CLI ===
echo [3/5] Checking Hermes Agent CLI...
hermes --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Hermes Agent CLI not found. Install via:
    echo       pip install hermes-agent
    echo       OR manual install from https://github.com/hermes
) else (
    hermes --version
    echo [OK] Hermes Agent CLI ready
)
echo.

REM === Grafana (binary download) ===
echo [4/5] Checking Grafana...
if exist "grafana\grafana-v11.6.0\bin\grafana-server.exe" (
    echo [OK] Grafana v11.6.0 found
) else (
    echo [INFO] Grafana not found. Download manual:
    echo       1. Go to https://grafana.com/grafana/download
    echo       2. Download Windows v11.6.0 zip
    echo       3. Extract to: grafana\grafana-v11.6.0\
)
echo.

REM === External repos ===
echo [5/5] Checking external projects...
if exist "hermes-agent\pyproject.toml" (
    echo [OK] hermes-agent/ source found
) else (
    echo [INFO] Hermes Agent source not found. Clone with:
    echo       git clone ^<hermes-repo-url^> hermes-agent
)
if exist "openclaw\package.json" (
    echo [OK] openclaw/ source found
) else (
    echo [INFO] OpenClaw not found. Clone with:
    echo       git clone ^<openclaw-repo-url^> openclaw
)
if exist "staroffice-ui\backend\app.py" (
    echo [OK] staroffice-ui/ source found
) else (
    echo [INFO] StarOfficeUI not found. Get from your source.
)
echo.

echo ========================================
echo   Setup Complete!
echo.
echo   Start cluster: start_all.bat
echo   Monitor:       http://localhost:19996
echo ========================================
pause
