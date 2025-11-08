# ===================================================================
# AI Agents Integration System - Complete Test Runner
# Portable script that works on any system - no hard-coded paths!
# Project Creator: Herman Swanepoel
# ===================================================================

param(
    [switch]$SkipDiagnostic,
    [switch]$SingleTest,
    [string]$TestName = "test_code_generation_task"
)

$ErrorActionPreference = "Continue"

# Get project root (where this script is located)
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Join-Path $ProjectRoot "backend"
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  AI Agents Integration System - Test Runner v2.0              ║" -ForegroundColor Cyan
Write-Host "║  Project Creator: Herman Swanepoel                            ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# ===================================================================
# Step 1: Verify Prerequisites
# ===================================================================
Write-Host "📋 Step 1/5: Verifying Prerequisites..." -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray

# Check Python virtual environment
if (-not (Test-Path $VenvPython)) {
    Write-Host "❌ Python virtual environment not found!" -ForegroundColor Red
    Write-Host "   Expected: $VenvPython" -ForegroundColor Gray
    Write-Host "   Please run setup first." -ForegroundColor Yellow
    exit 1
}
Write-Host "✅ Python venv found: $VenvPython" -ForegroundColor Green

# Check backend directory
if (-not (Test-Path $BackendDir)) {
    Write-Host "❌ Backend directory not found!" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Backend directory found" -ForegroundColor Green

# Check Ollama (try portable first, then system)
Write-Host ""
Write-Host "🔍 Checking Ollama service..." -ForegroundColor Cyan

# Set portable models path
$PortableModelsDir = Join-Path $ProjectRoot "ollama_models"
$env:OLLAMA_MODELS = $PortableModelsDir

try {
    $ollamaResponse = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -TimeoutSec 5 -ErrorAction Stop
    $models = ($ollamaResponse.Content | ConvertFrom-Json).models
    Write-Host "✅ Ollama is running with $($models.Count) models:" -ForegroundColor Green
    $models | ForEach-Object { 
        $sizeGB = [math]::Round($_.size/1GB, 2)
        Write-Host "   • $($_.name) ($sizeGB GB)" -ForegroundColor Gray
    }
} catch {
    Write-Host "❌ Ollama is not running!" -ForegroundColor Red
    Write-Host "   Starting portable Ollama..." -ForegroundColor Yellow
    
    # Try to start portable Ollama
    $PortableOllama = Join-Path $ProjectRoot "ollama\ollama.exe"
    if (Test-Path $PortableOllama) {
        Write-Host "   Found portable Ollama at: $PortableOllama" -ForegroundColor Cyan
        Start-Process -FilePath $PortableOllama -ArgumentList "serve" -WindowStyle Hidden
        Start-Sleep -Seconds 3
        
        # Check again
        try {
            $ollamaResponse = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -TimeoutSec 5 -ErrorAction Stop
            Write-Host "✅ Portable Ollama started successfully!" -ForegroundColor Green
        } catch {
            Write-Host "❌ Failed to start portable Ollama" -ForegroundColor Red
            exit 1
        }
    } else {
        Write-Host ""
        Write-Host "   No portable Ollama found. Options:" -ForegroundColor Yellow
        Write-Host "   1. Run: .\setup_portable_ollama.ps1" -ForegroundColor White
        Write-Host "   2. Run: .\start_ollama.ps1" -ForegroundColor White
        Write-Host "   3. Start system Ollama manually" -ForegroundColor White
        exit 1
    }
}

Write-Host ""

# ===================================================================
# Step 2: Start Backend Server
# ===================================================================
Write-Host "🚀 Step 2/5: Starting Backend Server..." -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray

# Check if backend is already running
try {
    $healthCheck = Invoke-WebRequest -Uri "http://localhost:8001/health" -TimeoutSec 2 -ErrorAction Stop
    Write-Host "✅ Backend already running and healthy" -ForegroundColor Green
    $backendAlreadyRunning = $true
} catch {
    Write-Host "⚙️  Starting new backend instance..." -ForegroundColor Cyan
    
    # Start backend in background
    $BackendProcess = Start-Process -FilePath $VenvPython `
        -ArgumentList "-m", "uvicorn", "src.main:app", "--host", "127.0.0.1", "--port", "8001" `
        -WorkingDirectory $BackendDir `
        -WindowStyle Hidden `
        -PassThru
    
    Write-Host "   Backend PID: $($BackendProcess.Id)" -ForegroundColor Gray
    
    # Wait for backend to start (max 15 seconds)
    Write-Host "   Waiting for backend to start" -NoNewline -ForegroundColor Gray
    $maxAttempts = 15
    $attempt = 0
    $backendReady = $false
    
    while ($attempt -lt $maxAttempts -and -not $backendReady) {
        Start-Sleep -Seconds 1
        Write-Host "." -NoNewline -ForegroundColor Gray
        try {
            $healthCheck = Invoke-WebRequest -Uri "http://localhost:8001/health" -TimeoutSec 1 -ErrorAction Stop
            $backendReady = $true
        } catch {
            $attempt++
        }
    }
    Write-Host ""
    
    if ($backendReady) {
        Write-Host "✅ Backend started successfully!" -ForegroundColor Green
    } else {
        Write-Host "❌ Backend failed to start within 15 seconds" -ForegroundColor Red
        if ($BackendProcess -and -not $BackendProcess.HasExited) {
            $BackendProcess.Kill()
        }
        exit 1
    }
    
    $backendAlreadyRunning = $false
}

Write-Host ""

# ===================================================================
# Step 3: Run Diagnostic Test
# ===================================================================
if (-not $SkipDiagnostic) {
    Write-Host "🔬 Step 3/5: Running Diagnostic Test..." -ForegroundColor Yellow
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
    
    $diagnosticScript = Join-Path $BackendDir "diagnostic_test.py"
    & $VenvPython $diagnosticScript
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "❌ Diagnostic test failed!" -ForegroundColor Red
        Write-Host "   Please fix issues before running full tests." -ForegroundColor Yellow
        
        # Cleanup backend if we started it
        if (-not $backendAlreadyRunning -and $BackendProcess) {
            Write-Host "   Stopping backend..." -ForegroundColor Gray
            $BackendProcess.Kill()
        }
        exit 1
    }
    
    Write-Host ""
    Write-Host "✅ Diagnostic test passed!" -ForegroundColor Green
    Write-Host ""
} else {
    Write-Host "⏭️  Step 3/5: Skipping Diagnostic Test (--SkipDiagnostic flag)" -ForegroundColor Gray
    Write-Host ""
}

