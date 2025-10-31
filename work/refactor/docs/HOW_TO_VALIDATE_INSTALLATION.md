# ✅ How to Check if WSL2 & Docker are Installed Correctly

## 🚀 Quick Answer

**Run this batch file:**

```
Double-click: Check-WSL-Docker-Installation.bat
```

**Or run this PowerShell command:**

```powershell
.\scripts\Validate-WSL-Docker-Installation.ps1
```

---

## 📋 What Gets Checked

### 1. ✅ WSL Installation

- Verifies `wsl` command is available
- Checks WSL version (should be 2.x.x)
- Confirms WSL kernel version

### 2. ✅ WSL Distributions

- Lists all installed distributions (Ubuntu, Debian, etc.)
- Checks if any distribution is WSL2 (VERSION 2)
- Warns if only WSL1 distros exist

### 3. ✅ VirtualMachinePlatform Feature

- Checks if Windows feature is enabled
- Required for WSL2 to work

### 4. ✅ Windows Subsystem for Linux Feature

- Checks if WSL feature is enabled
- Required for WSL to work

### 5. ✅ Hypervisor Status

- Checks if Hyper-V hypervisor is running
- Optional but indicates virtualization is active

### 6. ✅ Docker in WSL

- Checks if Docker is installed in your WSL distribution
- Tests Docker with `hello-world` container
- Confirms Docker daemon is running

### 7. ✅ CPU Virtualization in BIOS

- Checks if Intel VT-x/VT-d or AMD-V/SVM is enabled in BIOS
- Critical for WSL2 and Docker to work

---

## 🎯 Quick Manual Commands

### Check WSL Version

```powershell
wsl --version
```

**Expected output:**

```
WSL version: 2.x.x.x
Kernel version: 5.15.x.x
Windows version: 10.0.26100.x
```

### List WSL Distributions

```powershell
wsl --list --verbose
```

**Expected output:**

```
  NAME            STATE           VERSION
* Ubuntu-24.04    Running         2
```

(VERSION should be 2, not 1)

### Check WSL Status

```powershell
wsl --status
```

**Expected output:**

```
Default Distribution: Ubuntu-24.04
Default Version: 2
```

### Test Docker

```powershell
wsl -- docker run hello-world
```

**Expected output:**

```
Hello from Docker!
This message shows that your installation appears to be working correctly.
```

### Check Docker Version

```powershell
wsl -- docker --version
```

**Expected output:**

```
Docker version 24.x.x, build xxxxx
```

### Enter WSL and Test Inside

```powershell
wsl
```

Then inside WSL:

```bash
docker --version
docker run hello-world
```

---

## ⚠️ Common Issues & Fixes

### Issue: "wsl: command not found"

**Fix:** WSL is not installed. Run:

```
Double-click: Run-WSL-Install-Admin.bat
```

### Issue: "VERSION 1" instead of "VERSION 2"

**Fix:** Set WSL2 as default:

```powershell
wsl --set-default-version 2
wsl --set-version Ubuntu-24.04 2
```

### Issue: "VirtualMachinePlatform is not enabled"

**Fix:** Enable it in Windows Features:

1. Press `Win + R`, type `optionalfeatures.exe`
2. Check "Virtual Machine Platform"
3. Click OK and restart

### Issue: "Docker command not found" in WSL

**Fix:** Install Docker in WSL. Run:

```
Double-click: Run-WSL-Install-Admin.bat
```

This will install Docker automatically.

### Issue: "CPU Virtualization is disabled in BIOS"

**Fix:** Reboot and enter BIOS (DEL/F2/F10), enable:

- Intel: VT-x, VT-d
- AMD: SVM Mode, IOMMU

### Issue: Docker hello-world test fails

**Possible causes:**

- Docker daemon not running: `wsl -- sudo systemctl start docker`
- User not in docker group: `wsl -- sudo usermod -aG docker $USER`
- Permissions issue: `wsl -- sudo chmod 666 /var/run/docker.sock`

---

## 📊 Validation Output Example

When you run `Check-WSL-Docker-Installation.bat`, you'll see output like this:

```
===============================================
WSL2 & Docker Installation Validator
===============================================

[CHECK 1] WSL Installation...
✅ WSL is installed
WSL version: 2.0.14.0
Kernel version: 5.15.133.1-1
Windows version: 10.0.26100.1742

[CHECK 2] WSL Distributions...
✅ WSL distributions found:
  NAME            STATE           VERSION
* Ubuntu-24.04    Running         2
✅ WSL2 distro detected

[CHECK 3] VirtualMachinePlatform Feature...
✅ VirtualMachinePlatform is enabled

[CHECK 4] Windows Subsystem for Linux Feature...
✅ WSL feature is enabled

[CHECK 5] Hypervisor Status...
✅ Hypervisor is present and running

[CHECK 6] Docker in WSL...
   Checking Docker in: Ubuntu-24.04
✅ Docker is installed in WSL: Docker version 24.0.7, build afdd53b
   Testing Docker with hello-world...
✅ Docker hello-world test PASSED

[CHECK 7] CPU Virtualization...
✅ CPU Virtualization is enabled in BIOS

===============================================
✅ ALL CRITICAL CHECKS PASSED!
   Your WSL2 installation is ready to use.
===============================================

Quick Command Reference:
  - Check WSL version:        wsl --version
  - List distributions:       wsl --list --verbose
  - Set WSL2 as default:      wsl --set-default-version 2
  - Install Ubuntu:           wsl --install -d Ubuntu-24.04
  - Enter WSL:                wsl
  - Test Docker:              wsl -- docker run hello-world
```

---

## 🎉 Success Criteria

Your installation is successful when:

- ✅ `wsl --version` shows WSL 2.x.x
- ✅ `wsl --list --verbose` shows a distribution with VERSION 2
- ✅ `wsl` command launches Ubuntu (or your distro)
- ✅ `docker --version` works inside WSL
- ✅ `docker run hello-world` completes successfully
- ✅ All validation checks pass

---

## 📞 Need Help?

If validation fails:

1. **Review the failure messages** - they usually tell you what's wrong
2. **Check the log file** at `%TEMP%\wsl-docker-setup.log`
3. **Run diagnostics** with `Run-WSL-Diagnostics-Admin.bat`
4. **Check troubleshooting guide** at `docs/WSL_DOCKER_TROUBLESHOOTING_GUIDE.md`
5. **Try recovery** with `Run-WSL-Recovery-Admin.bat` if system crashed

---

**Created: 2025-10-19 | For Windows 11 Pro (Build 26200)**
