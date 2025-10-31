# Optimize System Resources for Testing
# This script frees up resources and optimizes for LLM testing

Write-Host "🔧 Optimizing System for Testing..." -ForegroundColor Cyan
Write-Host ""

# 1. Clear Python cache and temp files
Write-Host "📦 Cleaning Python cache..." -ForegroundColor Yellow
Get-ChildItem -Path "." -Include "__pycache__", "*.pyc", ".pytest_cache" -Recurse -Force | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Write-Host "   ✅ Python cache cleaned" -ForegroundColor Green

# 2. Clear old test coverage data
Write-Host "📊 Cleaning old coverage data..." -ForegroundColor Yellow
Remove-Item "backend\.coverage" -ErrorAction SilentlyContinue
Remove-Item "backend\htmlcov" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item "coverage.xml" -ErrorAction SilentlyContinue
Write-Host "   ✅ Coverage data cleaned" -ForegroundColor Green

# 3. Close unnecessary Chrome/Edge processes (keep current tab)
Write-Host "🌐 Optimizing browser processes..." -ForegroundColor Yellow
$chromeProcesses = Get-Process chrome -ErrorAction SilentlyContinue | Where-Object {$_.CPU -lt 10}
if ($chromeProcesses) {
    $chromeProcesses | Stop-Process -Force -ErrorAction SilentlyContinue
    Write-Host "   ✅ Closed idle Chrome processes" -ForegroundColor Green
} else {
    Write-Host "   ℹ️  No idle Chrome processes found" -ForegroundColor Gray
}

# 4. Set Windows to High Performance mode for testing
Write-Host "⚡ Setting power plan to High Performance..." -ForegroundColor Yellow
powercfg /setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c 2>$null
Write-Host "   ✅ Power plan optimized" -ForegroundColor Green

# 5. Increase Python process priority for better performance
Write-Host "🐍 Optimizing Python process priority..." -ForegroundColor Yellow
Get-Process python -ErrorAction SilentlyContinue | ForEach-Object {
    try {
        $_.PriorityClass = "High"
        Write-Host "   ✅ Set Python process to High priority" -ForegroundColor Green
    } catch {
        Write-Host "   ⚠️  Could not change priority (may need admin)" -ForegroundColor Yellow
    }
}

# 6. Display current resource usage
Write-Host ""
Write-Host "📊 Current Resource Usage:" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray

# Memory
$os = Get-CimInstance Win32_OperatingSystem
$totalRAM = [math]::Round($os.TotalVisibleMemorySize/1MB, 2)
$freeRAM = [math]::Round($os.FreePhysicalMemory/1MB, 2)
$usedRAM = $totalRAM - $freeRAM
$ramPercent = [math]::Round(($usedRAM / $totalRAM) * 100, 1)

Write-Host "💾 RAM: $usedRAM GB / $totalRAM GB ($ramPercent% used)" -ForegroundColor $(if ($ramPercent -gt 85) {"Red"} elseif ($ramPercent -gt 70) {"Yellow"} else {"Green"})

# CPU
$cpu = Get-CimInstance Win32_Processor
Write-Host "🖥️  CPU: $($cpu.Name)" -ForegroundColor Gray
Write-Host "   Cores: $($cpu.NumberOfCores) | Threads: $($cpu.NumberOfLogicalProcessors)" -ForegroundColor Gray

# Disk (RAID bottleneck info)
Write-Host ""
Write-Host "💽 Disk Configuration:" -ForegroundColor Cyan
$disks = Get-PhysicalDisk
foreach ($disk in $disks) {
    $health = $disk.HealthStatus
    $usage = $disk.Usage
    $busType = $disk.BusType
    $speed = $disk.SpindleSpeed

    $color = if ($health -eq "Healthy") {"Green"} else {"Red"}
    Write-Host "   $($disk.FriendlyName):" -ForegroundColor $color
    Write-Host "      Status: $health | Type: $busType | Usage: $usage" -ForegroundColor Gray
    if ($speed -and $speed -gt 0) {
        Write-Host "      Speed: $speed RPM" -ForegroundColor Gray
    }
}

# Check for RAID configuration
Write-Host ""
Write-Host "🔍 Checking RAID Configuration..." -ForegroundColor Yellow
$volumes = Get-Volume | Where-Object {$_.DriveType -eq "Fixed"}
foreach ($vol in $volumes) {
    if ($vol.DriveLetter) {
        Write-Host "   Drive $($vol.DriveLetter): $([math]::Round($vol.Size/1GB, 2)) GB total, $([math]::Round($vol.SizeRemaining/1GB, 2)) GB free" -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
Write-Host ""
Write-Host "✅ Optimization Complete!" -ForegroundColor Green
Write-Host ""
Write-Host "💡 Tips for Better Performance:" -ForegroundColor Cyan
Write-Host "   1. Close unnecessary applications (browsers, editors)" -ForegroundColor Gray
Write-Host "   2. Use smaller models for faster testing (qwen3:4b vs qwen3:8b)" -ForegroundColor Gray
Write-Host "   3. Reduce test timeout if tests are passing quickly" -ForegroundColor Gray
Write-Host "   4. Run tests sequentially instead of parallel (-n 1)" -ForegroundColor Gray
Write-Host ""

# RAID Bottleneck Advice
Write-Host "🚨 RAID Bottleneck Detected?" -ForegroundColor Yellow
Write-Host "   If you have RAID with 1 slow disk bottlenecking:" -ForegroundColor Gray
Write-Host ""
Write-Host "   Quick Fixes:" -ForegroundColor Cyan
Write-Host "   • Move .venv to faster drive (SSD if available)" -ForegroundColor Gray
Write-Host "   • Set OLLAMA_MODELS env var to SSD location" -ForegroundColor Gray
Write-Host "   • Use RAM disk for temporary test files" -ForegroundColor Gray
Write-Host ""
Write-Host "   Commands to move Ollama models to faster drive:" -ForegroundColor Cyan
Write-Host "   1. Stop Ollama: Get-Process ollama* | Stop-Process -Force" -ForegroundColor Gray
Write-Host "   2. Set env: " -NoNewline -ForegroundColor Gray
Write-Host "[System.Environment]::SetEnvironmentVariable('OLLAMA_MODELS', 'D:\OllamaModels', 'User')" -ForegroundColor White
Write-Host "   3. Copy models: robocopy `"~\.ollama\models`" `"D:\OllamaModels`" /E" -ForegroundColor Gray
Write-Host "   4. Restart Ollama" -ForegroundColor Gray
Write-Host ""
