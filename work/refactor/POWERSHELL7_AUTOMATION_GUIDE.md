# 🚀 PowerShell 7 Full Automation Guide

## ⚡ Quick Start

**1. Double-click to run:**

```
Launch-PowerShell7-Automation.bat
```

**2. Or run directly in PowerShell 7:**

```powershell
.\PowerShell7-Full-Automation.ps1
```

---

## 🎯 What This Automation Does

### ✅ **Phase 1: System Validation**

- Checks PowerShell 7 x64
- Validates Windows 11 (Build 22000+)
- Confirms Administrator privileges
- Verifies CPU virtualization in BIOS
- Checks disk space (20GB minimum)
- Tests Hyper-V compatibility

### ✅ **Phase 2: Windows Features**

- Enables `VirtualMachinePlatform`
- Enables `Microsoft-Windows-Subsystem-Linux`
- Downloads and installs WSL2 kernel update

### ✅ **Phase 3: WSL Configuration**

- Sets WSL2 as default version
- Installs Ubuntu 24.04 LTS
- Configures WSL for optimal performance

### ✅ **Phase 4: Docker Installation**

- Updates Ubuntu package lists
- Installs Docker CE with all dependencies
- Adds user to docker group
- Starts Docker service
- Tests with hello-world container

### ✅ **Phase 5: Validation**

- Tests WSL functionality
- Verifies Ubuntu 24.04 on WSL2
- Validates Docker installation
- Runs complete system check

---

## 🛠️ Command Line Options

```powershell
# Basic usage
.\PowerShell7-Full-Automation.ps1

# Skip BIOS warnings (if you know virtualization is enabled)
.\PowerShell7-Full-Automation.ps1 -SkipBiosCheck

# Auto-restart without prompting
.\PowerShell7-Full-Automation.ps1 -AutoRestart

# Force reinstall even if WSL exists
.\PowerShell7-Full-Automation.ps1 -Force

# Custom log location
.\PowerShell7-Full-Automation.ps1 -LogPath "C:\Logs\wsl-setup.log"

# Combined options
.\PowerShell7-Full-Automation.ps1 -AutoRestart -Force -SkipBiosCheck
```

---

## ⏱️ Expected Timeline

| Phase               | Duration          | Action Required |
| ------------------- | ----------------- | --------------- |
| System Validation   | 30 seconds        | None            |
| Windows Features    | 2-5 minutes       | None            |
| WSL Kernel          | 1-2 minutes       | None            |
| **RESTART**         | **2-3 minutes**   | **Automatic**   |
| WSL Configuration   | 3-5 minutes       | None            |
| Ubuntu Installation | 5-10 minutes      | None            |
| Docker Installation | 3-5 minutes       | None            |
| Final Validation    | 1 minute          | None            |
| **TOTAL**           | **15-25 minutes** | **1 restart**   |

---

## 🔍 Monitoring Progress

### **Console Output**

- Color-coded messages (Green=Success, Red=Error, Yellow=Warning)
- Real-time progress indicators
- Detailed step-by-step logging

### **Log File**

- Comprehensive log with timestamps
- Located in: `%TEMP%\wsl-docker-automation-YYYYMMDD-HHMMSS.log`
- Includes all command outputs and error details

### **Progress Indicators**

```
[2025-10-20 15:30:15.123] [SUCCESS] ✅ PowerShell 7 detected: 7.4.0
[2025-10-20 15:30:16.456] [INFO] Enabling Windows features for WSL2...
[2025-10-20 15:30:18.789] [SUCCESS] ✅ Virtual Machine Platform enabled
```

---

## 🆘 Troubleshooting

### **If Automation Stops with Error:**

1. Check the log file path shown in console
2. Look for the last ERROR message
3. Address the specific issue
4. Re-run with `-Force` flag

### **Common Issues:**

**❌ "CPU Virtualization not enabled"**

```
Solution: Enable Intel VT-x/VT-d or AMD-V/SVM in BIOS
1. Restart computer
2. Enter BIOS (F2, F10, F12, Del)
3. Enable virtualization features
4. Save and exit
```

**❌ "Administrator privileges required"**

```
Solution: Right-click PowerShell 7 → "Run as Administrator"
Or use the Launch-PowerShell7-Automation.bat file
```

**❌ "Insufficient disk space"**

```
Solution: Free up at least 20GB on C: drive
Check: Temp files, Downloads, Recycle Bin
```

**❌ "PowerShell 7 not found"**

```
Solution: Install PowerShell 7
winget install Microsoft.PowerShell
Or download from: https://github.com/PowerShell/PowerShell/releases
```

---

## ✅ Success Indicators

**🎉 Automation Complete:**

```
✅ WSL is working: WSL version 2.0.9.0
✅ Ubuntu 24.04 running on WSL2
✅ Docker is working correctly
🎉 AUTOMATION COMPLETED SUCCESSFULLY! 🎉
```

**📋 Manual Verification:**

```powershell
# Check WSL
wsl --version
wsl --list --verbose

# Test Docker
wsl -- docker run hello-world

# Enter Ubuntu
wsl
```

---

## 🔄 Post-Automation Commands

```powershell
# Start developing immediately
wsl

# Check Docker status
wsl -- docker ps

# Run your first container
wsl -- docker run -it ubuntu bash

# Install development tools
wsl -- sudo apt update && sudo apt install -y git nodejs npm python3 pip

# Clone your projects
wsl -- git clone https://github.com/yourusername/yourproject.git
```

---

## 🏆 Enterprise Features

- **✅ Circuit Breaker Pattern:** Stops on first critical error
- **✅ Comprehensive Logging:** Full audit trail with timestamps
- **✅ Progress Tracking:** Real-time status updates
- **✅ Error Recovery:** Detailed error messages with solutions
- **✅ Validation Framework:** Multi-layer verification
- **✅ PowerShell 7 Optimized:** Leverages latest PS7 features
- **✅ Zero-Touch Installation:** Minimal user interaction required

**Ready for enterprise deployment! 🚀**
