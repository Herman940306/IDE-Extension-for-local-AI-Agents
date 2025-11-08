# Start Backend Server
# Simple script to start the FastAPI backend on port 8001

Write-Host "🚀 Starting FastAPI Backend..." -ForegroundColor Cyan
Write-Host "   Port: 8001" -ForegroundColor Gray
Write-Host "   Host: 127.0.0.1" -ForegroundColor Gray
Write-Host ""

# Navigate to backend directory
Set-Location "E:\Visual Studio Coode Projects\AI Agents Integration system for VS Code\backend"

# Start uvicorn server
& "E:\Visual Studio Coode Projects\AI Agents Integration system for VS Code\.venv\Scripts\python.exe" -m uvicorn src.main:app --host 127.0.0.1 --port 8001

Write-Host ""
Write-Host "Backend stopped." -ForegroundColor Yellow
