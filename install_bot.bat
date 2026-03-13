@echo off
setlocal EnableExtensions
title TeleWoW Installer

cd /d "%~dp0"

echo ============================================================
echo TeleWoW One-Click Installer
echo ============================================================
echo.
echo This installer only installs the TeleWoW bot in this folder.
echo It does not install or configure your WoW repack.
echo.
echo Prerequisites:
echo - Windows with internet access
echo - This repository folder must be named tele-wow
echo - tele-wow must be placed beside Database and Repack
echo - Your repack files must already exist
echo.
echo After installation you still need to:
echo - Create your Telegram bot and get the token
echo - Edit .env with your Telegram and repack settings
echo - Enable RA in Repack\worldserver.conf if you want remote commands
echo - Start the bot with start_bot.bat
echo.
choice /C YN /N /M "Continue with installation? [Y/N]: "
if errorlevel 2 (
    echo Installation cancelled.
    exit /b 0
)

echo.
echo [1/7] Checking repository location...
if /I not "%~n0"=="install_bot" (
    rem no-op, keeps batch parser stable on older systems
)
if /I not "%CD:~-8%"=="tele-wow" (
    echo [TeleWoW] Warning: the current folder is not named tele-wow.
)
if not exist "..\Database\" (
    echo [TeleWoW] Missing sibling folder: ..\Database
    echo Move this repository so the structure is:
    echo   Database\
    echo   Repack\
    echo   tele-wow\
    pause
    exit /b 1
)
if not exist "..\Repack\" (
    echo [TeleWoW] Missing sibling folder: ..\Repack
    echo Move this repository so the structure is:
    echo   Database\
    echo   Repack\
    echo   tele-wow\
    pause
    exit /b 1
)
if not exist "requirements.txt" (
    echo [TeleWoW] requirements.txt was not found in this folder.
    pause
    exit /b 1
)
if not exist ".env.example" (
    echo [TeleWoW] .env.example was not found in this folder.
    pause
    exit /b 1
)

echo [2/7] Checking Python 3.11+...
call :detect_python
if errorlevel 1 (
    echo Python 3.11+ was not found. Trying to install it with winget...
    call :install_python
    if errorlevel 1 (
        echo [TeleWoW] Python installation failed.
        pause
        exit /b 1
    )
    call :detect_python
    if errorlevel 1 (
        echo [TeleWoW] Python was installed, but this terminal still cannot find it.
        echo Close this window, open a new one, and run install_bot.bat again.
        pause
        exit /b 1
    )
)
echo Using %PYTHON_EXE% %PYTHON_ARGS%

echo [3/7] Creating virtual environment...
if exist ".venv\Scripts\python.exe" (
    echo Existing virtual environment found. Reusing it.
) else (
    call "%PYTHON_EXE%" %PYTHON_ARGS% -m venv .venv
    if errorlevel 1 (
        echo [TeleWoW] Failed to create .venv
        pause
        exit /b 1
    )
)

echo [4/7] Activating virtual environment...
call ".venv\Scripts\activate.bat"
if errorlevel 1 (
    echo [TeleWoW] Failed to activate .venv
    pause
    exit /b 1
)

echo [5/7] Updating pip and installing requirements...
python -m pip install --upgrade pip
if errorlevel 1 (
    echo [TeleWoW] Failed to update pip
    pause
    exit /b 1
)
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo [TeleWoW] Failed to install requirements
    pause
    exit /b 1
)

echo [6/7] Preparing environment file...
if exist ".env" (
    echo Existing .env found. Keeping your current configuration.
) else (
    copy /Y ".env.example" ".env" >nul
    if errorlevel 1 (
        echo [TeleWoW] Failed to create .env from .env.example
        pause
        exit /b 1
    )
    echo Created .env from .env.example
)

echo [7/7] Installation complete.
echo.
echo TeleWoW is installed in:
echo %CD%
echo.
echo Next steps:
echo 1. Open TELEGRAM_SETUP.md and create your Telegram bot
echo 2. Edit .env and fill in TELEGRAM_BOT_TOKEN, TELEGRAM_ALLOWED_USER_IDS, and TELEGRAM_ALERT_CHAT_ID
echo 3. Review the default ../Repack and ../Database paths in .env
echo 4. Enable RA in Repack\worldserver.conf if you want remote commands
echo 5. Create or verify an RA account with enough access level
echo 6. Start the bot with start_bot.bat
echo.
echo Optional checks added by the installer:
echo - Python version validation
echo - Safe reuse of an existing .venv
echo - .env is not overwritten if you already configured it
echo.
pause
exit /b 0

:detect_python
set "PYTHON_EXE="
set "PYTHON_ARGS="

if exist "%LocalAppData%\Programs\Python\Launcher\py.exe" (
    "%LocalAppData%\Programs\Python\Launcher\py.exe" -3.11 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul
    if not errorlevel 1 (
        set "PYTHON_EXE=%LocalAppData%\Programs\Python\Launcher\py.exe"
        set "PYTHON_ARGS=-3.11"
        exit /b 0
    )
)

where py >nul 2>nul
if not errorlevel 1 (
    py -3.11 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul
    if not errorlevel 1 (
        set "PYTHON_EXE=py"
        set "PYTHON_ARGS=-3.11"
        exit /b 0
    )
    py -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul
    if not errorlevel 1 (
        set "PYTHON_EXE=py"
        set "PYTHON_ARGS="
        exit /b 0
    )
)

where python >nul 2>nul
if not errorlevel 1 (
    python -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul
    if not errorlevel 1 (
        set "PYTHON_EXE=python"
        set "PYTHON_ARGS="
        exit /b 0
    )
)

exit /b 1

:install_python
where winget >nul 2>nul
if errorlevel 1 (
    echo [TeleWoW] winget is not available on this system.
    echo Install Python 3.11+ manually, then run install_bot.bat again.
    exit /b 1
)

winget install -e --id Python.Python.3.11 --accept-package-agreements --accept-source-agreements
if errorlevel 1 (
    exit /b 1
)

set "PATH=%LocalAppData%\Programs\Python\Launcher;%LocalAppData%\Microsoft\WindowsApps;%PATH%"
exit /b 0