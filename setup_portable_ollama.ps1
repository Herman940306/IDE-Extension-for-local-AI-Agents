# ===================================================================
# Portable Ollama Setup Script
# Creates a self-contained Ollama installation in project directory
# Folder Structure: ollama/ (exe) + models/ (AI models)
# Project Creator: Herman Swanepoel
# ===================================================================

$ErrorActionPreference = "Stop"

# Get project root
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$OllamaDir = Join-Path $ProjectRoot "ollama"
$ModelsDir = Join-Path $ProjectRoot "models"  # Changed to match structure

Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  Portable Ollama Setup - Self-Contained Installation          ║" -ForegroundColor Cyan
Write-Host "║  Project Creator: Herman Swanepoel                            ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# ===================================================================
# Step 1: Create directories
# ===================================================================
Write-Host "📁 Step 1/4: Creating directories..." -ForegroundColor Yellow

if (-not (Test-Path $OllamaDir)) {
    New-Item -ItemType Directory -Path $OllamaDir -Force | Out-Null
    Write-Host "   Created: $OllamaDir" -ForegroundColor Green
} else {
    Write-Host "   Already exists: $OllamaDir" -ForegroundColor Gray
}

if (-not (Test-Path $ModelsDir)) {
    New-Item -ItemType Directory -Path $ModelsDir -Force | Out-Null
    Write-Host "   Created: $ModelsDir" -ForegroundColor Green
} else {
    Write-Host "   Already exists: $ModelsDir" -ForegroundColor Gray
}

Write-Host ""

# ===================================================================
# Step 2: Copy Ollama executable
# ===================================================================
Write-Host "📥 Step 2/4: Setting up Ollama executable..." -ForegroundColor Yellow

$SystemOllamaPath = "$env:USERPROFILE\AppData\Local\Programs\Ollama\ollama.exe"
$LocalOllamaExe = Join-Path $OllamaDir "ollama.exe"

if (Test-Path $SystemOllamaPath) {
    if (-not (Test-Path $LocalOllamaExe)) {
        Write-Host "   Copying Ollama from system installation..." -ForegroundColor Cyan
        Copy-Item -Path $SystemOllamaPath -Destination $LocalOllamaExe -Force
        Write-Host "   ✅ Copied: ollama.exe" -ForegroundColor Green
    } else {
        Write-Host "   ✅ Already exists: ollama.exe" -ForegroundColor Green
    }
} else {
    Write-Host "   ⚠️  System Ollama not found at: $SystemOllamaPath" -ForegroundColor Yellow
    Write-Host "   Downloading Ollama from official source..." -ForegroundColor Cyan
    
    # Download Ollama for Windows
    $downloadUrl = "https://ollama.com/download/OllamaSetup.exe"
    $tempInstaller = Join-Path $env:TEMP "OllamaSetup.exe"
    
    try {
        Invoke-WebRequest -Uri $downloadUrl -OutFile $tempInstaller
        Write-Host "   Downloaded Ollama installer" -ForegroundColor Green
        Write-Host ""
        Write-Host "   ⚠️  Please install Ollama first, then run this script again." -ForegroundColor Yellow
        Write-Host "   Installer location: $tempInstaller" -ForegroundColor Gray
        exit 1
    } catch {
        Write-Host "   ❌ Failed to download Ollama: $_" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""

# ===================================================================
# Step 3: Copy existing models (optional)
# ===================================================================
Write-Host "📦 Step 3/4: Checking for existing models..." -ForegroundColor Yellow

$SystemModelsPath = "$env:USERPROFILE\.ollama\models"

if (Test-Path $SystemModelsPath) {
    $modelFiles = Get-ChildItem -Path $SystemModelsPath -Recurse -File | Measure-Object -Property Length -Sum
    $totalSizeGB = [math]::Round($modelFiles.Sum / 1GB, 2)
    
    Write-Host "   Found $($modelFiles.Count) model files ($totalSizeGB GB)" -ForegroundColor Cyan
    Write-Host ""
    $response = Read-Host "   Copy existing models to project? (y/N)"
    
    if ($response -eq 'y' -or $response -eq 'Y') {
        Write-Host "   Copying models (this may take several minutes)..." -ForegroundColor Yellow
        
        # Use robocopy for better performance with large files
        $robocopyArgs = @(
            "`"$SystemModelsPath`"",
            "`"$ModelsDir`"",
            "/E",       # Copy subdirectories including empty ones
            "/MT:8",    # Multi-threaded copy (8 threads)
            "/NFL",     # No file list
            "/NDL",     # No directory list
            "/NP",      # No progress
            "/R:2",     # Retry 2 times
            "/W:5"      # Wait 5 seconds between retries
        )
        
        $robocopyCmd = "robocopy $($robocopyArgs -join ' ')"
        Invoke-Expression $robocopyCmd | Out-Null
        
        Write-Host "   ✅ Models copied successfully!" -ForegroundColor Green
    } else {
        Write-Host "   ⏭️  Skipping model copy - you can pull models later" -ForegroundColor Gray
    }
} else {
    Write-Host "   ℹ️  No existing models found" -ForegroundColor Gray
    Write-Host "   You'll need to pull models after setup" -ForegroundColor Gray
}

Write-Host ""

# ===================================================================
# Step 4: Create startup scripts
# ===================================================================
Write-Host "📝 Step 4/4: Creating startup scripts..." -ForegroundColor Yellow

# Create start_ollama.ps1
$startOllamaScript = @"
# Start Portable Ollama Server
# Auto-generated script - uses local Ollama installation

`$ErrorActionPreference = "Stop"

`$ProjectRoot = Split-Path -Parent `$MyInvocation.MyCommand.Path
`$OllamaExe = Join-Path `$ProjectRoot "ollama\ollama.exe"
`$ModelsDir = Join-Path `$ProjectRoot "ollama_models"

# Verify Ollama exists
if (-not (Test-Path `$OllamaExe)) {
    Write-Host "❌ Ollama not found at: `$OllamaExe" -ForegroundColor Red
    Write-Host "   Run setup_portable_ollama.ps1 first!" -ForegroundColor Yellow
    exit 1
}

