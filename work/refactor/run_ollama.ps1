# -------------------------------
# Starts Ollama server from project folder
# Uses local model cache - fully portable!
# Project Creator: Herman Swanepoel
# -------------------------------

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$OllamaExe = Join-Path $ProjectRoot "ollama\ollama.exe"
$ModelsDir = Join-Path $ProjectRoot "models"

Write-Host "🚀 Starting Ollama Server (Portable)" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
Write-Host ""

# Verify Ollama exists
if (-not (Test-Path $OllamaExe)) {
    Write-Host "❌ Ollama not found at: $OllamaExe" -ForegroundColor Red
    Write-Host "   Run setup_portable_ollama.ps1 first!" -ForegroundColor Yellow
    exit 1
}

# Ensure models directory exists
if (-not (Test-Path $ModelsDir)) {
    New-Item -ItemType Directory -Path $ModelsDir -Force | Out-Null
    Write-Host "📁 Created models directory: $ModelsDir" -ForegroundColor Green
}

# Set environment to use local models (CRITICAL for portability!)
$env:OLLAMA_MODELS = $ModelsDir

Write-Host "📦 Configuration:" -ForegroundColor Yellow
Write-Host "   Executable: $OllamaExe" -ForegroundColor Gray
Write-Host "   Models Dir: $ModelsDir" -ForegroundColor Gray
Write-Host "   Server URL: http://localhost:11434" -ForegroundColor Gray
Write-Host ""

# Check if already running
try {
    $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -TimeoutSec 2 -ErrorAction Stop -UseBasicParsing
    Write-Host "✅ Ollama already running!" -ForegroundColor Green
    Write-Host ""

    $models = ($response.Content | ConvertFrom-Json).models
    Write-Host "📦 Available Models ($($models.Count)):" -ForegroundColor Cyan
    $models | ForEach-Object {
        $sizeGB = [math]::Round($_.size/1GB, 2)
        Write-Host "   • $($_.name) ($sizeGB GB)" -ForegroundColor Gray
    }
    exit 0
} catch {
    Write-Host "⚙️  Starting new Ollama instance..." -ForegroundColor Yellow
}

# Start Ollama in background (silently)
Write-Host "   Launching Ollama server..." -ForegroundColor Gray
Start-Process -FilePath $OllamaExe -ArgumentList "serve" -WindowStyle Hidden

# Wait for startup
Write-Host "   Waiting for server to start" -NoNewline
$maxAttempts = 15
$attempt = 0

while ($attempt -lt $maxAttempts) {
    Start-Sleep -Seconds 1
    Write-Host "." -NoNewline

    try {
        $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -TimeoutSec 1 -ErrorAction Stop -UseBasicParsing
        Write-Host ""
        Write-Host ""
        Write-Host "✅ Ollama server started successfully!" -ForegroundColor Green

        $models = ($response.Content | ConvertFrom-Json).models
        Write-Host ""
        Write-Host "📦 Available Models ($($models.Count)):" -ForegroundColor Cyan

        if ($models.Count -eq 0) {
            Write-Host "   ⚠️  No models found!" -ForegroundColor Yellow
            Write-Host "   Run pull_models.ps1 to download required models" -ForegroundColor Gray
        } else {
            $models | ForEach-Object {
                $sizeGB = [math]::Round($_.size/1GB, 2)
                Write-Host "   • $($_.name) ($sizeGB GB)" -ForegroundColor Gray
            }
        }

        Write-Host ""
        Write-Host "💡 Tip: Keep this terminal open while Ollama is running" -ForegroundColor Cyan
        exit 0
    } catch {
        $attempt++
    }
}

Write-Host ""
Write-Host "❌ Failed to start Ollama within 15 seconds" -ForegroundColor Red
exit 1
