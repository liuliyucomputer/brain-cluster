@echo off
title Brain Cluster - Start All
cd /d "%~dp0"

REM === Load API Config (use %CD% to avoid trailing backslash in Python string) ===
set "BRAIN_ROOT=%CD%"
for /f "delims=" %%i in ('python -c "import json;c=json.load(open(r'%BRAIN_ROOT%\input\configs\ccswitch\endpoint.json','r',encoding='utf-8'));print(c.get('api_key',''))"') do set OPENAI_API_KEY=%%i
for /f "delims=" %%i in ('python -c "import json;c=json.load(open(r'%BRAIN_ROOT%\input\configs\ccswitch\endpoint.json','r',encoding='utf-8'));print(c.get('base_url','https://api.siliconflow.cn/v1'))"') do set OPENAI_BASE_URL=%%i

if "%OPENAI_API_KEY%"=="" (
    echo [WARN] Could not load API key, trying siliconflow fallback...
    for /f "delims=" %%i in ('python -c "import json;c=json.load(open(r'%BRAIN_ROOT%\input\configs\siliconflow\endpoint.json','r',encoding='utf-8'));print(c.get('api_key',''))"') do set OPENAI_API_KEY=%%i
    for /f "delims=" %%i in ('python -c "import json;c=json.load(open(r'%BRAIN_ROOT%\input\configs\siliconflow\endpoint.json','r',encoding='utf-8'));print(c.get('base_url','https://api.siliconflow.cn/v1'))"') do set OPENAI_BASE_URL=%%i
)
if "%OPENAI_API_KEY%"=="" (
    echo [WARN] Still no API key found, falling back to environment variable
)

set GATEWAY_ALLOW_ALL_USERS=true
set PYTHONIOENCODING=utf-8

REM === Date fix (CN Windows: 2026/06/06 -> 2026-06-06) ===
set LOG_DATE=%date:~0,10%
set LOG_DATE=%LOG_DATE:/=-%

REM === Create log dirs ===
if not exist "output\logs\gateway" mkdir output\logs\gateway
if not exist "output\logs\staroffice" mkdir output\logs\staroffice
if not exist "output\logs\grafana" mkdir output\logs\grafana
if not exist "output\logs\orchestrator" mkdir output\logs\orchestrator
if not exist "output\logs\agents" mkdir output\logs\agents
if not exist "output\logs\watchdog" mkdir output\logs\watchdog
if not exist "output\logs\supreme_commander" mkdir output\logs\supreme_commander

echo ============================================
echo   Brain AI Cluster Starting... %date% %time%
echo   SiliconFlow - DeepSeek-V4-Pro
echo   Logs: output\logs\
echo ============================================
echo.

REM === 1. Hermes Gateway (port 18789) ===
echo [1/7] Hermes Gateway (port 18789)
start "Brain-Gateway" /MIN cmd /c "set OPENAI_API_KEY=%OPENAI_API_KEY% && set OPENAI_BASE_URL=%OPENAI_BASE_URL% && set GATEWAY_ALLOW_ALL_USERS=true && set PYTHONIOENCODING=utf-8 && hermes gateway run --replace > output\logs\gateway\%LOG_DATE%.log 2>&1"
echo   Gateway launched
echo.

REM === 2. StarOfficeUI (port 18791) ===
echo [2/7] StarOfficeUI (port 18791)
start "Brain-StarUI" /MIN cmd /c "python staroffice-ui\backend\app.py > output\logs\staroffice\%LOG_DATE%.log 2>&1"
echo   StarOfficeUI launched
echo.

REM === 3. Grafana (port 3001) ===
echo [3/7] Grafana (port 3001)
start "Brain-Grafana" /MIN cmd /c "grafana\grafana-v11.6.0\bin\grafana-server.exe --config grafana\custom.ini --homepath grafana\grafana-v11.6.0 > output\logs\grafana\%LOG_DATE%.log 2>&1"
echo   Grafana launched
echo.

REM === 4. Hermes Dashboard (port 9119) ===
echo [4/7] Hermes Dashboard (port 9119)
start "Brain-Dashboard" /MIN cmd /c "hermes dashboard > output\logs\gateway\dashboard_%LOG_DATE%.log 2>&1"
echo   Dashboard launched
echo.

REM === 5. Monitor Dashboard (port 19997) ===
echo [5/7] Monitor Dashboard (port 19997)
start "Brain-Monitor" /MIN cmd /c "python tools\monitor_dashboard.py > output\logs\gateway\monitor_%LOG_DATE%.log 2>&1"
echo   Monitor launched
echo.

REM === 6. Pipeline Orchestrator v2.0 ===
echo [6/9] Pipeline Orchestrator v2.0 (3-round retry loop)
start "Brain-Orch" /MIN cmd /c "set OPENAI_API_KEY=%OPENAI_API_KEY% && set OPENAI_BASE_URL=%OPENAI_BASE_URL% && python tools\pipeline_orchestrator.py --daemon > output\logs\orchestrator\%LOG_DATE%.log 2>&1"
echo   Orchestrator launched (30s poll, max 3 retries)
echo.

REM === 7. Agent Watchdog ===
echo [7/9] Agent Watchdog (auto crash recovery)
start "Brain-Watchdog" /MIN cmd /c "python tools\watchdog.py --daemon > output\logs\watchdog\watchdog.log 2>&1"
echo   Watchdog launched (30s poll)
echo.

REM === 8. Checkpoint Manager ===
echo [8/9] Checkpoint Manager (5min snapshots)
start "Brain-Checkpoint" /MIN cmd /c "python tools\checkpoint.py --daemon > output\logs\checkpoint.log 2>&1"
echo   Checkpoint launched (5min interval)
echo.

REM === 9. Supreme Commander (v3.0) ===
echo [9/9] Supreme Commander v3.0 (Global Controller)
start "Brain-Commander" /MIN cmd /c "python tools\supreme_commander.py --start > output\logs\supreme_commander\%LOG_DATE%.log 2>&1"
echo   Supreme Commander launched (auto-scan, auto-fix, global coordination)
echo.

echo ============================================
echo   Cluster startup complete! (9 components, v3.0)
echo.
echo   New Panel:      http://localhost:18791/dashboard-v2
echo   StarOffice:     http://localhost:18791
echo   Gateway:        http://localhost:18789
echo   Kanban:         http://localhost:9119
echo   Grafana:        http://localhost:3001
echo   Monitor:        http://localhost:19997
echo.
echo   v3.0 New:
echo     Supreme Commander:  Auto-scan, auto-fix, global coordination
echo     Watchdog:           30s auto-recovery
echo     Orchestrator:       3-round retry loop
echo     Checkpoint:         5min state snapshots
echo.
echo   Logs: output\logs\
echo ============================================

REM === Auto-open dashboard ===
timeout /t 5 /nobreak >nul
start http://localhost:18791/dashboard-v2

pause
