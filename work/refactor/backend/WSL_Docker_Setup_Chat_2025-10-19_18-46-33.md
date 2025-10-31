# WSL + Docker Full Setup and Troubleshooting Guide (Chat Transcript)

**Date:** 2025-10-19
**User:** Wolf
**Environment:** Windows 11 Pro 25H2, BIOS E7B17IMS.AD0, ME 12.0.0.93.2331
**PowerShell Version:** 7.5.3

---

## 🧾 Summary of Goals

- Fully remove all traces of WSL and Docker.
- Reinstall WSL2 and Ubuntu 24.04 for Docker development.
- Provide robust, repeatable PowerShell and Bash scripts.
- Ensure 100% success from a clean Windows state.

---

## 🧹 Step 1 — Full Cleanup Script

User requested a PowerShell script that removes all WSL and Docker components before reinstall.

**Reset-WSL-Docker.ps1:**

```powershell
# Run as Administrator
Write-Host "=== Resetting all WSL & Docker components ==="

# Stop services
Stop-Service -Name "com.docker.service" -ErrorAction SilentlyContinue
wsl --shutdown

# Unregister all WSL distros
wsl --list --all --quiet | ForEach-Object { wsl --unregister $_ }

# Uninstall features
dism.exe /online /disable-feature /featurename:VirtualMachinePlatform /norestart
dism.exe /online /disable-feature /featurename:Microsoft-Windows-Subsystem-Linux /norestart

# Remove WSL/Docker packages and leftovers
Get-Package *docker* -ErrorAction SilentlyContinue | Uninstall-Package -Force -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "$env:LOCALAPPDATA\Docker" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "$env:ProgramData\Docker" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "$env:ProgramFiles\Docker" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "$env:USERPROFILE\.docker" -ErrorAction SilentlyContinue

# Cleanup WSL data
Remove-Item -Recurse -Force "$env:LOCALAPPDATA\Packages\Canonical*" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force "$env:ProgramData\Microsoft\Windows\Subsystems" -ErrorAction SilentlyContinue

Write-Host "✅ Cleanup complete. Please reboot before reinstalling."
```

---

## 🧰 Step 2 — WSL & Docker Reinstall Script

**Install-WSL-Docker.ps1 (fixed version):**

```powershell
# Run as Administrator
Write-Host "=== Starting WSL2 + Docker Setup ==="

# 1. Enable required Windows features
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart

# 2. Set WSL2 as default
wsl --set-default-version 2

# 3. Install Ubuntu 24.04
wsl --install -d Ubuntu-24.04

# 4. Copy and execute Docker setup script
$tempScript = "$env:TEMP\setup_docker_ubuntu.sh"
@"
#!/bin/bash
sudo apt update -y
sudo apt install -y ca-certificates curl gnupg lsb-release apt-transport-https
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=\$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \$(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update -y
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker \$USER
sudo systemctl enable docker
"@ | Out-File -Encoding utf8 -FilePath $tempScript

# Copy into WSL safely
Get-Content -Raw $tempScript | wsl -d Ubuntu-24.04 -- bash -c "cat > /tmp/setup_docker_ubuntu.sh"
wsl -d Ubuntu-24.04 -- chmod +x /tmp/setup_docker_ubuntu.sh

# Run it inside WSL
wsl -d Ubuntu-24.04 -- bash /tmp/setup_docker_ubuntu.sh

Write-Host "✅ Installation complete. Reboot and run 'docker run hello-world'."
```

---

## 🧩 Step 3 — Troubleshooting “Unsupported 16-Bit Application” Error

Error:

> Unsupported 16-Bit Application — The program or feature ‘wslsetup.exe’ cannot start or run due to incompatibility with 64-bit versions of Windows.

✅ Root cause: Old or corrupted `wslsetup.exe` (32-bit) in temp folder.
✅ Fix: Manually reinstall proper 64-bit WSL MSI from Microsoft.

```powershell
$msiPath = "$env:TEMP\wsl.msi"
Invoke-WebRequest -Uri "https://aka.ms/wsl-x64" -OutFile $msiPath -UseBasicParsing
Start-Process msiexec.exe -ArgumentList "/i `"$msiPath`" /passive /norestart" -Wait
```

Then verify:

```powershell
wsl --version
```

If you get `system cannot find the file specified`, it means WSL isn’t linked in PATH.

---

## 🧠 Step 4 — Re-register and Verify WSL

Run as Administrator:

```powershell
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart

$system32 = "$env:SystemRoot\System32"
if (-not (Test-Path "$system32\wsl.exe")) {
    Invoke-WebRequest -Uri "https://aka.ms/wsl-x64" -OutFile "$env:TEMP\wsl.msi" -UseBasicParsing
    Start-Process msiexec.exe -ArgumentList "/i `"$env:TEMP\wsl.msi`" /passive /norestart" -Wait
}
```

Reboot, then run:

```powershell
wsl --version
```

Expected result:

```
WSL version: 2.x.x.x
Kernel version: 5.15.x.x
Windows version: 10.0.26100.x
```

---

## ✅ Next Step: Install Ubuntu 24.04

```powershell
wsl --install -d Ubuntu-24.04
```

After first launch, set username and password.

---

## 🐳 Step 5 — Verify Docker in Ubuntu

Inside Ubuntu:

```bash
sudo docker version
sudo docker run hello-world
```

If both succeed, Docker + WSL2 + Ubuntu are fully operational.
