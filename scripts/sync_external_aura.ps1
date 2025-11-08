param(
    [Parameter(Mandatory = $true)]
    [string]$ExternalPath,

    [ValidateSet('Preview', 'Apply')]
    [string]$Mode = 'Preview',

    [ValidateSet('ExternalToWorkspace', 'WorkspaceToExternal')]
    [string]$Direction = 'ExternalToWorkspace',

    [switch]$Purge,

    [string]$BackupRoot = 'backups'
)

$ErrorActionPreference = 'Stop'

function Ensure-Path {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Path not found: $Path"
    }
}

function New-Backup {
    param([string]$WorkspaceRoot)
    $timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $backupDir = Join-Path -Path $WorkspaceRoot -ChildPath (Join-Path $BackupRoot "pre-sync-$timestamp")
    New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
    $backupDir
}

function Do-RoboCopyPreview {
    param([string]$Source, [string]$Target, [string[]]$ExcludeDirs)
    robocopy $Source $Target /MIR /L /NJH /NJS /NDL /NP /NS /NC /XD $ExcludeDirs
}

function Do-RoboCopyApply {
    param([string]$Source, [string]$Target, [switch]$Mirror, [string[]]$ExcludeDirs)
    $args = @($Source, $Target, '/E', '/R:1', '/W:1', '/NFL', '/NDL', '/NP', '/NS', '/NC')
    if ($Mirror) { $args += '/MIR' }
    if ($ExcludeDirs -and $ExcludeDirs.Count -gt 0) { $args += @('/XD') + $ExcludeDirs }
    robocopy @args
}

# Resolve paths
$ws = (Get-Location).Path
Ensure-Path -Path $ExternalPath
Ensure-Path -Path $ws

$excludeCommon = @(
    '.git', '.venv', '.venv-1', 'node_modules', 'remote_clone', 'backups', 'htmlcov',
    '.pytest_cache', '__pycache__', '.mypy_cache', '.ruff_cache', '.trunk', '.snapshots'
)
# When syncing Workspace -> External, also exclude large local-only artifacts present on External
$excludeWsToExt = $excludeCommon + @('models', 'data')

Write-Host "External: $ExternalPath" -ForegroundColor Cyan
Write-Host "Workspace: $ws" -ForegroundColor Cyan
Write-Host "Mode: $Mode  Direction: $Direction  Purge: $($Purge.IsPresent)" -ForegroundColor Cyan

if ($Mode -eq 'Preview') {
    Write-Host "[Preview] External → Workspace" -ForegroundColor Yellow
    Do-RoboCopyPreview -Source $ExternalPath -Target $ws -ExcludeDirs $excludeCommon | Out-File -Encoding UTF8 -FilePath "_diff-external_to_ws.txt"
    Write-Host "Saved: _diff-external_to_ws.txt" -ForegroundColor Green

    Write-Host "[Preview] Workspace → External" -ForegroundColor Yellow
    Do-RoboCopyPreview -Source $ws -Target $ExternalPath -ExcludeDirs $excludeWsToExt | Out-File -Encoding UTF8 -FilePath "_diff-ws_to_external.txt"
    Write-Host "Saved: _diff-ws_to_external.txt" -ForegroundColor Green
    exit 0
}

# Apply
$backupDir = New-Backup -WorkspaceRoot $ws
Write-Host "Backup: $backupDir" -ForegroundColor Green

if ($Direction -eq 'ExternalToWorkspace') {
    # Backup current workspace before applying changes from external
    Copy-Item -Path (Join-Path $ws '*') -Destination $backupDir -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "[Apply] External → Workspace" -ForegroundColor Yellow
    Do-RoboCopyApply -Source $ExternalPath -Target $ws -Mirror:$Purge -ExcludeDirs $excludeCommon | Out-Null
}
else {
    # Backup snapshot of external before pushing workspace changes (especially if purge enabled)
    Copy-Item -Path (Join-Path $ExternalPath '*') -Destination $backupDir -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "[Apply] Workspace → External" -ForegroundColor Yellow
    Do-RoboCopyApply -Source $ws -Target $ExternalPath -Mirror:$Purge -ExcludeDirs $excludeWsToExt | Out-Null
}

Write-Host "Sync complete." -ForegroundColor Green
Write-Host "Backup available at: $backupDir" -ForegroundColor Green
