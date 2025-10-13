# Stop MCP Server Script
# Project: AI Agents Integration System for VS Code
# Creator: Herman Swanepoel
# Description: Stops the ai-assistant-ml MCP server

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  AURA-DEV MCP Server Shutdown" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check for process info file
$processInfoFile = "logs\mcp-server-process.json"

if (Test-Path $processInfoFile) {
    $processInfo = Get-Content $processInfoFile | ConvertFrom-Json
    $pid = $processInfo.PID
    
    Write-Host "[→] Found process info (PID: $pid)" -ForegroundColor Cyan
    
    # Check if process is still running
    $process = Get-Process -Id $pid -ErrorAction SilentlyContinue
    
    if ($process) {
        Write-Host "[→] Stopping MCP server..." -ForegroundColor Yellow
        Stop-Process -Id $pid -Force
        Start-Sleep -Seconds 2
        Write-Host "[✓] MCP server stopped successfully" -ForegroundColor Green
        Remove-Item $processInfoFile
    } else {
        Write-Host "[!] Process not found (may have already stopped)" -ForegroundColor Yellow
        Remove-Item $processInfoFile
    }
} else {
    # Try to find the process by command line
    Write-Host "[→] Searching for MCP server process..." -ForegroundColor Cyan
    
    $mcpProcess = Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object {
        $_.CommandLine -like "*ai_assistant_ml_server.py*"
    }
    
    if ($mcpProcess) {
        Write-Host "[→] Found MCP server (PID: $($mcpProcess.Id))" -ForegroundColor Cyan
        Write-Host "[→] Stopping server..." -ForegroundColor Yellow
        Stop-Process -Id $mcpProcess.Id -Force
        Start-Sleep -Seconds 2
        Write-Host "[✓] MCP server stopped successfully" -ForegroundColor Green
    } else {
        Write-Host "[!] No MCP server process found" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Server Status: STOPPED" -ForegroundColor Red
Write-Host "========================================" -ForegroundColor Cyan
