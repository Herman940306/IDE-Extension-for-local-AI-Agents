# -------------------------------
# Start Backend + Ollama Automatically
# Complete startup automation
# Project Creator: Herman Swanepoel
# -------------------------------

Write-Host "🚀 Starting AI Agents Integration System..." -ForegroundColor Cyan
Write-Host "   Port: 8001" -ForegroundColor Gray
Write-Host "   Host: 127.0.0.1" -ForegroundColor Gray
Write-Host ""

# Navigate to project root
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

# Step 1: Start Ollama
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
Write-Host "📦 Step 1/2: Starting Ollama..." -ForegroundColor Yellow
& ".\run_ollama.ps1"

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to start Ollama" -ForegroundColor Red
    exit 1
}

# Wait for Ollama to be ready
Write-Host ""
Write-Host "⏳ Waiting for Ollama to be fully ready..." -ForegroundColor Gray
Start-Sleep -Seconds 3

# Step 2: Start FastAPI backend
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
Write-Host "🖥️  Step 2/2: Starting FastAPI Backend..." -ForegroundColor Yellow

$BackendDir = Join-Path $ProjectRoot "backend"
$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

# Verify Python exists
if (-not (Test-Path $PythonExe)) {
    Write-Host "❌ Python venv not found at: $PythonExe" -ForegroundColor Red
    exit 1
}

Write-Host "   Python: $PythonExe" -ForegroundColor Gray
Write-Host "   Working Dir: $BackendDir" -ForegroundColor Gray
Write-Host ""

# Start backend (foreground - see logs)
& $PythonExe -m uvicorn src.main:app --host 127.0.0.1 --port 8001

Write-Host ""
Write-Host "Backend stopped." -ForegroundColor Yellow