# Set environment to use local models
`$env:OLLAMA_MODELS = `$ModelsDir

Write-Host "🚀 Starting Portable Ollama Server..." -ForegroundColor Cyan
Write-Host "   Executable: `$OllamaExe" -ForegroundColor Gray
Write-Host "   Models Dir: `$ModelsDir" -ForegroundColor Gray
Write-Host "   URL: http://localhost:11434" -ForegroundColor Gray
Write-Host ""

# Check if already running
try {
    `$response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -TimeoutSec 2 -ErrorAction Stop
    Write-Host "✅ Ollama already running!" -ForegroundColor Green
    Write-Host ""
    
    `$models = (`$response.Content | ConvertFrom-Json).models
    Write-Host "📦 Available Models (`$(`$models.Count)):" -ForegroundColor Cyan
    `$models | ForEach-Object {
        `$sizeGB = [math]::Round(`$_.size/1GB, 2)
        Write-Host "   • `$(`$_.name) (`$sizeGB GB)" -ForegroundColor Gray
    }
    exit 0
} catch {
    Write-Host "⚙️  Starting new Ollama instance..." -ForegroundColor Yellow
}

# Start Ollama in background
Start-Process -FilePath `$OllamaExe -ArgumentList "serve" -WindowStyle Hidden

# Wait for startup
Write-Host "   Waiting for server to start" -NoNewline
`$maxAttempts = 15
`$attempt = 0

while (`$attempt -lt `$maxAttempts) {
    Start-Sleep -Seconds 1
    Write-Host "." -NoNewline
    
    try {
        `$response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -TimeoutSec 1 -ErrorAction Stop
        Write-Host ""
        Write-Host ""
        Write-Host "✅ Ollama server started successfully!" -ForegroundColor Green
        
        `$models = (`$response.Content | ConvertFrom-Json).models
        Write-Host ""
        Write-Host "📦 Available Models (`$(`$models.Count)):" -ForegroundColor Cyan
        `$models | ForEach-Object {
            `$sizeGB = [math]::Round(`$_.size/1GB, 2)
            Write-Host "   • `$(`$_.name) (`$sizeGB GB)" -ForegroundColor Gray
        }
        
        exit 0
    } catch {
        `$attempt++
    }
}

Write-Host ""
Write-Host "❌ Failed to start Ollama within 15 seconds" -ForegroundColor Red
exit 1
"@

$startOllamaPath = Join-Path $ProjectRoot "start_ollama.ps1"
Set-Content -Path $startOllamaPath -Value $startOllamaScript -Encoding UTF8
Write-Host "   ✅ Created: start_ollama.ps1" -ForegroundColor Green

# Create pull_models.ps1
$pullModelsScript = @"
# Pull Models for Portable Ollama
# Auto-generated script

`$ErrorActionPreference = "Stop"

`$ProjectRoot = Split-Path -Parent `$MyInvocation.MyCommand.Path
`$OllamaExe = Join-Path `$ProjectRoot "ollama\ollama.exe"
`$ModelsDir = Join-Path `$ProjectRoot "ollama_models"

# Set environment to use local models
`$env:OLLAMA_MODELS = `$ModelsDir

Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  Pull Models for Portable Ollama                              ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Required models for AI Agents Integration System
`$requiredModels = @(
    @{Name="qwen3:8b"; Description="System 1 Fast Reasoner (4.87 GB)"},
    @{Name="codellama:7b"; Description="Code Engine (3.56 GB)"},
    @{Name="gemma3:4b"; Description="Fast Model (3.11 GB)"},
    @{Name="nomic-embed-text:latest"; Description="Embeddings (0.26 GB)"}
)

Write-Host "📥 Required Models:" -ForegroundColor Yellow
`$requiredModels | ForEach-Object {
    Write-Host "   • `$(`$_.Name) - `$(`$_.Description)" -ForegroundColor Gray
}
Write-Host ""

# Start Ollama if not running
Write-Host "🔍 Checking Ollama server..." -ForegroundColor Cyan
try {
    Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -TimeoutSec 2 -ErrorAction Stop | Out-Null
    Write-Host "✅ Ollama is running" -ForegroundColor Green
} catch {
    Write-Host "⚙️  Starting Ollama..." -ForegroundColor Yellow
    Start-Process -FilePath `$OllamaExe -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep -Seconds 3
}

Write-Host ""
Write-Host "📦 Pulling models..." -ForegroundColor Yellow
Write-Host ""

foreach (`$model in `$requiredModels) {
    Write-Host "Pulling `$(`$model.Name)..." -ForegroundColor Cyan
    & `$OllamaExe pull `$model.Name
    
    if (`$LASTEXITCODE -eq 0) {
        Write-Host "   ✅ `$(`$model.Name) pulled successfully" -ForegroundColor Green
    } else {
        Write-Host "   ❌ Failed to pull `$(`$model.Name)" -ForegroundColor Red
    }
    Write-Host ""
}

Write-Host "✅ Model pulling complete!" -ForegroundColor Green
"@

$pullModelsPath = Join-Path $ProjectRoot "pull_models.ps1"
Set-Content -Path $pullModelsPath -Value $pullModelsScript -Encoding UTF8
Write-Host "   ✅ Created: pull_models.ps1" -ForegroundColor Green

Write-Host ""

# ===================================================================
# Summary
# ===================================================================
Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║  ✅ Portable Ollama Setup Complete!                           ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "📁 Project Structure:" -ForegroundColor Cyan
Write-Host "   $ProjectRoot\" -ForegroundColor Gray
Write-Host "   ├─ ollama\ollama.exe         (Portable executable)" -ForegroundColor Gray
Write-Host "   ├─ ollama_models\            (Local model storage)" -ForegroundColor Gray
Write-Host "   ├─ start_ollama.ps1          (Start Ollama server)" -ForegroundColor Gray
Write-Host "   └─ pull_models.ps1           (Pull required models)" -ForegroundColor Gray
Write-Host ""
Write-Host "📋 Next Steps:" -ForegroundColor Cyan
Write-Host "   1. Run: .\start_ollama.ps1   (Start the server)" -ForegroundColor White
Write-Host "   2. Run: .\pull_models.ps1    (Pull required models)" -ForegroundColor White
Write-Host "   3. Run: .\RUN_TESTS.ps1      (Run E2E tests)" -ForegroundColor White
Write-Host ""
Write-Host "💡 This setup is fully portable!" -ForegroundColor Green
Write-Host "   Copy the entire project folder to any Windows system and it will work." -ForegroundColor Gray
Write-Host ""
