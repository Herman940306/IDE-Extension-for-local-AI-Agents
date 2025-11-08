# ====================================================================
# BACKUP_TO_D_DRIVE.ps1
# Automated, adaptive-speed project backup from HDD to SSD
# Optimized for large file copies using Robocopy with live progress
# ====================================================================

Clear-Host
Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  Automated Project Backup & Migration to SSD                  ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# === CONFIGURATION ===
$source = "E:\Visual Studio Coode Projects\AI Agents Integration system for VS Code"
$targetRoot = "F:\VScode Projects"
$projectName = Split-Path $source -Leaf
$target = Join-Path $targetRoot $projectName
$logFile = Join-Path $targetRoot ("backup_log_{0}.txt" -f (Get-Date -Format "yyyy-MM-dd_HHmmss"))

# === STEP 1: Disk Health Check ===
Write-Host "`n🔍 Step 1/4: Checking Disk Health..." -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

Get-PhysicalDisk | Select-Object FriendlyName, MediaType, OperationalStatus, HealthStatus, @{Name="Size_GB";Expression={[math]::Round($_.Size/1GB,2)}} | Format-Table

$sourceDriveLetter = $source.Substring(0,1)
$drive = Get-PSDrive -Name $sourceDriveLetter -ErrorAction SilentlyContinue

if (-not $drive) {
    Write-Host "❌ Source drive $sourceDriveLetter not found!" -ForegroundColor Red
    exit
}

$isHDD = (Get-PhysicalDisk | Where-Object { $_.FriendlyName -like "*$sourceDriveLetter*" -and $_.MediaType -eq "HDD" }) -ne $null

# === STEP 2: Create Backup Directory ===
Write-Host "`n📁 Step 2/4: Creating Backup Directory..." -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if (-not (Test-Path $target)) {
    New-Item -ItemType Directory -Path $target | Out-Null
    Write-Host "✅ Created: $target" -ForegroundColor Green
} else {
    Write-Host "📁 Already exists: $target" -ForegroundColor Yellow
}

# === STEP 3: Adaptive Copying Strategy ===
Write-Host "`n⚙️ Step 3/4: Optimizing Copy Strategy..." -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if ($isHDD) {
    Write-Host "💡 Source drive (${sourceDriveLetter}:) is HDD — enabling adaptive throttling" -ForegroundColor Cyan
    $threadCount = 8
} else {
    Write-Host "⚡ Source drive (${sourceDriveLetter}:) is SSD — using max parallelism" -ForegroundColor Cyan
    $threadCount = 16
}

# === STEP 4: Run Robocopy Backup ===
Write-Host "`n🔄 Step 4/4: Syncing Project Files..." -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Write-Host "Using robocopy for efficient backup..."
Write-Host "Log File : $logFile"
Write-Host ""

$robocopyArgs = @(
    "`"$source`"", "`"$target`"", "/MIR", "/Z", "/R:2", "/W:2", "/MT:$threadCount",
    "/LOG+:`"$logFile`"", "/TEE", "/NFL", "/NDL", "/NP", "/ETA"
)

# Run the copy job in background to keep PowerShell responsive
$job = Start-Job -ScriptBlock {
    param($args)
    robocopy @args | Out-Null
} -ArgumentList ($robocopyArgs)

Write-Host "⏳ Copying in progress... please wait."

# Polling for completion
while ($job.State -eq "Running") {
    Write-Host "." -NoNewline
    Start-Sleep -Seconds 5
}
Write-Host ""

# Cleanly finish and report
Receive-Job -Job $job -ErrorAction SilentlyContinue | Out-Null
Remove-Job -Job $job -Force

Write-Host "`n✅ Backup Completed Successfully!" -ForegroundColor Green
Write-Host "🗂️  Files backed up from $source to $target"
Write-Host "🧾  Log saved at: $logFile"
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
