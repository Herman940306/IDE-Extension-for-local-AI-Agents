@echo off
REM Backend Startup Script
REM Project Creator: Herman Swanepoel

echo Starting Enterprise AI Agents Backend...
cd backend
call .venv\Scripts\activate
python run.py
