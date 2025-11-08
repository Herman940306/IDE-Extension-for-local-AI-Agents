@echo off
REM AuraIA System Startup
REM Project Creator: Herman Swanepoel

echo ========================================
echo    AuraIA System Startup
echo ========================================
echo.

echo Starting Backend...
start cmd /k "cd backend && .venv\Scripts\activate && python run.py"

timeout /t 5 /nobreak

echo Starting Frontend...
start cmd /k "cd frontend && npm run dev"

echo.
echo ========================================
echo    Both services starting...
echo    Backend: http://127.0.0.1:8001
echo    Frontend: http://localhost:3000
echo ========================================
echo.
pause
