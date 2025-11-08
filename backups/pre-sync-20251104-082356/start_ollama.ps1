# Start Portable Ollama Server
# Auto-generated script - uses local Ollama installation

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$OllamaExe = Join-Path $ProjectRoot "ollama\ollama.exe"
$ModelsDir = Join-Path $ProjectRoot "ollama_models"

# Verify Ollama exists
if (-not (Test-Path $OllamaExe)) {
    Write-Host "❌ Ollama not found at: $OllamaExe" -ForegroundColor Red
    Write-Host "   Run setup_portable_ollama.ps1 first!" -ForegroundColor Yellow
    exit 1
}

# Set environment to use local models
$env:OLLAMA_MODELS = $ModelsDir

Write-Host "🚀 Starting Portable Ollama Server..." -ForegroundColor Cyan
Write-Host "   Executable: $OllamaExe" -ForegroundColor Gray
Write-Host "   Models Dir: $ModelsDir" -ForegroundColor Gray
Write-Host "   URL: http://localhost:11434" -ForegroundColor Gray
Write-Host ""

# Check if already running
try {
    $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -TimeoutSec 2 -ErrorAction Stop
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

# Start Ollama in background
Start-Process -FilePath $OllamaExe -ArgumentList "serve" -WindowStyle Hidden

# Wait for startup
Write-Host "   Waiting for server to start" -NoNewline
$maxAttempts = 15
$attempt = 0

while ($attempt -lt $maxAttempts) {
    Start-Sleep -Seconds 1
    Write-Host "." -NoNewline
    
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -TimeoutSec 1 -ErrorAction Stop
        Write-Host ""
        Write-Host ""
        Write-Host "✅ Ollama server started successfully!" -ForegroundColor Green
        
        $models = ($response.Content | ConvertFrom-Json).models
        Write-Host ""
        Write-Host "📦 Available Models ($($models.Count)):" -ForegroundColor Cyan
        $models | ForEach-Object {
            $sizeGB = [math]::Round($_.size/1GB, 2)
            Write-Host "   • $($_.name) ($sizeGB GB)" -ForegroundColor Gray
        }
        
        exit 0
    } catch {
        $attempt++
    }
}

Write-Host ""
Write-Host "❌ Failed to start Ollama within 15 seconds" -ForegroundColor Red
exit 1
