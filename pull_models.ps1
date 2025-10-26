# -------------------------------
# Pull AI Models into Local Cache
# All models stay inside project folder
# Project Creator: Herman Swanepoel
# -------------------------------

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$OllamaExe = Join-Path $ProjectRoot "ollama\ollama.exe"
$ModelsDir = Join-Path $ProjectRoot "models"

# Set environment to use local models
$env:OLLAMA_MODELS = $ModelsDir

Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  Pull AI Models to Local Cache                                ║" -ForegroundColor Cyan
Write-Host "║  Target: .\models\                                            ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Verify Ollama exists
if (-not (Test-Path $OllamaExe)) {
    Write-Host "❌ Ollama not found!" -ForegroundColor Red
    Write-Host "   Run setup_portable_ollama.ps1 first" -ForegroundColor Yellow
    exit 1
}

# Ensure models directory exists
if (-not (Test-Path $ModelsDir)) {
    New-Item -ItemType Directory -Path $ModelsDir -Force | Out-Null
}

# Required models for AI Agents Integration System
$requiredModels = @(
    @{Name="qwen3:8b"; Description="System 1 Fast Reasoner"; Size="4.87 GB"},
    @{Name="codellama:7b"; Description="Code Engine"; Size="3.56 GB"},
    @{Name="gemma3:4b"; Description="Fast Model"; Size="3.11 GB"},
    @{Name="phi3:mini"; Description="Lightweight Model"; Size="2.03 GB"},
    @{Name="nomic-embed-text:latest"; Description="Embeddings"; Size="0.26 GB"}
)

Write-Host "📥 Required Models:" -ForegroundColor Yellow
$requiredModels | ForEach-Object {
    Write-Host "   • $($_.Name) - $($_.Description) ($($_.Size))" -ForegroundColor Gray
}
Write-Host ""

$totalSize = 13.83  # GB
Write-Host "📊 Total Download Size: ~$totalSize GB" -ForegroundColor Cyan
Write-Host "📁 Target Directory: $ModelsDir" -ForegroundColor Cyan
Write-Host ""

# Check if Ollama is running
Write-Host "🔍 Checking Ollama server..." -ForegroundColor Cyan
try {
    Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -TimeoutSec 2 -ErrorAction Stop -UseBasicParsing | Out-Null
    Write-Host "✅ Ollama is running" -ForegroundColor Green
} catch {
    Write-Host "⚙️  Starting Ollama..." -ForegroundColor Yellow
    Start-Process -FilePath $OllamaExe -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep -Seconds 5
    
    # Verify it started
    try {
        Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -TimeoutSec 2 -ErrorAction Stop -UseBasicParsing | Out-Null
        Write-Host "✅ Ollama started" -ForegroundColor Green
    } catch {
        Write-Host "❌ Failed to start Ollama" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "📦 Pulling models (this may take 10-20 minutes)..." -ForegroundColor Yellow
Write-Host ""

$successCount = 0
$failCount = 0

foreach ($model in $requiredModels) {
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
    Write-Host "Pulling: $($model.Name)" -ForegroundColor Cyan
    Write-Host "  Description: $($model.Description)" -ForegroundColor Gray
    Write-Host "  Size: $($model.Size)" -ForegroundColor Gray
    Write-Host ""
    
    try {
        & $OllamaExe pull $model.Name
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "   ✅ $($model.Name) pulled successfully" -ForegroundColor Green
            $successCount++
        } else {
            Write-Host "   ❌ Failed to pull $($model.Name)" -ForegroundColor Red
            $failCount++
        }
    } catch {
        Write-Host "   ❌ Error pulling $($model.Name): $_" -ForegroundColor Red
        $failCount++
    }
    
    Write-Host ""
}

Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
Write-Host ""

if ($failCount -eq 0) {
    Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "║  ✅ All Models Pulled Successfully!                           ║" -ForegroundColor Green
    Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Green
} else {
    Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Yellow
    Write-Host "║  ⚠️  Some Models Failed                                       ║" -ForegroundColor Yellow
    Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "📊 Summary:" -ForegroundColor Cyan
Write-Host "   ✅ Success: $successCount models" -ForegroundColor Green
if ($failCount -gt 0) {
    Write-Host "   ❌ Failed: $failCount models" -ForegroundColor Red
}

# Show current models
Write-Host ""
Write-Host "📦 Models in Local Cache:" -ForegroundColor Cyan
try {
    $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -UseBasicParsing
    $models = ($response.Content | ConvertFrom-Json).models
    
    $models | ForEach-Object {
        $sizeGB = [math]::Round($_.size/1GB, 2)
        Write-Host "   • $($_.name) ($sizeGB GB)" -ForegroundColor Gray
    }
} catch {
    Write-Host "   ⚠️  Could not fetch model list" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "✅ Ready to run tests!" -ForegroundColor Green
Write-Host "   Next: .\start_backend.ps1" -ForegroundColor Gray
Write-Host ""
