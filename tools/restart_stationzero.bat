@echo off
setlocal

fltmc >nul 2>&1
if errorlevel 1 (
    echo A pedir permissao de administrador...
    powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath 'powershell.exe' -Verb RunAs -ArgumentList '-NoExit -NoProfile -ExecutionPolicy Bypass -File ""%~dp0restart_stationzero.ps1""'"
    exit /b
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0restart_stationzero.ps1" %*
endlocal
pause
