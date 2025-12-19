@echo off
REM DubSync - Indító script (Windows Batch)
REM Ez a script aktiválja a virtuális környezetet és elindítja a programot

REM Mentjük a megnyitandó fájl elérési útját (ha van)
set "OPEN_FILE=%~1"

REM Váltás a script saját könyvtárába (ahol a DubSync van telepítve)
cd /d "%~dp0"

echo.
echo ========================================
echo   DubSync - Szinkronforditoi Editor
echo ========================================
echo.

REM Python keresése
set "PYTHON_CMD="
set "LIB_PYTHON=lib\py311-Windowsx86_64\python.exe"

REM Először ellenőrizzük, hogy van-e rendszer Python
where python >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_CMD=python"
    echo [OK] Rendszer Python talalhato.
) else (
    REM Ha nincs, nézzük a lib mappát
    if exist "%LIB_PYTHON%" (
        set "PYTHON_CMD=%LIB_PYTHON%"
        echo [OK] Beagyazott Python hasznalata: %LIB_PYTHON%
    ) else (
        echo [X] Python nem talalhato!
        echo     Telepitsd a Python 3.10+-t vagy helyezd a lib mappaba.
        pause
        exit /b 1
    )
)

REM Ellenőrizzük, hogy a venv könyvtár létezik-e
if not exist "venv" (
    echo [!] Virtualis kornyezet nem talalhato.
    echo [*] Letrehozas: %PYTHON_CMD% -m venv venv
    %PYTHON_CMD% -m venv venv
    if errorlevel 1 (
        echo [X] Hiba a virtualis kornyezet letrehozasakor!
        pause
        exit /b 1
    )
    echo [OK] Virtualis kornyezet letrehozva.
)

REM Virtuális környezet aktiválása
echo [*] Virtualis kornyezet aktivalasa...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [X] Hiba az aktivalaskor!
    pause
    exit /b 1
)

REM Függőségek ellenőrzése az update_checker.py-vel
echo [*] Fuggosegek ellenorzese (fo + pluginok)...
python update_checker.py
if errorlevel 1 (
    echo [X] Hiba a fuggosegek ellenorzese soran!
    pause
    exit /b 1
)

REM Alkalmazás indítása
echo.
echo [*] DubSync inditasa...
echo.
cd src

REM Ha kapott fájl paramétert, adjuk át az alkalmazásnak
if "%OPEN_FILE%"=="" (
    python -m dubsync
) else (
    echo [*] Projekt megnyitasa: %OPEN_FILE%
    python -m dubsync "%OPEN_FILE%"
)

REM Ha kilépett a program
echo.
echo [*] DubSync bezarva.
