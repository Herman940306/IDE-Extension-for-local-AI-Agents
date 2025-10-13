# Enterprise AI Agents - Windows Setup Script
# Project Creator: Herman Swanepoel

Write-Host "🚀 Setting up Enterprise AI Agents Integration..." -ForegroundColor Cyan

# Check Python version
try {
    $pythonVersion = python --version 2>&1
    if ($pythonVersion -match "Python 3\.1[1-9]") {
        Write-Host "✓ $pythonVersion detected" -ForegroundColor Green
    } else {
        Write-Host "✗ Python 3.11+ required. Current: $pythonVersion" -ForegroundColor Red
        Write-Host "Please install Python 3.11+ from python.org" -ForegroundColor Yellow
        exit 1
    }
} catch {
    Write-Host "✗ Python not found. Please install Python 3.11+ from python.org" -ForegroundColor Red
    exit 1
}

# Check Node.js version
try {
    $nodeVersion = node --version 2>&1
    Write-Host "✓ Node.js $nodeVersion detected" -ForegroundColor Green
} catch {
    Write-Host "✗ Node.js not found. Please install Node.js 18+ from nodejs.org" -ForegroundColor Red
    exit 1
}

# Create backend virtual environment
Write-Host "`n📦 Creating backend virtual environment..." -ForegroundColor Cyan
if (Test-Path "backend/venv") {
    Write-Host "Virtual environment already exists, skipping creation" -ForegroundColor Yellow
} else {
    python -m venv backend/venv
    Write-Host "✓ Virtual environment created" -ForegroundColor Green
}

# Activate and install backend dependencies
Write-Host "`n📥 Installing backend dependencies..." -ForegroundColor Cyan
& backend/venv/Scripts/Activate.ps1
pip install --upgrade pip --quiet
pip install -r backend/requirements.txt --quiet
Write-Host "✓ Backend dependencies installed" -ForegroundColor Green

# Deactivate venv
deactivate

# Install extension dependencies
Write-Host "`n📦 Installing extension dependencies..." -ForegroundColor Cyan
Set-Location extension
npm install --silent
Write-Host "✓ Extension dependencies installed" -ForegroundColor Green

# Return to root
Set-Location ..

# Create data directories
Write-Host "`n📁 Creating data directories..." -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path "data/chroma" | Out-Null
New-Item -ItemType Directory -Force -Path "data/cache" | Out-Null
New-Item -ItemType Directory -Force -Path "data/sessions" | Out-Null
Write-Host "✓ Data directories created" -ForegroundColor Green

# Create .env file from example
if (-not (Test-Path "backend/.env")) {
    Write-Host "`n📝 Creating .env file..." -ForegroundColor Cyan
    Copy-Item "backend/.env.example" "backend/.env"
    Write-Host "✓ .env file created (please configure as needed)" -ForegroundColor Green
} else {
    Write-Host "`n.env file already exists" -ForegroundColor Yellow
}

Write-Host "`n✅ Setup complete!" -ForegroundColor Green
Write-Host "`n📋 Next steps:" -ForegroundColor Yellow
Write-Host "1. Configure backend/.env file with your settings"
Write-Host "2. Activate backend: cd backend && .\venv\Scripts\Activate.ps1"
Write-Host "3. Start backend: python src/main.py"
Write-Host "4. Open extension folder in VS Code and press F5 to debug"
Write-Host "`n💡 Tip: Run 'Get-Help .\setup.ps1' for more information" -ForegroundColor Cyan
