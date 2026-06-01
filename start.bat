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



if not exist "web\dist\index.html" (

    echo Building web UI...

    where npm >nul 2>&1

    if errorlevel 1 (

        echo ERROR: npm not found. Install Node.js, then run:

        echo   cd web ^&^& npm install ^&^& npm run build

        pause

        exit /b 1

    )

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

