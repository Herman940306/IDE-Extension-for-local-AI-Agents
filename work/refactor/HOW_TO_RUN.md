# 🚀 WSL + Docker Setup - Quick Launch Guide

## ✅ Parser Error Fixed

The PowerShell syntax error has been fixed. You can now run the scripts.

---

## 📂 Easy Launcher Batch Files

I've created **4 easy-to-use batch files** that automatically launch PowerShell as Administrator:

### 1. ✅ Check-WSL-Docker-Installation.bat

**Purpose:** Verify if WSL2 and Docker are installed correctly

**What it checks:**

- WSL installation and version
- WSL distributions (Ubuntu, etc.)
- VirtualMachinePlatform feature
- Windows Subsystem for Linux feature
- Hypervisor status
- Docker in WSL
- CPU virtualization in BIOS

**When to use:** After installation to verify everything works

**How to use:**

1. Double-click `Check-WSL-Docker-Installation.bat`
2. Review the validation results
3. Follow any suggested fixes if checks fail

---

### 2. 🔍 Run-WSL-Diagnostics-Admin.bat

**Purpose:** Check if your system is ready for WSL/Docker

**What it does:**

- Validates CPU virtualization
- Checks BIOS settings
- Verifies Windows version
- Checks disk space
- Provides BIOS configuration guide

**When to use:** Run this FIRST before installation

**How to use:**

1. Double-click `Run-WSL-Diagnostics-Admin.bat`
2. Click "Yes" on UAC prompt
3. Review diagnostic results

---

### 2. 🚀 Run-WSL-Install-Admin.bat

**Purpose:** Full automated WSL2 + Docker installation

**What it does:**

- Cleans previous installations
- Enables Windows features
- Installs WSL2 + Ubuntu 24.04
- Installs Docker CE
- Validates everything works

**When to use:** After diagnostics pass

**How to use:**

1. Double-click `Run-WSL-Install-Admin.bat`
2. Click "Yes" on UAC prompt
3. Follow on-screen instructions
4. System will restart after feature enablement

---

### 3. 🆘 Run-WSL-Recovery-Admin.bat

**Purpose:** Emergency recovery if system crashes

**What it does:**

- Disables Virtual Machine Platform
- Disables WSL features
- Restores system to bootable state

**When to use:**

- System crashed during installation
- Black screen after reboot
- Boot loop
- Run from Safe Mode if needed

**How to use:**

1. Boot to Safe Mode (if needed)
2. Double-click `Run-WSL-Recovery-Admin.bat`
3. Click "Yes" on UAC prompt
4. Restart after recovery

---

## 🎯 Recommended Workflow

### First Time Setup

```
Step 1: Run-WSL-Diagnostics-Admin.bat
   ↓
   ✅ Diagnostics PASS
   ↓
Step 2: Run-WSL-Install-Admin.bat
   ↓
   🔄 System restarts
   ↓
Step 3: Check-WSL-Docker-Installation.bat (Validate)
   ↓
   ✅ ALL CHECKS PASSED - SUCCESS!
```

### If Diagnostics Fail

```
Run-WSL-Diagnostics-Admin.bat
   ↓
   ❌ Issues found
   ↓
Fix BIOS settings (enable virtualization)
Update Windows & drivers
   ↓
Run-WSL-Diagnostics-Admin.bat again
   ↓
   ✅ Diagnostics PASS
   ↓
Proceed with installation
```

### If System Crashes

```
System crashes during installation
   ↓
Boot to Safe Mode
   ↓
Run-WSL-Recovery-Admin.bat
   ↓
Restart normally
   ↓
Fix BIOS/drivers
   ↓
Run-WSL-Diagnostics-Admin.bat
   ↓
Try installation again
```

---

## 📋 Your System Status

Based on your `Get-ComputerInfo` output:

✅ **Ready for Installation!**

- ✅ Windows 11 Pro (Build 26200)
- ✅ Intel Core i7-9700K (8 cores)
- ✅ 16 GB RAM
- ✅ **Virtualization ENABLED in BIOS**
- ✅ CPU supports VT-x, SLAT, DEP
- ✅ Sufficient disk space

**You can proceed directly to installation!**

---

## 🎯 Quick Start (Just 2 Steps)

