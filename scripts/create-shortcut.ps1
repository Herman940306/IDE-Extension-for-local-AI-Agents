# ==============================================================================
# Desktop Shortcut Creator
# ==============================================================================
# Project Creator: Herman Swanepoel
# Description: Creates a desktop shortcut for one-click SSH connection
# ==============================================================================

#Requires -Version 7.0

$scriptPath = Join-Path $PSScriptRoot "devops-ssh-connect.ps1"
$desktopPath = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktopPath "DevOps SSH Connect.lnk"

$WScriptShell = New-Object -ComObject WScript.Shell
$shortcut = $WScriptShell.CreateShortcut($shortcutPath)

$shortcut.TargetPath = "pwsh.exe"
$shortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`""
$shortcut.WorkingDirectory = $PSScriptRoot
$shortcut.Description = "Connect to DevOps server via PuTTY and WinSCP"
$shortcut.IconLocation = "C:\Program Files\PuTTY\putty.exe,0"

$shortcut.Save()

Write-Host "✓ Desktop shortcut created successfully!" -ForegroundColor Green
Write-Host "  Location: $shortcutPath" -ForegroundColor Cyan
Write-Host ""
Write-Host "Double-click the shortcut to connect!" -ForegroundColor Yellow
