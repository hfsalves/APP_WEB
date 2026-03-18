@echo off
setlocal
start "" /min powershell.exe -WindowStyle Hidden -NoProfile -ExecutionPolicy Bypass -File "%~dp0restart_stationzero.ps1" -Mode Dev
endlocal
