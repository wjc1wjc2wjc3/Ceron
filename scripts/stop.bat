@echo off
REM Ceron stop script (thin wrapper, same pattern as start.bat)
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop.ps1"
if errorlevel 1 pause
endlocal
