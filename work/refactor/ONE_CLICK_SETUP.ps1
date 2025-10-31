# ===================================================================
# ONE-CLICK SETUP & TEST - Complete Automation
# Runs the entire setup and test process automatically
# Project Creator: Herman Swanepoel
# ===================================================================

param(
    [switch]$SkipModelCopy,
    [switch]$QuickTest
)

$ErrorActionPreference = "Continue"

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Magenta
Write-Host "║                                                                ║" -ForegroundColor Magenta
Write-Host "║          AI AGENTS INTEGRATION SYSTEM                          ║" -ForegroundColor Magenta
Write-Host "║          ONE-CLICK SETUP & TEST                                ║" -ForegroundColor Magenta
Write-Host "║                                                                ║" -ForegroundColor Magenta
Write-Host "║          Project Creator: Herman Swanepoel                     ║" -ForegroundColor Magenta
Write-Host "║                                                                ║" -ForegroundColor Magenta
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Magenta
Write-Host ""

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

Write-Host "📁 Project Root: $ProjectRoot" -ForegroundColor Gray
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
Write-Host ""

# ===================================================================
# Phase 1: Setup Portable Ollama
# ===================================================================
Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  PHASE 1: Setting Up Portable Ollama                          ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

$ollamaExe = Join-Path $ProjectRoot "ollama\ollama.exe"

if (-not (Test-Path $ollamaExe)) {
    Write-Host "⚙️  Running portable Ollama setup..." -ForegroundColor Yellow

    if ($SkipModelCopy) {
        # TODO: Add flag to setup script
        & ".\setup_portable_ollama.ps1"
    } else {
        & ".\setup_portable_ollama.ps1"
    }

    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "❌ Portable Ollama setup failed!" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "✅ Portable Ollama already set up" -ForegroundColor Green
}

Write-Host ""

# ===================================================================
# Phase 2: Start Ollama Server
# ===================================================================
Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  PHASE 2: Starting Ollama Server                              ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

& ".\start_ollama.ps1"

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "❌ Failed to start Ollama server!" -ForegroundColor Red
    exit 1
}

Write-Host ""

# ===================================================================
# Phase 3: Check Models
# ===================================================================
Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  PHASE 3: Checking Available Models                           ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

try {
    $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -TimeoutSec 5
    $models = ($response.Content | ConvertFrom-Json).models

    $requiredModels = @("qwen3:8b", "codellama:7b", "gemma3:4b", "nomic-embed-text:latest")
    $missingModels = @()

    foreach ($required in $requiredModels) {
        $found = $models | Where-Object { $_.name -eq $required }
        if (-not $found) {
            $missingModels += $required
        }
    }

    if ($missingModels.Count -gt 0) {
        Write-Host "⚠️  Missing required models:" -ForegroundColor Yellow
        $missingModels | ForEach-Object { Write-Host "   • $_" -ForegroundColor Gray }
        Write-Host ""

        $response = Read-Host "Pull missing models now? (y/N)"
        if ($response -eq 'y' -or $response -eq 'Y') {
            Write-Host ""
            & ".\pull_models.ps1"
            Write-Host ""
        } else {
            Write-Host "⚠️  Warning: Tests may fail without required models" -ForegroundColor Yellow
            Write-Host ""
        }
    } else {
        Write-Host "✅ All required models available!" -ForegroundColor Green
        Write-Host ""
    }
} catch {
    Write-Host "❌ Failed to check models: $_" -ForegroundColor Red
    exit 1
}

# ===================================================================
# Phase 4: Run Tests
# ===================================================================
Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  PHASE 4: Running E2E Tests                                   ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

if ($QuickTest) {
    Write-Host "⚡ Quick Test Mode: Running single test" -ForegroundColor Yellow
    Write-Host ""
    & ".\RUN_TESTS.ps1" -SingleTest -TestName "test_code_generation_task"
} else {
    Write-Host "🧪 Full Test Mode: Running complete test suite" -ForegroundColor Yellow
    Write-Host ""
    & ".\RUN_TESTS.ps1"
}

$testExitCode = $LASTEXITCODE

Write-Host ""

# ===================================================================
# Final Summary
# ===================================================================
Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Magenta
Write-Host "║                                                                ║" -ForegroundColor Magenta

if ($testExitCode -eq 0) {
    Write-Host "║          ✅ ALL PHASES COMPLETE - TESTS PASSED! 🎉            ║" -ForegroundColor Green
} else {
    Write-Host "║          ❌ TESTS FAILED - SEE DETAILS ABOVE                  ║" -ForegroundColor Red
}

Write-Host "║                                                                ║" -ForegroundColor Magenta
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Magenta
Write-Host ""

Write-Host "📊 Summary:" -ForegroundColor Cyan
Write-Host "   ✅ Phase 1: Portable Ollama Setup" -ForegroundColor Green
Write-Host "   ✅ Phase 2: Ollama Server Started" -ForegroundColor Green
Write-Host "   ✅ Phase 3: Models Checked" -ForegroundColor Green

if ($testExitCode -eq 0) {
    Write-Host "   ✅ Phase 4: E2E Tests Passed" -ForegroundColor Green
} else {
    Write-Host "   ❌ Phase 4: E2E Tests Failed" -ForegroundColor Red
}

Write-Host ""
Write-Host "📁 Project is now ready for deployment!" -ForegroundColor Green
Write-Host "   Zip entire folder and copy to any Windows system" -ForegroundColor Gray
Write-Host ""

exit $testExitCode
