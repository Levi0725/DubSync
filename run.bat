@echo off
REM DubSync - Start script (Windows Batch)
REM This script activates the virtual environment and starts the program
REM Usage: run.bat [project_file] [--debug]

REM Parse arguments
set "OPEN_FILE="
set "DEBUG_FLAG="

:parse_args
if "%~1"=="" goto :done_parsing
if /i "%~1"=="--debug" (
    set "DEBUG_FLAG=--debug"
) else if /i "%~1"=="-d" (
    set "DEBUG_FLAG=--debug"
) else (
    set "OPEN_FILE=%~1"
)
shift
goto :parse_args
:done_parsing

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
if not "%DEBUG_FLAG%"=="" echo [*] Debug mode enabled.
echo.
cd src

REM Build command with optional arguments
set "CMD=python -m dubsync"
if not "%OPEN_FILE%"=="" (
    echo [*] Opening project: %OPEN_FILE%
    set "CMD=%CMD% "%OPEN_FILE%""
)
if not "%DEBUG_FLAG%"=="" (
    set "CMD=%CMD% %DEBUG_FLAG%"
)

REM Execute
%CMD%

REM When the program exits
echo.
echo [*] DubSync closed.