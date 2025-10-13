# Quick Start Guide

**Get up and running in 5 minutes!**

---

## Step 1: Install Tools (2 minutes)

Open PowerShell 7 and run:

```powershell
# Install PuTTY
winget install -e --id PuTTY.PuTTY

# Install WinSCP
winget install -e --id WinSCP.WinSCP
```

---

## Step 2: Verify Installation (1 minute)

```powershell
# Navigate to scripts directory
cd path\to\scripts

# Run verification
.\verify-installation.ps1
```

Expected output: ✓ All tools installed and configured!

---

## Step 3: Configure (1 minute)

```powershell
# Copy config template
Copy-Item config.example.ps1 config.ps1

# Edit with your credentials
notepad config.ps1
```

Update these values:
- `ServerIP`: Your server IP (e.g., `192.168.1.134`)
- `Username`: Your SSH username (e.g., `root`)
- `Password`: Your SSH password
- `RemoteProjectDir`: Your remote project path
- `LocalProjectDir`: Your local project path

**Save and close!**

---

## Step 4: Run! (1 minute)

```powershell
.\devops-ssh-connect.ps1
```

**That's it!** 🎉

You should now see:
- ✅ PuTTY window connected to your server in the project directory
- ✅ WinSCP GUI with local files (left) and remote files (right)

---

## Troubleshooting

### Can't run script?

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

### Server not reachable?

```powershell
ping 192.168.1.134
```

### Wrong directory?

Check `config.ps1` paths are correct.

---

## Next Steps

- Read full [README.md](README.md) for advanced features
- Set up SSH keys for passwordless authentication
- Create desktop shortcut for one-click access

---

**Project Creator:** Herman Swanepoel
