# ==============================================================================
# Installation Verification & PATH Setup Script
# ==============================================================================
# Project Creator: Herman Swanepoel
# Version: 1.0
# Description: Verifies PuTTY and WinSCP installation and adds to PATH
# ==============================================================================

#Requires -Version 7.0

function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Color
}

function Test-InPath {
    param([string]$Command)

    $null -ne (Get-Command $Command -ErrorAction SilentlyContinue)
}

function Add-ToPath {
    param(
        [string]$Directory,
        [string]$Scope = "User"
    )

    $currentPath = [Environment]::GetEnvironmentVariable("Path", $Scope)

    if ($currentPath -notlike "*$Directory*") {
        $newPath = "$currentPath;$Directory"
        [Environment]::SetEnvironmentVariable("Path", $newPath, $Scope)

        # Update current session
        $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                    [Environment]::GetEnvironmentVariable("Path", "User")

        return $true
    }

    return $false
}

# ==============================================================================
# MAIN
# ==============================================================================

Write-Host ""
Write-ColorOutput "╔════════════════════════════════════════════════════════════╗" "Cyan"
Write-ColorOutput "║     PuTTY & WinSCP Installation Verification              ║" "Cyan"
Write-ColorOutput "╚════════════════════════════════════════════════════════════╝" "Cyan"
Write-Host ""

# Check PuTTY
Write-ColorOutput "Checking PuTTY..." "Yellow"

$puttyPaths = @(
    "C:\Program Files\PuTTY\putty.exe",
    "C:\Program Files (x86)\PuTTY\putty.exe",
    "$env:LOCALAPPDATA\Programs\PuTTY\putty.exe"
)

$puttyFound = $false
$puttyPath = $null

foreach ($path in $puttyPaths) {
    if (Test-Path $path) {
        $puttyFound = $true
        $puttyPath = Split-Path $path -Parent
        Write-ColorOutput "  ✓ PuTTY found: $path" "Green"
        break
    }
}

if (-not $puttyFound) {
    Write-ColorOutput "  ✗ PuTTY not found" "Red"
    Write-ColorOutput "  Install with: winget install -e --id PuTTY.PuTTY" "Yellow"
} else {
    if (Test-InPath "putty") {
        Write-ColorOutput "  ✓ PuTTY is in PATH" "Green"
    } else {
        Write-ColorOutput "  ⚠ PuTTY not in PATH, adding..." "Yellow"
        if (Add-ToPath -Directory $puttyPath -Scope "User") {
            Write-ColorOutput "  ✓ Added PuTTY to PATH" "Green"
        } else {
            Write-ColorOutput "  ℹ PuTTY already in PATH" "Cyan"
        }
    }
}

Write-Host ""

# Check WinSCP
Write-ColorOutput "Checking WinSCP..." "Yellow"

$winscpPaths = @(
    "C:\Program Files\WinSCP\WinSCP.exe",
    "C:\Program Files (x86)\WinSCP\WinSCP.exe",
    "$env:LOCALAPPDATA\Programs\WinSCP\WinSCP.exe"
)

$winscpFound = $false
$winscpPath = $null

foreach ($path in $winscpPaths) {
    if (Test-Path $path) {
        $winscpFound = $true
        $winscpPath = Split-Path $path -Parent
        Write-ColorOutput "  ✓ WinSCP found: $path" "Green"
        break
    }
}

if (-not $winscpFound) {
    Write-ColorOutput "  ✗ WinSCP not found" "Red"
    Write-ColorOutput "  Install with: winget install -e --id WinSCP.WinSCP" "Yellow"
} else {
    if (Test-InPath "winscp") {
        Write-ColorOutput "  ✓ WinSCP is in PATH" "Green"
    } else {
        Write-ColorOutput "  ⚠ WinSCP not in PATH, adding..." "Yellow"
        if (Add-ToPath -Directory $winscpPath -Scope "User") {
            Write-ColorOutput "  ✓ Added WinSCP to PATH" "Green"
        } else {
            Write-ColorOutput "  ℹ WinSCP already in PATH" "Cyan"
        }
    }
}

Write-Host ""

# Summary
Write-ColorOutput "═══════════════════════════════════════════════════════════" "Cyan"
Write-ColorOutput "SUMMARY" "Cyan"
Write-ColorOutput "═══════════════════════════════════════════════════════════" "Cyan"

if ($puttyFound -and $winscpFound) {
    Write-ColorOutput "✓ All tools installed and configured!" "Green"
    Write-Host ""
    Write-ColorOutput "Next steps:" "Yellow"
    Write-ColorOutput "  1. Copy config.example.ps1 to config.ps1" "White"
    Write-ColorOutput "  2. Update config.ps1 with your credentials" "White"
    Write-ColorOutput "  3. Run: .\devops-ssh-connect.ps1" "White"
} else {
    Write-ColorOutput "⚠ Some tools are missing. Install them and run this script again." "Yellow"
}

Write-Host ""
