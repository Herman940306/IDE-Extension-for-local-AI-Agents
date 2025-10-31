<!-- Placeholder: ANTHROPIC_API_KEY not set. Skipping doc rewrite. -->
# WSL + Docker Quick Start Guide

**🚀 Fast Track Setup | Created by: Herman Swanepoel | AURA-DEV GODMODE**

---

## ⚡ Quick Start (3 Commands)

If your system is ready and you know virtualization is enabled:

```powershell
# 1. Check if ready
.\scripts\WSL-Docker-SafeMode-Recovery.ps1 -Mode FullDiagnostics

# 2. If diagnostics pass, install
.\scripts\WSL-Docker-Setup-Enterprise.ps1 -Mode FullSetup

# 3. After restart, validate
.\scripts\WSL-Docker-Setup-Enterprise.ps1 -Mode Validate
```

---

## 🆘 If You're Experiencing Crashes

### Symptoms: Black screen after enabling Virtual Machine Platform

**Immediate Fix:**

```powershell
# Boot to Safe Mode (Shift + Restart)
# Then run:
.\scripts\WSL-Docker-SafeMode-Recovery.ps1 -Mode DisableAndRecover
```

**Next Steps:**

1. Enable virtualization in BIOS (see guide below)
2. Update Windows and drivers
3. Try installation again

---

## 🔧 BIOS Quick Reference

### Access BIOS

**During boot, repeatedly press:** F2, F10, F12, Del, or Esc

### Enable These Settings

- **Intel:** Virtualization Technology (VT-x) + VT-d
- **AMD:** SVM Mode + IOMMU

### Common Paths

| Brand  | Path                                                           |
| ------ | -------------------------------------------------------------- |
| Dell   | Advanced > Virtualization                                      |
| HP     | Advanced > System Options > Virtualization Technology          |
| Lenovo | Configuration > Intel Virtual Technology                       |
| ASUS   | Advanced > CPU Configuration > Intel Virtualization Technology |

### Save & Exit

Press **F10** → Yes → System will restart

---

## 📋 Pre-Flight Checklist

Before running installation:

- [ ] Windows 10 Build 19041+ or Windows 11
- [ ] All Windows Updates installed
- [ ] Virtualization enabled in BIOS
- [ ] Latest chipset drivers installed
- [ ] At least 20GB free disk space
- [ ] Backup important data

---

## 🎯 Available Scripts

### Diagnostics

```powershell
# Full system check (run this first!)
.\scripts\WSL-Docker-SafeMode-Recovery.ps1 -Mode FullDiagnostics

# Just check BIOS/virtualization
.\scripts\WSL-Docker-SafeMode-Recovery.ps1 -Mode DiagnoseBIOS
```

### Installation

```powershell
# Complete setup (recommended)
.\scripts\WSL-Docker-Setup-Enterprise.ps1 -Mode FullSetup

# Cleanup only
.\scripts\WSL-Docker-Setup-Enterprise.ps1 -Mode CleanupOnly

# Install without cleanup
.\scripts\WSL-Docker-Setup-Enterprise.ps1 -Mode InstallOnly
```

### Recovery

```powershell
# Disable features (if system crashed)
.\scripts\WSL-Docker-SafeMode-Recovery.ps1 -Mode DisableAndRecover

# Create restore point before trying
.\scripts\WSL-Docker-SafeMode-Recovery.ps1 -Mode CreateRestorePoint

# Safe gradual enablement
.\scripts\WSL-Docker-SafeMode-Recovery.ps1 -Mode SafeEnable
```

### Validation

```powershell
# Verify installation
.\scripts\WSL-Docker-Setup-Enterprise.ps1 -Mode Validate -DistroName Ubuntu-24.04
```

---

## 🐛 Common Issues & Quick Fixes

### Issue: "16-bit application error"

```powershell
Remove-Item "$env:TEMP\wsl*" -Recurse -Force
$msi = "$env:TEMP\wsl.msi"
Invoke-WebRequest -Uri "https://aka.ms/wsl-x64" -OutFile $msi -UseBasicParsing
msiexec /i $msi /passive /norestart
```

### Issue: WSL command not found

```powershell
# Reinstall WSL package
Invoke-WebRequest -Uri "https://aka.ms/wsl-x64" -OutFile "$env:TEMP\wsl.msi"
msiexec /i "$env:TEMP\wsl.msi" /passive
```

### Issue: Docker won't start in Ubuntu

```bash
# Inside WSL
sudo systemctl start docker
sudo usermod -aG docker $USER
# Log out and back in
docker run hello-world
```

---

## ✅ Success Validation

Run these commands to verify everything works:

```powershell
# 1. Check WSL version
wsl --version
# Should show: WSL version: 2.x.x.x

# 2. List distributions
wsl --list --verbose
# Should show: Ubuntu-24.04 Running VERSION 2

# 3. Test Docker
wsl -d Ubuntu-24.04 -- docker run hello-world
# Should download and run successfully
```

---

## 📞 Need Help?

### Detailed Troubleshooting

See: `docs\WSL_DOCKER_TROUBLESHOOTING_GUIDE.md`

### Logs Location

- Full setup: `%TEMP%\wsl-docker-setup.log`
- Safe mode: `%TEMP%\wsl-safemode-recovery.log`

### Online Resources

- [WSL Docs](https://docs.microsoft.com/en-us/windows/wsl/)
- [Docker WSL Guide](https://docs.docker.com/desktop/wsl/)
- [Microsoft Q&A](https://learn.microsoft.com/en-us/answers/)

---

## 🎯 Typical Workflow

### First Time Setup

```powershell
# 1. Run diagnostics
.\scripts\WSL-Docker-SafeMode-Recovery.ps1 -Mode FullDiagnostics

# 2. If issues found, fix BIOS/drivers, then run diagnostics again

# 3. Create restore point
.\scripts\WSL-Docker-SafeMode-Recovery.ps1 -Mode CreateRestorePoint

# 4. Install
.\scripts\WSL-Docker-Setup-Enterprise.ps1 -Mode FullSetup

# 5. After restart, validate
.\scripts\WSL-Docker-Setup-Enterprise.ps1 -Mode Validate
```

### If System Crashes

```powershell
# 1. Boot to Safe Mode (Shift + Restart)

# 2. Disable features
.\scripts\WSL-Docker-SafeMode-Recovery.ps1 -Mode DisableAndRecover

# 3. Restart normally

# 4. Fix BIOS/drivers

# 5. Try safe enablement
.\scripts\WSL-Docker-SafeMode-Recovery.ps1 -Mode SafeEnable
```

---

## 🏆 Enterprise Features

These scripts include:

- ✅ Pre-flight system validation
- ✅ Automatic cleanup and recovery
- ✅ Detailed logging with timestamps
- ✅ Circuit breaker patterns for fault tolerance
- ✅ System restore point creation
- ✅ Gradual feature enablement
- ✅ Post-installation validation
- ✅ Comprehensive error handling

---

**AURA-DEV OMNIDEV GODMODE** - Enterprise DevOps Automation
**Version:** 1.0-ENTERPRISE | **Date:** 2025-10-19
