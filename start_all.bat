@echo off
title Brain Cluster - Start All

REM === API Config ===
set OPENAI_API_KEY=sk-xGSsFRUlKUXduzjnwPK4m9J7eNmmVTRwraXROi0dhPiRTvP8
set OPENAI_BASE_URL=https://tokenshengsheng.com/v1
set GATEWAY_ALLOW_ALL_USERS=true
set PYTHONIOENCODING=utf-8

REM === Date fix (CN Windows: 2026/06/06 -> 2026-06-06) ===
set LOG_DATE=%date:~0,10%
set LOG_DATE=%LOG_DATE:/=-%

REM === Create log dirs ===
if not exist "D:\brain\output\logs\gateway" mkdir D:\brain\output\logs\gateway
if not exist "D:\brain\output\logs\staroffice" mkdir D:\brain\output\logs\staroffice
if not exist "D:\brain\output\logs\grafana" mkdir D:\brain\output\logs\grafana
if not exist "D:\brain\output\logs\agents" mkdir D:\brain\output\logs\agents

echo ============================================
echo   Brain AI Cluster Starting... %date% %time%
echo   ccswitch - GPT-5.5
echo   Logs: D:\brain\output\logs\
echo ============================================
echo.

REM === 1. Hermes Gateway (port 18789) ===
echo [1/5] Hermes Gateway (port 18789)
start "Brain-Gateway" cmd /c "set OPENAI_API_KEY=sk-xGSsFRUlKUXduzjnwPK4m9J7eNmmVTRwraXROi0dhPiRTvP8 && set OPENAI_BASE_URL=https://tokenshengsheng.com/v1 && set GATEWAY_ALLOW_ALL_USERS=true && set PYTHONIOENCODING=utf-8 && hermes gateway run > D:\brain\output\logs\gateway\%LOG_DATE%.log 2>&1"
echo   Gateway launched in background
echo.

REM === 2. StarOfficeUI (port 18791) ===
echo [2/5] StarOfficeUI (port 18791)
start "Brain-StarUI" cmd /c "E:\Python3134\python.exe D:\brain\staroffice-ui\backend\app.py > D:\brain\output\logs\staroffice\%LOG_DATE%.log 2>&1"
echo   StarOfficeUI launched in background
echo.

REM === 3. Grafana (port 3001) ===
echo [3/5] Grafana (port 3001)
start "Brain-Grafana" cmd /c "cd /d D:\brain\grafana\grafana-v11.6.0 && bin\grafana-server.exe --config D:\brain\grafana\custom.ini --homepath D:\brain\grafana\grafana-v11.6.0 > D:\brain\output\logs\grafana\%LOG_DATE%.log 2>&1"
echo   Grafana launched in background
echo.

REM === 4. Hermes Dashboard (port 9119) ===
echo [4/5] Hermes Dashboard (port 9119)
start "Brain-Dashboard" cmd /c "hermes dashboard"
echo   Dashboard launched in background
echo.

REM === 5. Monitor Dashboard (port 19998) ===
echo [5/5] Monitor Dashboard (port 19998)
start "Brain-Monitor" cmd /c "E:\Python3134\python.exe D:\brain\tools\monitor_dashboard.py"
echo   Monitor launched in background
echo.

echo ============================================
echo   Cluster startup complete!
echo.
echo   Monitor Board:   http://localhost:19996
echo   Dashboard:       http://localhost:9119
echo   StarOffice:      http://localhost:18791
echo   Grafana:         http://localhost:3001 (admin/admin)
echo.
echo   Logs: D:\brain\output\logs\
echo ============================================
echo.
pause
