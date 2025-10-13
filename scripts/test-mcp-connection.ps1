# Test MCP Server Connection Script
# Project: AI Agents Integration System for VS Code
# Creator: Herman Swanepoel
# Description: Tests the connection to the ai-assistant-ml MCP server

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  AURA-DEV MCP Connection Test" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if server process is running
Write-Host "[→] Checking if MCP server is running..." -ForegroundColor Cyan

$mcpProcess = Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*ai_assistant_ml_server.py*"
}

if ($mcpProcess) {
    Write-Host "[✓] MCP server process found (PID: $($mcpProcess.Id))" -ForegroundColor Green
} else {
    Write-Host "[✗] MCP server process not found" -ForegroundColor Red
    Write-Host "    Run: .\scripts\start-mcp-server.ps1" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "[→] Checking server logs..." -ForegroundColor Cyan

# Check output log
if (Test-Path "logs\mcp-server-output.log") {
    $outputLog = Get-Content "logs\mcp-server-output.log" -Tail 10
    if ($outputLog) {
        Write-Host "[✓] Server output log found" -ForegroundColor Green
        Write-Host ""
        Write-Host "Last 10 lines of output:" -ForegroundColor Gray
        Write-Host "------------------------" -ForegroundColor Gray
        $outputLog | ForEach-Object { Write-Host $_ -ForegroundColor White }
        Write-Host "------------------------" -ForegroundColor Gray
    }
} else {
    Write-Host "[!] No output log found yet" -ForegroundColor Yellow
}

Write-Host ""

# Check error log
if (Test-Path "logs\mcp-server-error.log") {
    $errorLog = Get-Content "logs\mcp-server-error.log" -Tail 10
    if ($errorLog -and $errorLog.Length -gt 0) {
        Write-Host "[!] Errors detected in log:" -ForegroundColor Yellow
        Write-Host "------------------------" -ForegroundColor Gray
        $errorLog | ForEach-Object { Write-Host $_ -ForegroundColor Red }
        Write-Host "------------------------" -ForegroundColor Gray
    } else {
        Write-Host "[✓] No errors in log" -ForegroundColor Green
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Connection Test Complete" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Use Kiro to test MCP tools" -ForegroundColor White
Write-Host "2. Check .kiro/settings/mcp.json for configuration" -ForegroundColor White
Write-Host "3. View full logs: Get-Content logs\mcp-server-output.log -Wait" -ForegroundColor White
Write-Host ""
