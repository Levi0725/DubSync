@echo off
REM DubSync - Start script (Windows Batch)
REM This script activates the virtual environment and starts the program

REM Save the path of the file to open (if any)
set "OPEN_FILE=%~1"

REM Change to the script's own directory (where DubSync is installed)
cd /d "%~dp0"

echo.
echo ========================================
echo   DubSync - Professional Dubbing Translation Editor
echo ========================================
echo.

REM Searching for Python
set "PYTHON_CMD="
set "LIB_PYTHON=lib\py311-Windowsx86_64\python.exe"

REM First, check if system Python is available
where python >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_CMD=python"
    echo [OK] System Python found.
) else (
    REM If not, check the lib folder
    if exist "%LIB_PYTHON%" (
        set "PYTHON_CMD=%LIB_PYTHON%"
        echo [OK] Using embedded Python: %LIB_PYTHON%
    ) else (
        echo [X] Python not found!
        echo     Please install Python 3.10+ or place it in the lib folder.
        pause
        exit /b 1
    )
)

REM Check if the venv directory exists
if not exist "venv" (
    echo [!] Virtual environment not found.
    echo [*] Creating: %PYTHON_CMD% -m venv venv
    %PYTHON_CMD% -m venv venv
    if errorlevel 1 (
        echo [X] Error creating virtual environment!
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created.
)

REM Activate virtual environment
echo [*] Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [X] Error activating virtual environment!
    pause
    exit /b 1
)

REM Check dependencies with update_checker.py
echo [*] Checking dependencies (main + plugins)...
python update_checker.py
if errorlevel 1 (
    echo [X] Error checking dependencies!
    pause
    exit /b 1
)

REM Starting application
echo.
echo [*] Starting DubSync...
echo.
cd src

REM If a file parameter was received, pass it to the application
if "%OPEN_FILE%"=="" (
    python -m dubsync
) else (
    echo [*] Opening project: %OPEN_FILE%
    python -m dubsync "%OPEN_FILE%"
)

REM When the program exits
echo.
echo [*] DubSync closed.