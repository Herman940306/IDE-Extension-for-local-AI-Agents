# 🚀 WSL2 VirtualMachinePlatform Crash Fixer (Improved)

**File:** `Run-WSL2-VirtualMachinePlatform-Fix-Improved.bat`
**Purpose:** Safely fix Windows crashes (black screen, BSOD) when enabling VirtualMachinePlatform for WSL2 on Windows 11 Pro (Build 26200), Intel/MSI/AMIBIOS systems.

---

## 📝 What This Batch File Does

1. **Guides you step-by-step:**
   - Prompts for BIOS/UEFI update and virtualization settings
   - Prompts for Windows Update and driver installation
   - Explains each step before running
2. **Automates key fixes:**
   - Runs a PowerShell script to:
     - Run DISM and SFC health checks
     - Disable/re-enable VirtualMachinePlatform and WSL features
     - Clean registry keys (vmcompute, vmbus)
     - Download and install the latest WSL2 MSI
   - Keeps the PowerShell window open so you can review all output
3. **Logs all actions:**
   - Actions are logged to `%TEMP%\WSL2_VirtualMachinePlatform_Fix.log` for troubleshooting
4. **Pauses between steps:**
   - Lets you control the process and review instructions

---

## 🛠️ How to Use

1. **Boot normally or in Safe Mode** (if your system is crashing)
2. **Double-click** `Run-WSL2-VirtualMachinePlatform-Fix-Improved.bat` in your project folder
3. **Follow the prompts**:
   - Step 1: BIOS/UEFI & Virtualization
   - Step 2: Windows Update & Drivers
   - Step 3: Automated Fix Script (PowerShell)
   - Step 4: Final Manual Steps
4. **Review the PowerShell output** (window stays open)
5. **Check the log file** at `%TEMP%\WSL2_VirtualMachinePlatform_Fix.log` if you need troubleshooting info
6. **After all steps, verify WSL2:**

   ```powershell
   wsl --set-default-version 2
   wsl --list --verbose
   ```

---

## 🧩 What Problems Does This Fix?

- Windows crashes (black screen, BSOD) after enabling VirtualMachinePlatform for WSL2
- Outdated drivers, firmware, or BIOS settings causing instability
- Registry corruption or stuck feature states
- Core Isolation/Memory Integrity conflicts
- Integrated graphics/UMA memory issues

---

## 🛡️ Safety & Recovery

- You can run this batch file in **Safe Mode** if your system won’t boot normally
- All steps are explained before running
- No changes are made without your confirmation
- PowerShell window stays open for review
- All actions are logged for support

---

## 📚 Additional Resources

- [docs/WSL_DOCKER_TROUBLESHOOTING_GUIDE.md](docs/WSL_DOCKER_TROUBLESHOOTING_GUIDE.md)
- [WSL2 VirtualMachinePlatform Fix PowerShell Script](scripts/WSL2_VirtualMachinePlatform_Fix.ps1)
- [Microsoft Q&A: Windows crash when Virtual Machine Platform was enabling](https://learn.microsoft.com/en-us/answers/questions/3985493/windows-crash-when-virtual-machine-platform-was-en)

---

## 🏆 Best Practices

- Always update BIOS/UEFI and drivers before enabling virtualization features
- Use Safe Mode to disable features if system crashes
- Review all output and logs for troubleshooting
- Consult the troubleshooting guide for advanced fixes

---

**Created by GitHub Copilot | Last updated: 2025-10-19**
