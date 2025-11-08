param(
    [string]$RepoUrl = "https://github.com/Herman940306/IDE-Extension-for-local-AI-Agents.git",
    [switch]$NoBackup,
    [switch]$Purge,         # If set, delete local files not present in remote (dangerous)
    [switch]$Quiet
)

$ErrorActionPreference = "Stop"

function Write-Info($msg) { if (-not $Quiet) { Write-Host $msg -ForegroundColor Cyan } }
function Write-Ok($msg)   { if (-not $Quiet) { Write-Host $msg -ForegroundColor Green } }
function Write-Warn($msg) { if (-not $Quiet) { Write-Host $msg -ForegroundColor Yellow } }
function Write-Err($msg)  { Write-Host $msg -ForegroundColor Red }

# Root paths
$root       = (Get-Location).Path
$remoteRoot = Join-Path $root "remote_clone"
$backupsDir = Join-Path $root "backups"
$stamp      = Get-Date -Format "yyyyMMdd-HHmmss"
$backupPath = Join-Path $backupsDir "pre-sync-$stamp"

# Exclusions for backup and apply
$excludeDirsBackup = @("remote_clone","backups",".git",".venv","venv","models","ollama","ollama_models","frontend\node_modules","extension\node_modules")
$excludeDirsApply  = @(".git","remote_clone","backups")

try {
    Write-Info "[1/4] Ensuring remote clone at: $remoteRoot"
    if (Test-Path (Join-Path $remoteRoot ".git")) {
        git -C "$remoteRoot" fetch origin
        git -C "$remoteRoot" reset --hard origin/main
        Write-Ok "[Updated existing clone]"
    } else {
        git clone $RepoUrl "$remoteRoot"
        Write-Ok "[Cloned fresh copy]"
    }

    $localEnv = Join-Path $root "backend/.env"
    $remoteEnv = Join-Path $remoteRoot "backend/.env"
    if (Test-Path $localEnv) {
        Copy-Item -Path $localEnv -Destination $remoteEnv -Force -ErrorAction SilentlyContinue
        Write-Ok "[Copied backend/.env into remote_clone]"
    } else {
        Write-Warn "[No backend/.env found locally to copy]"
    }

    if (-not $NoBackup) {
        Write-Info "[2/4] Creating backup at: $backupPath"
        New-Item -ItemType Directory -Force -Path $backupPath | Out-Null
        $xdArgs = @()
        foreach ($d in $excludeDirsBackup) { $xdArgs += @('/XD', (Join-Path $root $d)) }
        robocopy "$root" "$backupPath" /MIR /XJ /R:1 /W:1 @xdArgs | Out-Null
        Write-Ok "[Backup complete]"
    } else {
        Write-Warn "[Skipping backup as requested]"
    }

    Write-Info "[3/4] Applying remote → local sync"
    $xdApply = @()
    foreach ($d in $excludeDirsApply) { $xdApply += @('/XD', (Join-Path $root $d)) }

    # Default: Non-destructive (update/add only). With -Purge: also delete extras.
    if ($Purge) {
        Write-Warn "[Purge mode] Local files absent in remote will be deleted (excluded dirs remain)."
        robocopy "$remoteRoot" "$root" /MIR /XJ /R:1 /W:1 /FFT /COPY:DAT @xdApply | Out-Null
    } else {
        robocopy "$remoteRoot" "$root" /E   /XJ /R:1 /W:1 /FFT /COPY:DAT @xdApply | Out-Null
    }
    Write-Ok "[Sync complete]"

    Write-Info "[4/4] Summary"
    Write-Host " - Remote clone: $remoteRoot" -ForegroundColor White
    if (-not $NoBackup) { Write-Host " - Backup     : $backupPath" -ForegroundColor White }
    Write-Host " - Apply mode : " -NoNewline; if ($Purge) { Write-Host "Purge (mirrored)" -ForegroundColor White } else { Write-Host "Add/Update only" -ForegroundColor White }
    Write-Host "Next: run tests/tasks to validate the sync." -ForegroundColor DarkGray
} catch {
    Write-Err "[ERROR] $($_.Exception.Message)"
    exit 1
}
