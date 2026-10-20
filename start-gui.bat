@echo off
setlocal
rem Launch the desktop configuration GUI (Plan B).
rem ASCII-only on purpose: cmd.exe parses .bat as GBK, UTF-8 Chinese garbles.

cd /d "%~dp0"

set "PY=D:\Python38\python.exe"
if not exist "%PY%" set "PY=python"

"%PY%" -c "import customtkinter" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] customtkinter not available for: %PY%
    echo Install it with: "%PY%" -m pip install customtkinter
    pause
    exit /b 1
)

echo Starting Microsoft Rewards GUI...
"%PY%" "gui\app.py"
if errorlevel 1 (
    echo.
    echo GUI exited with an error. See the message above.
    pause
)
