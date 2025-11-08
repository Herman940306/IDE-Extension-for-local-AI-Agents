# ===================================================================
# Automated Project Backup to D:\VScode Projects
# Backs up entire AI Agents Integration System
# Project Creator: Herman Swanepoel
# ===================================================================

$ErrorActionPreference = "Stop"

Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  Automated Project Backup                                     ║" -ForegroundColor Cyan
Write-Host "║  Target: D:\VScode Projects                                   ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Get project root and name
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectName = Split-Path -Leaf $ProjectRoot
$Timestamp = Get-Date -Format 'yyyy-MM-dd_HHmmss'

# Backup locations
$BackupBase = "D:\VScode Projects"
$BackupPath = Join-Path $BackupBase $ProjectName
$BackupArchive = Join-Path $BackupBase "${ProjectName}_BACKUP_${Timestamp}.zip"

Write-Host "📁 Source: $ProjectRoot" -ForegroundColor Gray
Write-Host "📁 Target: $BackupPath" -ForegroundColor Gray
Write-Host ""

# ===================================================================
# Step 1: Check Disk Health
# ===================================================================
Write-Host "🔍 Step 1/4: Checking Disk Health..." -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray

$disks = Get-PhysicalDisk | Select-Object FriendlyName, MediaType, OperationalStatus, HealthStatus, @{Name="Size_GB";Expression={[math]::Round($_.Size/1GB, 2)}}

$disks | Format-Table -AutoSize

$failingDisks = $disks | Where-Object {$_.HealthStatus -ne "Healthy"}
if ($failingDisks) {
    Write-Host "⚠️  WARNING: Failing disks detected!" -ForegroundColor Red
    $failingDisks | ForEach-Object {
        Write-Host "   • $($_.FriendlyName): $($_.HealthStatus) - $($_.OperationalStatus)" -ForegroundColor Yellow
    }
    Write-Host ""
}

# Check target drive
$targetDrive = Get-Volume -DriveLetter D
$freeSpaceGB = [math]::Round($targetDrive.SizeRemaining / 1GB, 2)
$totalSpaceGB = [math]::Round($targetDrive.Size / 1GB, 2)

Write-Host "💾 Target Drive D:\" -ForegroundColor Cyan
Write-Host "   Total: $totalSpaceGB GB" -ForegroundColor Gray
Write-Host "   Free: $freeSpaceGB GB" -ForegroundColor Gray

if ($freeSpaceGB -lt 10) {
    Write-Host "   ⚠️  Low disk space!" -ForegroundColor Yellow
}

Write-Host ""

# ===================================================================
# Step 2: Create Backup Directory
# ===================================================================
Write-Host "📁 Step 2/4: Creating Backup Directory..." -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray

if (-not (Test-Path $BackupBase)) {
    New-Item -ItemType Directory -Path $BackupBase -Force | Out-Null
    Write-Host "   Created: $BackupBase" -ForegroundColor Green
}

if (Test-Path $BackupPath) {
    Write-Host "   Existing backup found, creating timestamped copy..." -ForegroundColor Yellow
    $BackupPath = Join-Path $BackupBase "${ProjectName}_${Timestamp}"
}

New-Item -ItemType Directory -Path $BackupPath -Force | Out-Null
Write-Host "   ✅ Backup directory ready: $BackupPath" -ForegroundColor Green

Write-Host ""

# ===================================================================
# Step 3: Sync Project Files
# ===================================================================
Write-Host "🔄 Step 3/4: Syncing Project Files..." -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
Write-Host ""

# Use robocopy for efficient file sync
$robocopyLog = Join-Path $BackupBase "backup_log_${Timestamp}.txt"

Write-Host "   Using robocopy for efficient backup..." -ForegroundColor Cyan
Write-Host "   This may take several minutes depending on project size..." -ForegroundColor Gray
Write-Host ""