### Step 1: Run Diagnostics

```
Double-click: Run-WSL-Diagnostics-Admin.bat
```

This will confirm everything is ready.

### Step 2: Install

```
Double-click: Run-WSL-Install-Admin.bat
```

This will install everything automatically.

---

## 💡 Manual Commands (If You Prefer)

If you prefer to run commands manually in an Administrator PowerShell:

### Diagnostics

```powershell
cd "E:\Visual Studio Coode Projects\AI Agents Integration system for VS Code"
.\scripts\WSL-Docker-SafeMode-Recovery.ps1 -Mode FullDiagnostics
```

### Installation

```powershell
cd "E:\Visual Studio Coode Projects\AI Agents Integration system for VS Code"
.\scripts\WSL-Docker-Setup-Enterprise.ps1 -Mode FullSetup
```

### Validation (Check if installed correctly)

```powershell
cd "E:\Visual Studio Coode Projects\AI Agents Integration system for VS Code"
.\scripts\Validate-WSL-Docker-Installation.ps1
```

**Or use the batch file:**

```
Double-click: Check-WSL-Docker-Installation.bat
```

### Recovery (Safe Mode)

```powershell
cd "E:\Visual Studio Coode Projects\AI Agents Integration system for VS Code"
.\scripts\WSL-Docker-SafeMode-Recovery.ps1 -Mode DisableAndRecover
```

---

## ✅ How to Check if Everything Works

### Quick Manual Check

```powershell
# 1. Check WSL version
wsl --version

# 2. List distributions
wsl --list --verbose

# 3. Check if WSL2 is default
wsl --status

# 4. Test Docker (if installed)
wsl -- docker run hello-world
```

### Automated Validation

```
Double-click: Check-WSL-Docker-Installation.bat
```

This will check:

- ✅ WSL installation and version
- ✅ WSL distributions
- ✅ VirtualMachinePlatform feature status
- ✅ WSL feature status
- ✅ Hypervisor status
- ✅ Docker installation in WSL
- ✅ CPU virtualization in BIOS

---

## 📁 File Locations

All files are in your project root:

```
E:\Visual Studio Coode Projects\AI Agents Integration system for VS Code\
│
├── Run-WSL-Diagnostics-Admin.bat    ← Double-click to run diagnostics
├── Run-WSL-Install-Admin.bat        ← Double-click to install
├── Run-WSL-Recovery-Admin.bat       ← Double-click for emergency recovery
│
├── scripts\
│   ├── WSL-Docker-Setup-Enterprise.ps1
│   └── WSL-Docker-SafeMode-Recovery.ps1
│
└── docs\
    ├── WSL_DOCKER_QUICK_START.md
    └── WSL_DOCKER_TROUBLESHOOTING_GUIDE.md
```

---

## 🔧 What Was Fixed

**Issue:** PowerShell parser error on line 192

```powershell
# Before (broken):
Write-Log "✅ $feature: ENABLED" -Level SUCCESS

# After (fixed):
Write-Log "✅ ${feature}: ENABLED" -Level SUCCESS
```

**Root cause:** PowerShell tried to parse `$feature:` as a special variable syntax (like `$env:` or `$global:`). Using `${feature}` explicitly delimits the variable name.

---

## ✅ Next Action

**→ Double-click: `Run-WSL-Diagnostics-Admin.bat`**

This will:

1. Open PowerShell as Administrator
2. Run full system diagnostics
3. Show you if system is ready
4. Provide BIOS guide if needed

Then if diagnostics pass:

**→ Double-click: `Run-WSL-Install-Admin.bat`**

---

## 📞 Need Help?

- **Quick reference:** `docs/WSL_DOCKER_QUICK_START.md`
- **Detailed guide:** `docs/WSL_DOCKER_TROUBLESHOOTING_GUIDE.md`
- **Navigation:** `WSL_DOCKER_INDEX.md`

**Logs saved to:**

- Diagnostics: `%TEMP%\wsl-safemode-recovery.log`
- Installation: `%TEMP%\wsl-docker-setup.log`

---

**🎯 Ready to go! Start with diagnostics.**

**Status:** ✅ PARSER ERROR FIXED | ✅ BATCH FILES CREATED | ✅ READY TO RUN
