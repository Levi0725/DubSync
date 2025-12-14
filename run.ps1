# DubSync - Indító script (PowerShell)
# Ez a script aktiválja a virtuális környezetet és elindítja a programot

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  DubSync - Szinkronfordítói Editor" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$ErrorActionPreference = "Stop"

# Script könyvtár beállítása
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# Python keresése
$pythonCmd = $null
$libPython = "lib\py311-Windowsx86_64\python.exe"

# Először ellenőrizzük, hogy van-e rendszer Python
$systemPython = Get-Command python -ErrorAction SilentlyContinue
if ($systemPython) {
    $pythonCmd = "python"
    Write-Host "[OK] Rendszer Python található." -ForegroundColor Green
}
elseif (Test-Path $libPython) {
    $pythonCmd = $libPython
    Write-Host "[OK] Beágyazott Python használata: $libPython" -ForegroundColor Green
}
else {
    Write-Host "[X] Python nem található!" -ForegroundColor Red
    Write-Host "    Telepítsd a Python 3.10+-t vagy helyezd a lib mappába."
    Read-Host "Nyomj ENTER-t a kilépéshez"
    exit 1
}

# Ellenőrizzük, hogy a venv könyvtár létezik-e
if (-not (Test-Path "venv")) {
    Write-Host "[!] Virtuális környezet nem található." -ForegroundColor Yellow
    Write-Host "[*] Létrehozás: $pythonCmd -m venv venv" -ForegroundColor Gray
    
    try {
        & $pythonCmd -m venv venv
        Write-Host "[OK] Virtuális környezet létrehozva." -ForegroundColor Green
    }
    catch {
        Write-Host "[X] Hiba a virtuális környezet létrehozásakor!" -ForegroundColor Red
        Write-Host $_.Exception.Message
        Read-Host "Nyomj ENTER-t a kilépéshez"
        exit 1
    }
}

# Virtuális környezet aktiválása
Write-Host "[*] Virtuális környezet aktiválása..." -ForegroundColor Gray
$activateScript = ".\venv\Scripts\Activate.ps1"

if (-not (Test-Path $activateScript)) {
    Write-Host "[X] Aktiváló script nem található: $activateScript" -ForegroundColor Red
    Read-Host "Nyomj ENTER-t a kilépéshez"
    exit 1
}

try {
    & $activateScript
}
catch {
    Write-Host "[X] Hiba az aktiváláskor!" -ForegroundColor Red
    Write-Host $_.Exception.Message
    Write-Host ""
    Write-Host "Tipp: Futtasd a következőt rendszergazdaként:" -ForegroundColor Yellow
    Write-Host "  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser" -ForegroundColor Yellow
    Read-Host "Nyomj ENTER-t a kilépéshez"
    exit 1
}

# Függőségek ellenőrzése (fő + pluginok)
Write-Host "[*] Függőségek ellenőrzése (fő + pluginok)..." -ForegroundColor Gray

try {
    python update_checker.py
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[!] Néhány függőség telepítése sikertelen." -ForegroundColor Yellow
    }
}
catch {
    Write-Host "[X] Hiba a függőségek ellenőrzésekor!" -ForegroundColor Red
    Write-Host $_.Exception.Message
    
    # Fallback: csak a fő requirements.txt
    Write-Host "[*] Fallback: fő függőségek telepítése..." -ForegroundColor Yellow
    pip install -r requirements.txt
}

# Alkalmazás indítása
Write-Host ""
Write-Host "[*] DubSync indítása..." -ForegroundColor Cyan
Write-Host ""

try {
    Set-Location "src"
    python -m dubsync
}
catch {
    Write-Host "[X] Hiba az alkalmazás futtatásakor!" -ForegroundColor Red
    Write-Host $_.Exception.Message
}

Write-Host ""
Write-Host "[*] DubSync bezárva." -ForegroundColor Gray