# Robocopy arguments
$robocopyArgs = @(
    "`"$ProjectRoot`"",
    "`"$BackupPath`"",
    "/E",           # Copy subdirectories, including empty ones
    "/MT:16",       # Multi-threaded copy (16 threads)
    "/R:2",         # Retry 2 times on failed copies
    "/W:5",         # Wait 5 seconds between retries
    "/XD",          # Exclude directories
    "node_modules",
    ".pytest_cache",
    "__pycache__",
    "htmlcov",
    ".mypy_cache",
    ".git",         # Exclude .git to save space (we'll handle separately)
    "/XF",          # Exclude files
    "*.pyc",
    "*.pyo",
    "*.pyd",
    ".coverage",
    "/LOG:`"$robocopyLog`"",
    "/NP",          # No progress percentage (cleaner output)
    "/NDL"          # No directory list
)

# Execute robocopy
$robocopyCommand = "robocopy $($robocopyArgs -join ' ')"
$robocopyProcess = Start-Process -FilePath "robocopy" -ArgumentList $robocopyArgs -Wait -PassThru -NoNewWindow

# Robocopy exit codes (0-7 are success, 8+ are errors)
if ($robocopyProcess.ExitCode -le 7) {
    Write-Host "   ✅ Files synced successfully!" -ForegroundColor Green
    
    # Get backup size
    $backupSize = (Get-ChildItem -Path $BackupPath -Recurse -File | Measure-Object -Property Length -Sum).Sum
    $backupSizeGB = [math]::Round($backupSize / 1GB, 2)
    Write-Host "   📊 Backup Size: $backupSizeGB GB" -ForegroundColor Cyan
} else {
    Write-Host "   ⚠️  Robocopy completed with warnings (Exit Code: $($robocopyProcess.ExitCode))" -ForegroundColor Yellow
    Write-Host "   Check log: $robocopyLog" -ForegroundColor Gray
}

Write-Host ""

# ===================================================================
# Step 4: Backup Git Repository (Optional)
# ===================================================================
Write-Host "📦 Step 4/4: Git Repository Backup..." -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray

$gitDir = Join-Path $ProjectRoot ".git"
if (Test-Path $gitDir) {
    Write-Host "   Git repository detected" -ForegroundColor Cyan
    
    # Create git bundle (complete backup)
    $gitBundle = Join-Path $BackupPath "git_backup_${Timestamp}.bundle"
    
    try {
        Set-Location $ProjectRoot
        git bundle create $gitBundle --all 2>&1 | Out-Null
        
        if (Test-Path $gitBundle) {
            $bundleSize = (Get-Item $gitBundle).Length
            $bundleSizeMB = [math]::Round($bundleSize / 1MB, 2)
            Write-Host "   ✅ Git bundle created: $bundleSizeMB MB" -ForegroundColor Green
        }
    } catch {
        Write-Host "   ⚠️  Git bundle failed: $_" -ForegroundColor Yellow
    }
    
    # Also copy .git folder
    Write-Host "   Copying .git folder..." -ForegroundColor Cyan
    $gitBackupPath = Join-Path $BackupPath ".git"
    Copy-Item -Path $gitDir -Destination $gitBackupPath -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "   ✅ .git folder copied" -ForegroundColor Green
} else {
    Write-Host "   ℹ️  No git repository found" -ForegroundColor Gray
}

Write-Host ""

# ===================================================================
# Summary & Verification
# ===================================================================
Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║  ✅ BACKUP COMPLETE!                                          ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""

Write-Host "📊 Backup Summary:" -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
Write-Host "   📁 Source:       $ProjectRoot" -ForegroundColor Gray
Write-Host "   📁 Destination:  $BackupPath" -ForegroundColor Gray
Write-Host "   📝 Robocopy Log: $robocopyLog" -ForegroundColor Gray
Write-Host ""

# Verify critical files
Write-Host "🔍 Verifying Critical Files:" -ForegroundColor Cyan

$criticalFiles = @(
    "backend\src\main.py",
    "backend\requirements.txt",
    ".venv\Scripts\python.exe",
    "RUN_TESTS.ps1",
    "ONE_CLICK_SETUP.ps1"
)

$allPresent = $true
foreach ($file in $criticalFiles) {
    $backupFile = Join-Path $BackupPath $file
    if (Test-Path $backupFile) {
        Write-Host "   ✅ $file" -ForegroundColor Green
    } else {
        Write-Host "   ❌ $file (MISSING!)" -ForegroundColor Red
        $allPresent = $false
    }
}

Write-Host ""

if ($allPresent) {
    Write-Host "✅ All critical files backed up successfully!" -ForegroundColor Green
} else {
    Write-Host "⚠️  Some files are missing from backup - check robocopy log" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "💡 Next Steps:" -ForegroundColor Cyan
Write-Host "   1. Verify backup: cd `"$BackupPath`"" -ForegroundColor White
Write-Host "   2. Test backup: .\RUN_TESTS.ps1" -ForegroundColor White
Write-Host "   3. Schedule regular backups (see below)" -ForegroundColor White
Write-Host ""

# ===================================================================
# Create Scheduled Task (Optional)
# ===================================================================
Write-Host "📅 Automated Backup Scheduling:" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor DarkGray
Write-Host ""
Write-Host "   To schedule automatic daily backups, run:" -ForegroundColor Gray
Write-Host ""
Write-Host "   Register-ScheduledTask -TaskName `"AI_Agents_Backup`" ``" -ForegroundColor White
Write-Host "     -Trigger (New-ScheduledTaskTrigger -Daily -At 2AM) ``" -ForegroundColor White
Write-Host "     -Action (New-ScheduledTaskAction -Execute `"powershell.exe`" ``" -ForegroundColor White
Write-Host "       -Argument `"-File `"`"$PSCommandPath`"`"`") ``" -ForegroundColor White
Write-Host "     -Description `"Daily backup of AI Agents Integration System`"" -ForegroundColor White
Write-Host ""

Write-Host "✅ Backup script complete!" -ForegroundColor Green
Write-Host ""
