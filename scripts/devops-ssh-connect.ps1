# ==============================================================================
# AURA-DEV DevOps SSH Connection Script
# ==============================================================================
# Project Creator: Herman Swanepoel
# Version: 1.0
# PowerShell: 7.5.3+
# Description: Production-safe PuTTY + WinSCP auto-login with directory navigation
# ==============================================================================

#Requires -Version 7.0

# ==============================================================================
# CONFIGURATION
# ==============================================================================

# Load configuration from config.ps1
$configPath = Join-Path $PSScriptRoot "config.ps1"
if (Test-Path $configPath) {
    $Config = & $configPath
    # Add temp file paths
    $Config.PuTTYCommandFile = "$env:TEMP\putty_commands.txt"
    $Config.WinSCPScriptFile = "$env:TEMP\winscp_script.txt"
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

function Start-PuTTYSession {
    param($Config)
    
    Write-Log "Starting PuTTY session..." -Level Info
    
    try {
        # Create command file for auto-navigation
        # Commands execute after SSH login to navigate to working directory
        $commands = "cd `"$($Config.RemoteProjectDir)`"`nls -la`n"
        
        Set-Content -Path $Config.PuTTYCommandFile -Value $commands -Force -NoNewline
        Write-Log "Created PuTTY command file" -Level Success
        
        # Build PuTTY arguments
        $puttyArgs = @(
            "-ssh"
            "$($Config.Username)@$($Config.ServerIP)"
            "-pw"
            $Config.Password
            "-m"
            $Config.PuTTYCommandFile
        )
        
        # Start PuTTY process with WindowStyle Normal to ensure it's visible
        Start-Process -FilePath $Config.PuTTYPath -ArgumentList $puttyArgs -WindowStyle Normal
        Write-Log "✓ PuTTY session launched successfully" -Level Success
        Write-Log "  Auto-navigating to: $($Config.RemoteProjectDir)" -Level Info
        
        return $true
    }
    catch {
        Write-Log "✗ Failed to start PuTTY: $($_.Exception.Message)" -Level Error
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
        
        # Create WinSCP script file for automated navigation
        # Opens GUI in dual-pane mode with both directories ready for work
        $winscpScript = @"
option batch abort
option confirm off
open scp://$($Config.Username):$($Config.Password)@$($Config.ServerIP)
cd "$($Config.RemoteProjectDir)"
lcd "$($Config.LocalProjectDir)"
"@
        
        Set-Content -Path $Config.WinSCPScriptFile -Value $winscpScript -Force
        Write-Log "Created WinSCP script file" -Level Success
        
        # WinSCP arguments for GUI mode with script
        $winscpArgs = @(
            "/script=$($Config.WinSCPScriptFile)"
        )
        
        # Start WinSCP GUI with working directory set to local project dir
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
    Write-Host "║          AURA-DEV DevOps SSH Connection Manager           ║" -ForegroundColor Cyan
    Write-Host "║                                                            ║" -ForegroundColor Cyan
    Write-Host "║  PuTTY + WinSCP Auto-Login & Directory Navigation         ║" -ForegroundColor Cyan
    Write-Host "║                                                            ║" -ForegroundColor Cyan
    Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host ""
}

function Invoke-Cleanup {
    param($Config)
    
    Write-Log "Cleaning up temporary files..." -Level Info
    
    try {
        if (Test-Path $Config.PuTTYCommandFile) {
            Remove-Item $Config.PuTTYCommandFile -Force
        }
        if (Test-Path $Config.WinSCPScriptFile) {
            Remove-Item $Config.WinSCPScriptFile -Force
        }
        Write-Log "✓ Cleanup complete" -Level Success
    }
    catch {
        Write-Log "Warning: Cleanup failed: $($_.Exception.Message)" -Level Warning
    }
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
    
    $puttyOk = Test-ApplicationInstalled -Path $Config.PuTTYPath -AppName "PuTTY"
    $winscpOk = Test-ApplicationInstalled -Path $Config.WinSCPPath -AppName "WinSCP"
    $networkOk = Test-NetworkConnectivity -ServerIP $Config.ServerIP
    
    Write-Host ""
    
    if (-not ($puttyOk -and $winscpOk -and $networkOk)) {
        Write-Log "Pre-flight checks failed. Aborting." -Level Error
        return 1
    }
    
    Write-Log "✓ All pre-flight checks passed" -Level Success
    Write-Host ""
    
    # Launch sessions
    Write-Log "=== LAUNCHING SESSIONS ===" -Level Info
    
    $puttySuccess = Start-PuTTYSession -Config $Config
    Start-Sleep -Seconds 2  # Stagger launches
    
    $winscpSuccess = Start-WinSCPSession -Config $Config
    
    Write-Host ""
    
    if ($puttySuccess -and $winscpSuccess) {
        Write-Log "=== SUCCESS ===" -Level Success
        Write-Log "Both sessions launched successfully!" -Level Success
        Write-Log "PuTTY: Connected to $($Config.ServerIP) in $($Config.RemoteProjectDir)" -Level Info
        Write-Log "WinSCP: GUI opened with dual-pane view" -Level Info
    } else {
        Write-Log "=== PARTIAL SUCCESS ===" -Level Warning
        Write-Log "Some sessions failed to launch. Check logs above." -Level Warning
    }
    
    Write-Host ""
    
    # Cleanup
    Start-Sleep -Seconds 3
    Invoke-Cleanup -Config $Config
    
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
    # Ensure cleanup even on error
    Invoke-Cleanup -Config $Config
}

# ==============================================================================
# END OF SCRIPT
# ==============================================================================
