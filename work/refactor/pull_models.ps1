# Pull Models for Portable Ollama
# Auto-generated script

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$OllamaExe = Join-Path $ProjectRoot "ollama\ollama.exe"
$ModelsDir = Join-Path $ProjectRoot "ollama_models"

# Set environment to use local models
$env:OLLAMA_MODELS = $ModelsDir

Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  Pull Models for Portable Ollama                              ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Required models for AI Agents Integration System
$requiredModels = @(
    @{Name="qwen3:8b"; Description="System 1 Fast Reasoner (4.87 GB)"},
    @{Name="codellama:7b"; Description="Code Engine (3.56 GB)"},
    @{Name="gemma3:4b"; Description="Fast Model (3.11 GB)"},
    @{Name="nomic-embed-text:latest"; Description="Embeddings (0.26 GB)"}
)

Write-Host "📥 Required Models:" -ForegroundColor Yellow
$requiredModels | ForEach-Object {
    Write-Host "   • $($_.Name) - $($_.Description)" -ForegroundColor Gray
}
Write-Host ""

# Start Ollama if not running
Write-Host "🔍 Checking Ollama server..." -ForegroundColor Cyan
try {
    Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -TimeoutSec 2 -ErrorAction Stop | Out-Null
    Write-Host "✅ Ollama is running" -ForegroundColor Green
} catch {
    Write-Host "⚙️  Starting Ollama..." -ForegroundColor Yellow
    Start-Process -FilePath $OllamaExe -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep -Seconds 3
}

Write-Host ""
Write-Host "📦 Pulling models..." -ForegroundColor Yellow
Write-Host ""

foreach ($model in $requiredModels) {
    Write-Host "Pulling $($model.Name)..." -ForegroundColor Cyan
    & $OllamaExe pull $model.Name

    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✅ $($model.Name) pulled successfully" -ForegroundColor Green
    } else {
        Write-Host "   ❌ Failed to pull $($model.Name)" -ForegroundColor Red
    }
    Write-Host ""
}

Write-Host "✅ Model pulling complete!" -ForegroundColor Green