# ===================================================================
# Step 4: Run E2E Tests
# ===================================================================
Write-Host "🧪 Step 4/5: Running E2E Tests..." -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray

$testFile = Join-Path $BackendDir "tests\integration\test_end_to_end_router_v2.py"

if ($SingleTest) {
    Write-Host "Running single test: $TestName" -ForegroundColor Cyan
    $testTarget = "${testFile}::TestRouterV2EndToEnd::${TestName}"
} else {
    Write-Host "Running full test suite (15 tests)" -ForegroundColor Cyan
    $testTarget = $testFile
}

Write-Host ""

# Run pytest with proper working directory
Set-Location $ProjectRoot
& $VenvPython -m pytest $testTarget -v --tb=short --color=yes

$testExitCode = $LASTEXITCODE

Write-Host ""

# ===================================================================
# Step 5: Cleanup & Summary
# ===================================================================
Write-Host "🧹 Step 5/5: Cleanup & Summary..." -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray

# Stop backend if we started it
if (-not $backendAlreadyRunning -and $BackendProcess) {
    if (-not $BackendProcess.HasExited) {
        Write-Host "Stopping backend (PID: $($BackendProcess.Id))..." -ForegroundColor Gray
        $BackendProcess.Kill()
        Write-Host "✅ Backend stopped" -ForegroundColor Green
    }
} else {
    Write-Host "ℹ️  Backend was already running - leaving it active" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan

if ($testExitCode -eq 0) {
    Write-Host "║  ✅ ALL TESTS PASSED! 🎉                                      ║" -ForegroundColor Green
} else {
    Write-Host "║  ❌ TESTS FAILED - See details above                          ║" -ForegroundColor Red
}

Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Return test exit code
exit $testExitCode
