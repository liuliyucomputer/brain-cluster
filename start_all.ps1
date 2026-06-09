# Brain Cluster - Start All (PowerShell)
# 右键 -> 使用 PowerShell 运行

# Set working directory to script location
Set-Location $PSScriptRoot

# Load API Config
$endpointPath = Join-Path $PSScriptRoot "input\configs\ccswitch\endpoint.json"
$endpoint = Get-Content -Raw -Encoding UTF8 $endpointPath | ConvertFrom-Json
$env:OPENAI_API_KEY = $endpoint.api_key
$env:OPENAI_BASE_URL = $endpoint.base_url
$env:GATEWAY_ALLOW_ALL_USERS = "true"
$env:PYTHONIOENCODING = "utf-8"

$python = "python"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Brain AI Cluster Starting..." -ForegroundColor Cyan
Write-Host "  SiliconFlow -> DeepSeek-V4-Pro" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# 1. Hermes Gateway
Write-Host "[1/7] Hermes Gateway (port 18789)..." -ForegroundColor Green
$envBlock = "set OPENAI_API_KEY=$($env:OPENAI_API_KEY) && set OPENAI_BASE_URL=$($env:OPENAI_BASE_URL) && set GATEWAY_ALLOW_ALL_USERS=true && set PYTHONIOENCODING=utf-8 && hermes gateway run --replace"
Start-Process cmd -ArgumentList "/c $envBlock" -WindowStyle Minimized
Start-Sleep -Seconds 2

# 2. StarOfficeUI
Write-Host "[2/7] StarOfficeUI (port 18791)..." -ForegroundColor Green
$starofficePath = Join-Path $PSScriptRoot "staroffice-ui\backend\app.py"
Start-Process cmd -ArgumentList "/c $python $starofficePath" -WindowStyle Minimized -WorkingDirectory (Join-Path $PSScriptRoot "staroffice-ui\backend")
Start-Sleep -Seconds 2

# 3. Grafana
Write-Host "[3/7] Grafana (port 3001)..." -ForegroundColor Green
$grafanaBin = Join-Path $PSScriptRoot "grafana\grafana-v11.6.0\bin\grafana-server.exe"
$grafanaIni = Join-Path $PSScriptRoot "grafana\custom.ini"
$grafanaHome = Join-Path $PSScriptRoot "grafana\grafana-v11.6.0"
Start-Process cmd -ArgumentList "/c $grafanaBin --config $grafanaIni --homepath $grafanaHome" -WindowStyle Minimized -WorkingDirectory $grafanaHome
Start-Sleep -Seconds 2

# 4. Dashboard
Write-Host "[4/7] Hermes Dashboard..." -ForegroundColor Green
Start-Process cmd -ArgumentList "/c hermes dashboard" -WindowStyle Minimized
Start-Sleep -Seconds 1

# 5. Monitor Dashboard
Write-Host "[5/7] Monitor Dashboard (port 19997)..." -ForegroundColor Green
$monitorPath = Join-Path $PSScriptRoot "tools\monitor_dashboard.py"
Start-Process cmd -ArgumentList "/c $python $monitorPath" -WindowStyle Minimized -WorkingDirectory (Join-Path $PSScriptRoot "tools")
Start-Sleep -Seconds 1

# 6. Pipeline Orchestrator v2.0
Write-Host "[6/9] Pipeline Orchestrator v2.0 (3-round retry loop)..." -ForegroundColor Green
$orchPath = Join-Path $PSScriptRoot "tools\pipeline_orchestrator.py"
$orchEnv = "set OPENAI_API_KEY=$($env:OPENAI_API_KEY) && set OPENAI_BASE_URL=$($env:OPENAI_BASE_URL) && $python $orchPath --daemon"
Start-Process cmd -ArgumentList "/c $orchEnv" -WindowStyle Minimized -WorkingDirectory (Join-Path $PSScriptRoot "tools")
Start-Sleep -Seconds 1

# 7. Agent Watchdog
Write-Host "[7/9] Agent Watchdog (auto crash recovery)..." -ForegroundColor Green
$watchdogPath = Join-Path $PSScriptRoot "tools\watchdog.py"
Start-Process cmd -ArgumentList "/c $python $watchdogPath --daemon" -WindowStyle Minimized -WorkingDirectory (Join-Path $PSScriptRoot "tools")
Start-Sleep -Seconds 1

# 8. Checkpoint Manager
Write-Host "[8/9] Checkpoint Manager (5min snapshots)..." -ForegroundColor Green
$checkpointPath = Join-Path $PSScriptRoot "tools\checkpoint.py"
Start-Process cmd -ArgumentList "/c $python $checkpointPath --daemon" -WindowStyle Minimized -WorkingDirectory (Join-Path $PSScriptRoot "tools")
Start-Sleep -Seconds 1

# 9. Letta Memory Engine (placeholder)
Write-Host "[9/9] Letta Memory Engine (dB: letta\letta.db)" -ForegroundColor DarkGray
Write-Host "      Manual start: python letta\init_letta.py" -ForegroundColor DarkGray

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Cluster startup complete! (9 components, v2.0)" -ForegroundColor Green
Write-Host ""
Write-Host "  New Panel:      http://localhost:18791/dashboard-v2  [3D Live Monitor]" -ForegroundColor Yellow
Write-Host "  StarOffice:     http://localhost:18791" -ForegroundColor White
Write-Host "  Gateway:        http://localhost:18789" -ForegroundColor White
Write-Host "  Kanban:         http://localhost:9119" -ForegroundColor White
Write-Host "  Grafana:        http://localhost:3001 (admin/admin)" -ForegroundColor White
Write-Host "  Monitor:        http://localhost:19997" -ForegroundColor White
Write-Host ""
Write-Host "  v2.0 New:" -ForegroundColor Yellow
Write-Host "    Watchdog:      30s auto-recovery" -ForegroundColor DarkYellow
Write-Host "    Orchestrator:  3-round retry loop" -ForegroundColor DarkYellow
Write-Host "    Checkpoint:    5min state snapshots" -ForegroundColor DarkYellow
Write-Host "============================================" -ForegroundColor Cyan

# Auto-open dashboard
Start-Sleep -Seconds 5
Start-Process "http://localhost:18791/dashboard-v2"
Write-Host ""
Write-Host "  Auto-healing components:" -ForegroundColor Yellow
Write-Host "    Watchdog:      Agent crash -> 30s auto-restart"
Write-Host "    Orchestrator:  Task FAIL -> 3-round progressive retry"
Write-Host "    Checkpoint:    System crash -> resume from snapshot"
Write-Host ""
Write-Host "  Cron jobs (managed by Hermes):" -ForegroundColor Yellow
Write-Host "    Dreaming short:  every 4h (learner)"
Write-Host "    Dreaming medium: daily 02:00 (learner)"
Write-Host "    Dreaming long:   every Mon 03:00 (learner)"
Write-Host "    Health check:    every 5min (monitor)"
Write-Host ""

Read-Host "Press Enter to exit"
