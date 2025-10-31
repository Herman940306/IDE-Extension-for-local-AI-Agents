@echo off
REM Redis Setup Script for Windows
REM Project Creator: Herman Swanepoel

echo Setting up Redis for Enterprise AI Agents Backend...
echo.

echo Option 1: Docker (Recommended)
echo docker run -d --name redis-aura -p 6379:6379 redis:7-alpine
echo.

echo Option 2: Windows Service
echo Download from: https://github.com/microsoftarchive/redis/releases
echo.

echo Option 3: WSL2
echo wsl -d Ubuntu
echo sudo apt update
echo sudo apt install redis-server
echo sudo service redis-server start
echo.

pause
