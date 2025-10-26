#Requires -Version 5.1
<#!
Purpose: Robust elevated launcher for WSL/Docker FullSetup.
- Self-elevates if needed
- Starts transcript logging to logs/ with timestamp
- Sets working directory to repo root
- Executes WSL-Docker-Setup-Enterprise.ps1 -Mode FullSetup
- Keeps window open at the end for review
!#>

param(
    [ValidateSet('FullSetup','InstallOnly','CleanupOnly','DiagnosticsOnly','Validate')]
    [string]$Mode = 'FullSetup'
)

function Test-IsAdmin {
    $currentIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentIdentity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Get-PwshPath {
    $candidates = @()
    foreach ($name in 'pwsh','powershell') {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue
        if ($null -ne $cmd) {
            $path = $cmd.Path
            if (-not $path) { $path = $cmd.Source }
            if ($path) { $candidates += $path }
        }
    }
    if ($candidates.Count -gt 0) { return $candidates[0] }
    throw 'Neither pwsh nor Windows PowerShell was found in PATH.'
}

try {
    # Determine script path (PSCommandPath may be null in some invocation contexts)
    $scriptPath = $PSCommandPath
    if (-not $scriptPath -and $MyInvocation -and $MyInvocation.MyCommand) {
        $scriptPath = $MyInvocation.MyCommand.Path
    }
    if (-not $scriptPath) {
        throw 'Cannot determine the current script path.'
    }

    # Determine repo root (this script is under scripts/)
    $scriptDir = Split-Path -LiteralPath $scriptPath -Parent
    $repoRoot = Split-Path -LiteralPath $scriptDir -Parent

    if (-not (Test-IsAdmin)) {
        Write-Host '[i] Elevation required. Relaunching as Administrator...' -ForegroundColor Yellow
    $shell = Get-PwshPath
    $launchArgs = @('-NoProfile','-ExecutionPolicy','Bypass','-NoExit','-File', $PSCommandPath, '-Mode', $Mode)
    Start-Process -FilePath $shell -ArgumentList $launchArgs -Verb RunAs
        Write-Host '[i] Admin window launched. You can close this window.' -ForegroundColor Yellow
        return
    }

    # Ensure logs directory exists
    $logsDir = Join-Path -Path $repoRoot -ChildPath 'logs'
    if (-not (Test-Path -LiteralPath $logsDir)) { New-Item -ItemType Directory -Path $logsDir -Force | Out-Null }

    $timestamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    $logPath = Join-Path -Path $logsDir -ChildPath "WSL-Install_${timestamp}.log"
    try {
        if ($PSVersionTable.PSVersion.Major -ge 6) {
            Start-Transcript -Path $logPath -Append -ErrorAction Stop
        } else {
            Start-Transcript -Path $logPath -ErrorAction Stop
        }
    } catch {
        Write-Warning "Could not start transcript: $_"
    }

    Write-Host '=== WSL + Docker Full Setup (Elevated) ===' -ForegroundColor Cyan
    Write-Host "Repo: $repoRoot" -ForegroundColor DarkGray
    Set-Location -LiteralPath $repoRoot

    $enterpriseScript = Join-Path -Path $repoRoot -ChildPath 'scripts/WSL-Docker-Setup-Enterprise.ps1'
    if (-not (Test-Path -LiteralPath $enterpriseScript)) {
        throw "Enterprise setup script not found at: $enterpriseScript"
    }

    Write-Host "[>] Running: $enterpriseScript -Mode $Mode" -ForegroundColor Green
    & $enterpriseScript -Mode $Mode

    $exitCode = $LASTEXITCODE
    Write-Host "[i] Script completed. ExitCode: $exitCode" -ForegroundColor Cyan
    Write-Host "[i] Log saved to: $logPath" -ForegroundColor Cyan

    # Keep window open for review
    Write-Host
    Read-Host 'Press Enter to close this window'
}
catch {
    Write-Error $_
    Write-Host '--- Exception Details ---' -ForegroundColor Red
    if ($_.Exception) {
        Write-Host "Type      : $($_.Exception.GetType().FullName)" -ForegroundColor Red
        Write-Host "Message   : $($_.Exception.Message)" -ForegroundColor Red
    }
    if ($_.InvocationInfo) {
        Write-Host "Command   : $($_.InvocationInfo.MyCommand)" -ForegroundColor Red
        Write-Host "Script    : $($_.InvocationInfo.ScriptName)" -ForegroundColor Red
        Write-Host "Line      : $($_.InvocationInfo.Line)" -ForegroundColor Red
        Write-Host "Pos       : $($_.InvocationInfo.PositionMessage.Trim())" -ForegroundColor Red
    }
    Write-Host '-------------------------' -ForegroundColor Red
    Write-Host
    Read-Host 'An error occurred. Press Enter to close this window'
}
finally {
    try { Stop-Transcript | Out-Null } catch { }
}
