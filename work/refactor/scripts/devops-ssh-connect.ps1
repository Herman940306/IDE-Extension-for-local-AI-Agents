# ==============================================================================
# AURA-DEV DevOps WinSCP Connection Script
# ==============================================================================
# Project Creator: Herman Swanepoel
# Version: 2.0
# PowerShell: 7.5.3+
# Description: WinSCP auto-login for file management
# ==============================================================================

#Requires -Version 7.0

# ==============================================================================
# CONFIGURATION
# ==============================================================================

# Load configuration from config.ps1
$configPath = Join-Path $PSScriptRoot "config.ps1"
if (Test-Path $configPath) {
    $Config = & $configPath
} else {
    Write-Error "Config file not found: $configPath"
    exit 1
}

# ==============================================================================
# FUNCTIONS
# ==============================================================================

function Write-Log {
    param(
        [string]$Message,
        [ValidateSet('Info', 'Success', 'Warning', 'Error')]
        [string]$Level = 'Info'
    )

    $colors = @{
        'Info'    = 'Cyan'
        'Success' = 'Green'
        'Warning' = 'Yellow'
        'Error'   = 'Red'
    }

    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$timestamp] " -NoNewline -ForegroundColor Gray
    Write-Host "[$Level] " -NoNewline -ForegroundColor $colors[$Level]
    Write-Host $Message
}

function Test-ApplicationInstalled {
    param([string]$Path, [string]$AppName)

    if (Test-Path $Path) {
        Write-Log "✓ $AppName found at: $Path" -Level Success
        return $true
    } else {
        Write-Log "✗ $AppName not found at: $Path" -Level Error
        return $false
    }
}

function Start-WinSCPSession {
    param($Config)

    Write-Log "Starting WinSCP session..." -Level Info

    try {
        # Ensure local directory exists
        if (-not (Test-Path $Config.LocalProjectDir)) {
            Write-Log "Creating local project directory: $($Config.LocalProjectDir)" -Level Warning
            New-Item -ItemType Directory -Path $Config.LocalProjectDir -Force | Out-Null
        }

        # Simple WinSCP connection - just open GUI and connect
        # User can navigate to desired directory manually
        $connectionString = "scp://$($Config.Username):$($Config.Password)@$($Config.ServerIP)"

        Write-Log "Created WinSCP connection string" -Level Success

        # WinSCP arguments for GUI mode
        $winscpArgs = @(
            $connectionString
        )

        # Start WinSCP GUI
        Start-Process -FilePath $Config.WinSCPPath -ArgumentList $winscpArgs -WorkingDirectory $Config.LocalProjectDir
        Write-Log "✓ WinSCP GUI session launched successfully" -Level Success
        Write-Log "  Remote: $($Config.RemoteProjectDir)" -Level Info
        Write-Log "  Local: $($Config.LocalProjectDir)" -Level Info

        return $true
    }
    catch {
        Write-Log "✗ Failed to start WinSCP: $($_.Exception.Message)" -Level Error
        return $false
    }
}

function Test-NetworkConnectivity {
    param([string]$ServerIP)

    Write-Log "Testing network connectivity to $ServerIP..." -Level Info

    try {
        $ping = Test-Connection -ComputerName $ServerIP -Count 2 -Quiet

        if ($ping) {
            Write-Log "✓ Server is reachable" -Level Success
            return $true
        } else {
            Write-Log "✗ Server is not reachable" -Level Error
            return $false
        }
    }
    catch {
        Write-Log "✗ Network test failed: $($_.Exception.Message)" -Level Error
        return $false
    }
}

function Show-Banner {
    Write-Host ""
    Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║                                                            ║" -ForegroundColor Cyan
    Write-Host "║          AURA-DEV DevOps WinSCP Launcher                  ║" -ForegroundColor Cyan
    Write-Host "║                                                            ║" -ForegroundColor Cyan
    Write-Host "║  WinSCP Auto-Login for File Management                    ║" -ForegroundColor Cyan
    Write-Host "║                                                            ║" -ForegroundColor Cyan
    Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host ""
}



# ==============================================================================
# MAIN EXECUTION
# ==============================================================================

function Main {
    Show-Banner

    Write-Log "Initializing DevOps SSH Connection Manager..." -Level Info
    Write-Log "Target: $($Config.Username)@$($Config.ServerIP)" -Level Info
    Write-Log "Remote Directory: $($Config.RemoteProjectDir)" -Level Info
    Write-Log "Local Directory: $($Config.LocalProjectDir)" -Level Info
    Write-Host ""

    # Pre-flight checks
    Write-Log "=== PRE-FLIGHT CHECKS ===" -Level Info

    $winscpOk = Test-ApplicationInstalled -Path $Config.WinSCPPath -AppName "WinSCP"
    $networkOk = Test-NetworkConnectivity -ServerIP $Config.ServerIP

    Write-Host ""

    if (-not ($winscpOk -and $networkOk)) {
        Write-Log "Pre-flight checks failed. Aborting." -Level Error
        return 1
    }

    Write-Log "✓ All pre-flight checks passed" -Level Success
    Write-Host ""

    # Launch WinSCP
    Write-Log "=== LAUNCHING WINSCP ===" -Level Info

    $winscpSuccess = Start-WinSCPSession -Config $Config

    Write-Host ""

    if ($winscpSuccess) {
        Write-Log "=== SUCCESS ===" -Level Success
        Write-Log "WinSCP launched successfully!" -Level Success
        Write-Log "Connected to: $($Config.ServerIP)" -Level Info
        Write-Log "Navigate to: $($Config.RemoteProjectDir)" -Level Info
    } else {
        Write-Log "=== FAILED ===" -Level Error
        Write-Log "WinSCP failed to launch. Check logs above." -Level Error
    }

    Write-Host ""

    Write-Log "Script execution complete." -Level Info
    Write-Host ""

    return 0
}

# ==============================================================================
# ENTRY POINT
# ==============================================================================

try {
    $exitCode = Main
    exit $exitCode
}
catch {
    Write-Log "FATAL ERROR: $($_.Exception.Message)" -Level Error
    Write-Log "Stack Trace: $($_.ScriptStackTrace)" -Level Error
    exit 1
}
finally {
    # Nothing to cleanup
}

# ==============================================================================
# END OF SCRIPT
# ==============================================================================
