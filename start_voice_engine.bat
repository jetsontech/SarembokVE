@echo off
TITLE SAREMBOK VE - Multi-Agent Voice Orchestrator Gateway
color 0B

:: Ensure working directory is the script's root (c:\SarembokVE)
cd /d "%~dp0"

echo ==============================================================================
echo   SAREMBOK VIRTUAL EVOLUTION (VE) // MULTI-AGENT VOICE ORCHESTRATOR
echo   Google AI Studio / Cloud TTS Voices ^| SQLite-WAL Ledger ^| Barge-In VAD
echo ==============================================================================
echo.

:: Check for Python
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not installed or not in PATH.
    pause
    exit /b
)

:: Ensure dependencies are present
echo [INFO] Verifying runtime dependencies (websockets, google-cloud-texttospeech)...
pip install -q websockets

:: Launch Voice Orchestrator
echo [INFO] Starting Voice Orchestrator on ws://localhost:8765...
echo [INFO] Ledger Database: sarembok_runtime.db (SQLite-WAL)
echo.
python Runtime/sarembok_voice_orchestrator.py 8765

pause
