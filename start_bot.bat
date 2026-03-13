@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
    echo [TeleWoW] Virtual environment not found: .venv\Scripts\activate.bat
    echo Run install_bot.bat first, or create it manually with: python -m venv .venv
    exit /b 1
)

call ".venv\Scripts\activate.bat"
python bot.py

set EXIT_CODE=%ERRORLEVEL%
if not "%EXIT_CODE%"=="0" (
    echo.
    echo [TeleWoW] Bot exited with code %EXIT_CODE%.
)

exit /b %EXIT_CODE%