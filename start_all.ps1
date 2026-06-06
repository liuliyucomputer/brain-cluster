# Brain Cluster - Start All (PowerShell)
# 右键 -> 使用 PowerShell 运行

$env:OPENAI_API_KEY = "sk-xGSsFRUlKUXduzjnwPK4m9J7eNmmVTRwraXROi0dhPiRTvP8"
$env:OPENAI_BASE_URL = "https://tokenshengsheng.com/v1"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Brain AI Cluster Starting..." -ForegroundColor Cyan
Write-Host "  ccswitch -> GPT-5.5" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# 1. Hermes Gateway
Write-Host "[1/4] Hermes Gateway (port 18789)..." -ForegroundColor Green
Start-Process cmd -ArgumentList "/c set OPENAI_API_KEY=$env:OPENAI_API_KEY && set OPENAI_BASE_URL=$env:OPENAI_BASE_URL && hermes gateway run" -WindowStyle Minimized
Start-Sleep -Seconds 2

# 2. StarOfficeUI
Write-Host "[2/4] StarOfficeUI (port 18791)..." -ForegroundColor Green
Start-Process cmd -ArgumentList "/c E:\Python3134\python.exe D:\brain\staroffice-ui\backend\app.py" -WindowStyle Minimized -WorkingDirectory "D:\brain\staroffice-ui\backend"
Start-Sleep -Seconds 2

# 3. Grafana
Write-Host "[3/4] Grafana (port 3001)..." -ForegroundColor Green
Start-Process cmd -ArgumentList "/c D:\brain\grafana\grafana-v11.6.0\bin\grafana-server.exe --config D:\brain\grafana\custom.ini" -WindowStyle Minimized -WorkingDirectory "D:\brain\grafana\grafana-v11.6.0"
Start-Sleep -Seconds 2

# 4. Dashboard
Write-Host "[4/4] Hermes Dashboard..." -ForegroundColor Green
Start-Process cmd -ArgumentList "/c hermes dashboard"

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  Cluster startup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "  Dashboard:  http://localhost:9119"
Write-Host "  StarOffice: http://localhost:18791"
Write-Host "  Grafana:    http://localhost:3001 (admin/admin)"
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Cron jobs:" -ForegroundColor Yellow
Write-Host "    Dreaming short:  every 4h (learner)"
Write-Host "    Dreaming medium: daily 02:00 (learner)"
Write-Host "    Dreaming long:   every Mon 03:00 (learner)"
Write-Host "    Health check:    every 5min (monitor)"
Write-Host ""

Read-Host "Press Enter to exit"
