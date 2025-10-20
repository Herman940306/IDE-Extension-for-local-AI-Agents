# WSL2 + Docker Troubleshooting & Recovery Guide

**Project Creator:** Herman Swanepoel  
**Version:** 1.0-ENTERPRISE  
**Date:** 2025-10-19  
**Mode:** AURA-DEV GODMODE - DEVOPS + SECOPS

---

## 🎯 Purpose

This guide addresses the critical issue where Windows crashes with a black screen when enabling the **Virtual Machine Platform** feature required for WSL2 and Docker.

**Reference:** [Microsoft Community Issue #3985493](https://learn.microsoft.com/en-us/answers/questions/3985493/windows-crash-when-virtual-machine-platform-was-en)

---

## 🚨 Critical Issue: Black Screen Crash During VM Platform Enablement

### Symptoms
- System reboots after enabling Virtual Machine Platform
- Update process reaches ~15% then reboots again
- Black screen appears after BIOS (screen active but showing black pixels)
- System becomes unresponsive or stuck in boot loop

### Root Causes
1. **Virtualization disabled in BIOS/UEFI**
2. **Outdated BIOS/UEFI firmware**
3. **Incompatible or outdated chipset drivers**
4. **Conflicting virtualization software**
5. **Hardware incompatibility (CPU doesn't support required features)**
6. **Secure Boot conflicts**

---

## 📋 Pre-Installation Checklist

### Before You Start

Run full diagnostics:
```powershell
# Run as Administrator
.\scripts\WSL-Docker-SafeMode-Recovery.ps1 -Mode FullDiagnostics
```

This will check:
- ✅ CPU virtualization support (VT-x/AMD-V)
- ✅ BIOS settings status
- ✅ Windows version compatibility
- ✅ SLAT (Second Level Address Translation) support
- ✅ Hyper-V availability
- ✅ Current feature states

### System Requirements

| Requirement | Minimum | Recommended |
|------------|---------|-------------|
| Windows Version | Windows 10 Build 19041+ | Windows 11 22H2+ |
| RAM | 4 GB | 8 GB+ |
| CPU | 64-bit with VT-x/AMD-V | Multi-core with SLAT |
| Disk Space | 20 GB free | 50 GB+ free |
| BIOS | Virtualization enabled | Latest firmware |

---

## 🔧 Step-by-Step Safe Installation Process

### Phase 1: Prepare Your System

#### 1.1 Update Windows
```powershell
# Open Windows Update
ms-settings:windowsupdate

# Install ALL available updates
# Restart if required
# Check again until no updates remain
```

#### 1.2 Update BIOS/UEFI

**⚠️ CRITICAL: Backup all data before BIOS update!**

1. Identify your system:
   ```powershell
   Get-CimInstance -ClassName Win32_ComputerSystem | Select-Object Manufacturer, Model
   Get-CimInstance -ClassName Win32_BIOS | Select-Object SMBIOSBIOSVersion
   ```

2. Visit manufacturer's website:
   - **Dell:** https://www.dell.com/support
   - **HP:** https://support.hp.com
   - **Lenovo:** https://support.lenovo.com
   - **ASUS:** https://www.asus.com/support
   - **MSI:** https://www.msi.com/support

3. Download latest BIOS/UEFI update
4. Follow manufacturer's update instructions carefully
5. **Do not interrupt the update process**

#### 1.3 Update Chipset & Virtualization Drivers

Download and install from manufacturer:
- Chipset drivers
- Intel Management Engine (ME) drivers
- AMD chipset drivers
- Virtualization-related firmware

#### 1.4 Enable Virtualization in BIOS

**Common BIOS keys:** F2, F10, F12, Del, Esc (press repeatedly during boot)

**Settings to enable:**

**Intel Systems:**
- Intel Virtualization Technology (VT-x)
- Intel VT for Directed I/O (VT-d)

**AMD Systems:**
- SVM Mode (Secure Virtual Machine)
- AMD IOMMU

**Common BIOS paths by manufacturer:**

| Manufacturer | Path |
|--------------|------|
| **Dell** | Advanced > Virtualization > Intel Virtualization Technology |
| **HP** | Advanced > System Options > Virtualization Technology |
| **Lenovo** | Configuration > Intel Virtual Technology |
| **ASUS** | Advanced > CPU Configuration > Intel Virtualization Technology |
| **MSI** | OC > CPU Features > Intel Virtualization Tech |

**After enabling:**
1. Save and Exit (usually F10)
2. Allow system to restart
3. Boot into Windows normally
4. Verify: Run diagnostics again

### Phase 2: Create Safety Net

#### 2.1 Create System Restore Point
```powershell
# Run as Administrator
.\scripts\WSL-Docker-SafeMode-Recovery.ps1 -Mode CreateRestorePoint
```

#### 2.2 Backup Important Data
- Documents
- Projects
- Configuration files
- Browser bookmarks/passwords

### Phase 3: Safe Feature Enablement

#### 3.1 Run Safe Installation Script
```powershell
# Run as Administrator
.\scripts\WSL-Docker-Setup-Enterprise.ps1 -Mode FullSetup
```

This script:
- ✅ Validates system requirements
- ✅ Cleans previous installations
- ✅ Enables features gradually
- ✅ Provides detailed logging
- ✅ Offers rollback options

#### 3.2 Monitor First Restart

**IMPORTANT:** After enabling Virtual Machine Platform:
- System will restart automatically
- Update process will run (may reach 15-30%)
- **Normal:** System restarts and boots normally
- **Problem:** Black screen or boot loop

**If black screen occurs:**
1. Wait 5 minutes for automatic recovery
2. If no recovery, force power off (hold power button 10s)
3. Proceed to Recovery Process below

---

## 🚑 Recovery Process for Crashed Systems

### Step 1: Boot into Safe Mode

**Method A: From lock screen**
1. Hold `Shift` key
2. Click `Restart`
3. Navigate: Troubleshoot > Advanced Options > Startup Settings > Restart
4. Press `F4` or `F5` to enter Safe Mode

**Method B: Force Safe Mode (if can't reach lock screen)**
1. Force power off during boot (3 times)
2. Windows will enter Automatic Repair
3. Select: Advanced Options > Startup Settings > Restart
4. Press `F4` for Safe Mode

### Step 2: Disable Virtualization Features (in Safe Mode)

```powershell
# Run as Administrator in Safe Mode
.\scripts\WSL-Docker-SafeMode-Recovery.ps1 -Mode DisableAndRecover
```

Or manually:
```powershell
# Shutdown WSL
wsl --shutdown

# Disable features
dism.exe /online /disable-feature /featurename:VirtualMachinePlatform /norestart
dism.exe /online /disable-feature /featurename:Microsoft-Windows-Subsystem-Linux /norestart

# Restart
Restart-Computer
```

### Step 3: Fix Root Cause

After system is stable:

1. **Check BIOS settings again**
   - Ensure virtualization is enabled
   - Check for BIOS updates

2. **Update all drivers**
   ```powershell
   # Use Windows Update for drivers
   # Or download from manufacturer
   ```

3. **Check Windows integrity**
   ```powershell
   # Run as Administrator
   DISM /Online /Cleanup-Image /RestoreHealth
   sfc /scannow
   ```

4. **Verify no conflicting software**
   - VirtualBox (may conflict)
   - VMware Workstation (may conflict)
   - Older Hyper-V settings

### Step 4: Retry with Safe Enablement

```powershell
# After fixes, try again
.\scripts\WSL-Docker-SafeMode-Recovery.ps1 -Mode SafeEnable
```

---

## 🔍 Advanced Troubleshooting

### Issue: "Unsupported 16-Bit Application" Error

**Symptoms:** Error message about `wslsetup.exe` being incompatible with 64-bit Windows

**Cause:** Corrupted or outdated 32-bit WSL installer in temp folder

**Fix:**
```powershell
# Run as Administrator

# Remove corrupted files
Remove-Item "$env:TEMP\wsl*" -Recurse -Force -ErrorAction SilentlyContinue

# Download and install proper 64-bit WSL
$msiPath = "$env:TEMP\wsl.msi"
Invoke-WebRequest -Uri "https://aka.ms/wsl-x64" -OutFile $msiPath -UseBasicParsing
Start-Process msiexec.exe -ArgumentList "/i `"$msiPath`" /passive /norestart" -Wait

# Verify installation
wsl --version
```

### Issue: "System cannot find the file specified"

**Symptoms:** `wsl` command not found or not in PATH

**Fix:**
```powershell
# Verify wsl.exe exists
Test-Path "$env:SystemRoot\System32\wsl.exe"

# If missing, reinstall WSL
$msiPath = "$env:TEMP\wsl.msi"
Invoke-WebRequest -Uri "https://aka.ms/wsl-x64" -OutFile $msiPath -UseBasicParsing
Start-Process msiexec.exe -ArgumentList "/i `"$msiPath`" /passive /norestart" -Wait

# Restart PowerShell
```

### Issue: Docker fails in Ubuntu after installation

**Symptoms:** Docker installed but won't run

**Fix:**
```bash
# Inside WSL Ubuntu

# Check Docker status
sudo systemctl status docker

# If not running, start it
sudo systemctl start docker

# Add user to docker group (if not done)
sudo usermod -aG docker $USER

# Log out and back in, then test
docker run hello-world

# If still failing, check permissions
sudo chmod 666 /var/run/docker.sock
```

### Issue: WSL2 kernel not updating

**Symptoms:** WSL --version shows old kernel

**Fix:**
```powershell
# Download kernel update
$kernelUrl = "https://wslstorestorage.blob.core.windows.net/wslblob/wsl_update_x64.msi"
$kernelPath = "$env:TEMP\wsl_update_x64.msi"
Invoke-WebRequest -Uri $kernelUrl -OutFile $kernelPath -UseBasicParsing
Start-Process msiexec.exe -ArgumentList "/i `"$kernelPath`" /quiet /norestart" -Wait

# Set WSL2 as default
wsl --set-default-version 2
```

---

## 📊 Diagnostic Commands Reference

### System Information
```powershell
# OS and build
Get-CimInstance Win32_OperatingSystem | Select-Object Caption, Version, BuildNumber

# CPU info
Get-CimInstance Win32_Processor | Select-Object Name, NumberOfCores, VirtualizationFirmwareEnabled

# Virtualization status
Get-CimInstance -ClassName Win32_ComputerSystem | Select-Object HypervisorPresent

# BIOS info
Get-CimInstance Win32_BIOS | Select-Object SMBIOSBIOSVersion, ReleaseDate
```

### WSL Commands
```powershell
# WSL version
wsl --version

# List distributions
wsl --list --verbose

# Check distribution status
wsl --status

# Set default version
wsl --set-default-version 2

# Update WSL
wsl --update

# Shutdown WSL
wsl --shutdown
```

### Windows Features
```powershell
# Check feature status
dism.exe /online /Get-FeatureInfo /FeatureName:Microsoft-Windows-Subsystem-Linux
dism.exe /online /Get-FeatureInfo /FeatureName:VirtualMachinePlatform

# List all Hyper-V features
Get-WindowsOptionalFeature -Online | Where-Object {$_.FeatureName -like "*Hyper*"}
```

### Docker in WSL
```bash
# Docker version
docker --version

# Docker info
docker info

# Test Docker
sudo docker run hello-world

# Check Docker service
sudo systemctl status docker

# Docker logs
sudo journalctl -u docker
```

---

## 🛠️ Quick Reference: Script Usage

### Full Diagnostics
```powershell
.\scripts\WSL-Docker-SafeMode-Recovery.ps1 -Mode FullDiagnostics
```

### Safe Installation
```powershell
.\scripts\WSL-Docker-Setup-Enterprise.ps1 -Mode FullSetup
```

### Recovery Mode (Safe Mode)
```powershell
.\scripts\WSL-Docker-SafeMode-Recovery.ps1 -Mode DisableAndRecover
```

### Cleanup Only
```powershell
.\scripts\WSL-Docker-Setup-Enterprise.ps1 -Mode CleanupOnly
```

### Validation Only
```powershell
.\scripts\WSL-Docker-Setup-Enterprise.ps1 -Mode Validate -DistroName Ubuntu-24.04
```

---

## ✅ Post-Installation Validation

### Verify WSL2
```powershell
# Check WSL version
wsl --version

# Should show:
# WSL version: 2.x.x.x
# Kernel version: 5.15.x.x
```

### Verify Ubuntu
```powershell
# List distributions
wsl --list --verbose

# Should show Ubuntu-24.04 with VERSION 2
```

### Verify Docker
```bash
# Inside WSL
docker --version
docker run hello-world

# Should pull and run successfully
```

---

## 🔐 Security Considerations

### Firewall Rules
After installation, configure Windows Firewall:
```powershell
# Allow WSL network
New-NetFirewallRule -DisplayName "WSL2" -Direction Inbound -Action Allow
```

### User Permissions
```bash
# Inside WSL - verify docker group
groups

# Should include 'docker'
```

### Network Configuration
```bash
# Inside WSL - check network
ip addr show

# Should show eth0 with IP address
```

---

## 📞 Additional Resources

### Official Documentation
- [WSL Documentation](https://docs.microsoft.com/en-us/windows/wsl/)
- [Docker Documentation](https://docs.docker.com/desktop/wsl/)
- [Hyper-V Documentation](https://docs.microsoft.com/en-us/virtualization/hyper-v-on-windows/)

### Community Support
- [WSL GitHub Issues](https://github.com/microsoft/WSL/issues)
- [Docker Community Forums](https://forums.docker.com/)
- [Microsoft Q&A](https://learn.microsoft.com/en-us/answers/)

### Hardware-Specific Guides
- Search: "[Your PC Model] enable virtualization BIOS"
- Check manufacturer support forums
- Contact manufacturer support if issues persist

---

## 🎯 Success Criteria

Your installation is successful when:
- ✅ `wsl --version` shows WSL 2.x.x
- ✅ `wsl --list --verbose` shows Ubuntu-24.04 VERSION 2
- ✅ `wsl -d Ubuntu-24.04` launches successfully
- ✅ `docker --version` works inside WSL
- ✅ `docker run hello-world` completes successfully
- ✅ No system crashes or black screens
- ✅ System remains stable after reboots

---

## 📝 Troubleshooting Log Template

When seeking help, provide:

```
System Information:
- OS: [Windows 11 Pro 22H2, Build 22621]
- CPU: [Intel i7-12700K]
- RAM: [32 GB]
- Virtualization in BIOS: [Enabled/Disabled]
- BIOS Version: [X.Y.Z]

Issue Description:
[Describe the problem]

Steps Taken:
1. [What you tried]
2. [Results]

Error Messages:
[Exact error text or screenshot]

Log Location:
%TEMP%\wsl-docker-setup.log
%TEMP%\wsl-safemode-recovery.log
```

---

## 🏆 AURA-DEV GODMODE Compliance

This solution follows enterprise standards:
- ✅ Zero Technical Debt (Clean automation, comprehensive docs)
- ✅ Security by Design (Safe Mode recovery, system restore points)
- ✅ Automation Over Manual Labor (Scripted diagnostics and installation)
- ✅ Observability Is Law (Detailed logging, diagnostics)
- ✅ Global Scalability First (Works across hardware configurations)

---

**Created by:** Herman Swanepoel  
**AURA-DEV OMNIDEV GODMODE** - Enterprise DevOps & Security Operations  
**Date:** 2025-10-19  
**Version:** 1.0-ENTERPRISE
