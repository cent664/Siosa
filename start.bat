@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found.
    echo Run: python -m venv .venv
    echo Then: .venv\Scripts\pip install -e ".[dev,speech]"
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat

set "NPM_OK="
where npm >nul 2>&1 && set "NPM_OK=1"
if not defined NPM_OK if exist "%ProgramFiles%\nodejs\npm.cmd" (
    set "PATH=%ProgramFiles%\nodejs;%PATH%"
    set "NPM_OK=1"
)
if not defined NPM_OK if exist "%ProgramFiles(x86)%\nodejs\npm.cmd" (
    set "PATH=%ProgramFiles(x86)%\nodejs;%PATH%"
    set "NPM_OK=1"
)
if not defined NPM_OK if exist "%LOCALAPPDATA%\nodejs\npm.cmd" (
    set "PATH=%LOCALAPPDATA%\nodejs;%PATH%"
    set "NPM_OK=1"
)

if not defined NPM_OK (
    echo ERROR: npm not found. Node.js is required to build the web UI.
    echo.
    echo Install Node.js LTS, then close and reopen this window:
    echo   winget install OpenJS.NodeJS.LTS
    echo   https://nodejs.org/
    echo.
    echo Or manually: cd web ^&^& npm install ^&^& npm run build
    pause
    exit /b 1
)

echo Building web UI...
pushd web
call npm install
if errorlevel 1 (
    popd
    pause
    exit /b 1
)
call npm run build
popd
if errorlevel 1 (
    pause
    exit /b 1
)

echo Starting PoE Wiki Agent API...
echo.
echo   App:      http://127.0.0.1:8000/
echo   API:      http://127.0.0.1:8000
echo   Docs:     http://127.0.0.1:8000/docs/
echo.
echo Press Ctrl+C to stop.
echo.

uvicorn poe_agent.harness.api.app:app --host 127.0.0.1 --port 8000
