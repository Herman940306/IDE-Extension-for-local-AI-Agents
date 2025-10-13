# Start MCP Server Script
# Project: AI Agents Integration System for VS Code
# Creator: Herman Swanepoel
# Description: Automatically starts the ai-assistant-ml MCP server

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  AURA-DEV MCP Server Startup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Configuration
$MCP_SERVER_PATH = "C:\AI\_Assistant\_HomeServer\mcp_server\ai_assistant_ml_server.py"
$PYTHON_PATH = "C:\AI\_Assistant\_HomeServer\.venv\Scripts\python.exe"
$LOG_FILE = "logs\mcp-server.log"

# Create logs directory if it doesn't exist
if (-not (Test-Path "logs")) {
    New-Item -ItemType Directory -Path "logs" | Out-Null
    Write-Host "[✓] Created logs directory" -ForegroundColor Green
}

# Check if MCP server file exists
if (-not (Test-Path $MCP_SERVER_PATH)) {
    Write-Host "[✗] ERROR: MCP server not found at: $MCP_SERVER_PATH" -ForegroundColor Red
    Write-Host "    Please verify the path in this script." -ForegroundColor Yellow
    exit 1
}

# Check if Python exists
if (-not (Test-Path $PYTHON_PATH)) {
    Write-Host "[✗] ERROR: Python not found at: $PYTHON_PATH" -ForegroundColor Red
    Write-Host "    Please verify the Python path in this script." -ForegroundColor Yellow
    exit 1
}

Write-Host "[✓] MCP server found" -ForegroundColor Green
Write-Host "[✓] Python interpreter found" -ForegroundColor Green
Write-Host ""

# Check if server is already running
$existingProcess = Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*ai_assistant_ml_server.py*"
}

if ($existingProcess) {
    Write-Host "[!] MCP server is already running (PID: $($existingProcess.Id))" -ForegroundColor Yellow
    $response = Read-Host "Do you want to restart it? (y/n)"
    if ($response -eq 'y') {
        Write-Host "[→] Stopping existing server..." -ForegroundColor Yellow
        Stop-Process -Id $existingProcess.Id -Force
        Start-Sleep -Seconds 2
        Write-Host "[✓] Server stopped" -ForegroundColor Green
    } else {
        Write-Host "[→] Keeping existing server running" -ForegroundColor Cyan
        exit 0
    }
}

# Start the MCP server
Write-Host "[→] Starting AURA-DEV MCP Server..." -ForegroundColor Cyan
Write-Host "    Mode: GODMODE" -ForegroundColor Magenta
Write-Host "    Log: $LOG_FILE" -ForegroundColor Gray
Write-Host ""

try {
    # Start the server in a new process
    $process = Start-Process -FilePath $PYTHON_PATH `
                            -ArgumentList $MCP_SERVER_PATH `
                            -PassThru `
                            -WindowStyle Hidden `
                            -RedirectStandardOutput "logs\mcp-server-output.log" `
                            -RedirectStandardError "logs\mcp-server-error.log"
    
    # Wait a moment for the server to start
    Start-Sleep -Seconds 3
    
    # Check if process is still running
    if (Get-Process -Id $process.Id -ErrorAction SilentlyContinue) {
        Write-Host "[✓] MCP Server started successfully!" -ForegroundColor Green
        Write-Host "    PID: $($process.Id)" -ForegroundColor Gray
        Write-Host ""
        Write-Host "========================================" -ForegroundColor Cyan
        Write-Host "  Server Status: RUNNING" -ForegroundColor Green
        Write-Host "========================================" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "To stop the server, run:" -ForegroundColor Yellow
        Write-Host "  Stop-Process -Id $($process.Id)" -ForegroundColor White
        Write-Host ""
        Write-Host "To view logs:" -ForegroundColor Yellow
        Write-Host "  Get-Content logs\mcp-server-output.log -Wait" -ForegroundColor White
        Write-Host ""
    } else {
        Write-Host "[✗] Server failed to start. Check logs for details." -ForegroundColor Red
        Write-Host "    Error log: logs\mcp-server-error.log" -ForegroundColor Yellow
        exit 1
    }
} catch {
    Write-Host "[✗] ERROR: Failed to start MCP server" -ForegroundColor Red
    Write-Host "    $_" -ForegroundColor Red
    exit 1
}

# Save process info for later reference
$processInfo = @{
    PID = $process.Id
    StartTime = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    ServerPath = $MCP_SERVER_PATH
} | ConvertTo-Json

$processInfo | Out-File "logs\mcp-server-process.json"

Write-Host "[✓] Process info saved to logs\mcp-server-process.json" -ForegroundColor Green
Write-Host ""
Write-Host "MCP Server is ready for Kiro to use!" -ForegroundColor Cyan
