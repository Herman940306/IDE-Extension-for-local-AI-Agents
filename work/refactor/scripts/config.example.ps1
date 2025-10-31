# ==============================================================================
# Configuration Template
# ==============================================================================
# Project Creator: Herman Swanepoel
# Copy this file to config.ps1 and update with your credentials
# Add config.ps1 to .gitignore to keep credentials secure
# ==============================================================================

return @{
    # Server Configuration
    ServerIP = "192.168.1.134"
    Username = "root"
    Password = "YOUR_PASSWORD_HERE"  # NEVER commit this file with real password

    # Directory Paths
    RemoteProjectDir = "/volume2/docker/herman_docker_runner/deploy/runner"
    LocalProjectDir = "C:\Users\Wolf\Projects"

    # Application Paths (auto-detected, override if needed)
    PuTTYPath = "C:\Program Files\PuTTY\putty.exe"
    WinSCPPath = "C:\Users\Wolf\AppData\Local\Programs\WinSCP\WinSCP.exe"
}
