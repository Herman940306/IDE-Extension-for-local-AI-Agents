# EMERGENCY: Backup Critical Project Data
# Your NVMe SSD is showing Predictive Failure!

$ErrorActionPreference = "Stop"

Write-Host "🚨 EMERGENCY BACKUP SCRIPT" -ForegroundColor Red
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
Write-Host ""

# Get project root
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

# Determine backup target (prefer healthy drives)
$BackupLocations = @(
    "D:\BACKUP_$(Get-Date -Format 'yyyy-MM-dd_HHmmss')",  # WDC WD20EZRX (2TB HDD - Healthy)
    "F:\BACKUP_$(Get-Date -Format 'yyyy-MM-dd_HHmmss')",  # Samsung 750 EVO (250GB SSD - Healthy)
    "G:\BACKUP_$(Get-Date -Format 'yyyy-MM-dd_HHmmss')"   # ST500 (500GB HDD - Healthy)
)

Write-Host "📊 Disk Status:" -ForegroundColor Yellow
Get-PhysicalDisk | Select-Object FriendlyName, MediaType, OperationalStatus, HealthStatus | Format-Table -AutoSize

Write-Host ""
Write-Host "🎯 Backup Target Options:" -ForegroundColor Cyan
$BackupLocations | ForEach-Object {
    $drive = $_.Substring(0, 2)
    if (Test-Path $drive) {
        $volume = Get-Volume -DriveLetter $drive[0]
        $freeGB = [math]::Round($volume.SizeRemaining / 1GB, 2)
        Write-Host "   $drive - $freeGB GB free" -ForegroundColor Green
    } else {
        Write-Host "   $drive - Not available" -ForegroundColor Gray
    }
}

Write-Host ""
$selectedDrive = Read-Host "Enter target drive letter (D/F/G)"
$BackupPath = "$($selectedDrive):\BACKUP_AI_AGENTS_$(Get-Date -Format 'yyyy-MM-dd_HHmmss')"

Write-Host ""
Write-Host "📁 Creating backup at: $BackupPath" -ForegroundColor Yellow

# Create backup directory
New-Item -ItemType Directory -Path $BackupPath -Force | Out-Null

# Critical files to backup
Write-Host ""
Write-Host "📦 Backing up critical files..." -ForegroundColor Cyan

$itemsToBackup = @(
    @{Name="Source Code"; Path="backend\src"},
    @{Name="Tests"; Path="backend\tests"},
    @{Name="Configuration"; Path="backend\src\config"},
    @{Name="Virtual Environment"; Path=".venv"},
    @{Name="Documentation"; Path="*.md"},
    @{Name="Scripts"; Path="*.ps1"},
    @{Name="Requirements"; Path="backend\requirements.txt"},
    @{Name="Git Config"; Path=".git"}
)

$totalItems = $itemsToBackup.Count
$current = 0

foreach ($item in $itemsToBackup) {
    $current++
    $percent = [math]::Round(($current / $totalItems) * 100)

    Write-Host "   [$current/$totalItems] Backing up: $($item.Name)..." -ForegroundColor Yellow

    $sourcePath = Join-Path $ProjectRoot $item.Path
    $destPath = Join-Path $BackupPath $item.Path

    if (Test-Path $sourcePath) {
        try {
            if ($item.Path -match '\*') {
                # Wildcard pattern
                Copy-Item -Path $sourcePath -Destination $BackupPath -Force -ErrorAction Stop
            } else {
                # Directory or file
                Copy-Item -Path $sourcePath -Destination $destPath -Recurse -Force -ErrorAction Stop
            }
            Write-Host "      ✅ Backed up" -ForegroundColor Green
        } catch {
            Write-Host "      ⚠️  Failed: $_" -ForegroundColor Yellow
        }
    } else {
        Write-Host "      ⏭️  Not found, skipping" -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
Write-Host "✅ BACKUP COMPLETE!" -ForegroundColor Green
Write-Host ""
Write-Host "📁 Backup Location: $BackupPath" -ForegroundColor Cyan
Write-Host ""

# Get backup size
$backupSize = (Get-ChildItem -Path $BackupPath -Recurse | Measure-Object -Property Length -Sum).Sum
$backupSizeGB = [math]::Round($backupSize / 1GB, 2)
Write-Host "📊 Backup Size: $backupSizeGB GB" -ForegroundColor Gray

Write-Host ""
Write-Host "🔴 NEXT STEPS:" -ForegroundColor Red
Write-Host "   1. Replace failing NVMe SSD ASAP" -ForegroundColor Yellow
Write-Host "   2. Move project to healthy drive temporarily" -ForegroundColor Yellow
Write-Host "   3. Run disk diagnostics: Get-PhysicalDisk | Get-StorageReliabilityCounter" -ForegroundColor Yellow
Write-Host "   4. Check SMART data with CrystalDiskInfo" -ForegroundColor Yellow
Write-Host ""
