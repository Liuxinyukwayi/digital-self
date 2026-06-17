@echo off
echo ========================================
echo   Digital Self - Startup Script
echo ========================================
echo.

REM Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python 3.10+
    pause
    exit /b 1
)

REM Check Node.js
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js not found. Please install Node.js 18+
    pause
    exit /b 1
)

REM Create .env file
if not exist backend\.env (
    echo [1/5] Creating .env config...
    if exist .env.example (
        copy .env.example backend\.env >nul
    ) else (
        echo DATABASE_URL=sqlite:///./digital_self.db> backend\.env
        echo QDRANT_ENABLED=false>> backend\.env
        echo MIMO_API_KEY=your-mimo-api-key-here>> backend\.env
        echo MIMO_API_BASE=https://api.xiaomimimo.com/v1>> backend\.env
        echo MIMO_MODEL=mimo-v2.5-pro>> backend\.env
    )
    echo   Please edit backend\.env with your API Key
    echo.
) else (
    echo [1/5] .env config exists
)

REM Install backend dependencies
echo [2/5] Checking backend dependencies...
cd backend
pip install -q -r requirements.txt 2>nul
cd ..

REM Install frontend dependencies
echo [3/5] Checking frontend dependencies...
cd frontend
if not exist node_modules (
    call npm install --silent 2>nul
)
cd ..

REM Clean old cache
if exist frontend\.next rmdir /s /q frontend\.next 2>nul

REM Start backend
echo [4/5] Starting backend (port 8000)...
start /b "digital-self-backend" cmd /c "cd backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload 2>&1"

echo   Waiting for backend...
timeout /t 3 /nobreak >nul

REM Start frontend
echo [5/5] Starting frontend (port 3000)...
start /b "digital-self-frontend" cmd /c "cd frontend && npx next dev --port 3000 2>&1"

echo.
echo   Waiting for frontend...
timeout /t 8 /nobreak >nul

echo.
echo ========================================
echo   Services started!
echo ========================================
echo.
echo   Frontend:  http://localhost:3000
echo   Backend:   http://localhost:8000
echo   API Docs:  http://localhost:8000/docs
echo.
echo   Close this window or run stop.bat to stop
echo.

REM Open browser
start http://localhost:3000

pause
