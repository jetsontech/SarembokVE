@echo off
TITLE SAREMBOK VE - Voice Engine Host
color 0B
echo [INFO] Booting Voice Agent Framework on Windows 11...

:: Check for Python
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not installed or not in PATH.
    pause
    exit /b
)

:: Setup Virtual Environment
IF NOT EXIST "venv" (
    echo [INFO] Creating Python virtual environment...
    python -m venv venv
)

echo [INFO] Activating virtual environment...
call venv\Scripts\activate.bat

echo [INFO] Installing frontier dependencies...
:: We use FastAPI for the async event loop and WebSockets for low-latency audio streaming
pip install -q fastapi uvicorn websockets openai pyaudio python-dotenv

:: Start the API Server
echo [INFO] Starting FastAPI WebSocket Server (Port 8000)...
start "Backend Engine" cmd /c "uvicorn backend.main:app --host 0.0.0.0 --port 8001 --reload"

:: Serve the PWA Frontend
echo [INFO] Serving Mobile Web Client (Port 3000)...
cd frontend
start "Frontend UI" cmd /c "python -m http.server 3000"

echo ===================================================
echo [SUCCESS] Engine is running in the background.
echo [NETWORK] Access via iOS/Android browser at:
echo           http://<YOUR_WINDOWS_IPV4_ADDRESS>:3000
echo ===================================================
pause