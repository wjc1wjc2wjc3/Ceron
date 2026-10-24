@echo off
REM Ceron 一键本地启动（Windows 批处理）
REM 依次拉起：python-svc(8000) -> go-svc(8080) -> frontend(3000)
REM 内部用 PowerShell Start-Process 启动并捕获 PID，按任意键一键停止全部。
setlocal EnableDelayedExpansion

set "ROOT=%~dp0.."
set "PYDIR=%ROOT%\backend\python-svc"
set "GODIR=%ROOT%\backend\go-svc"
set "FEDIR=%ROOT%\frontend"
set "PYPORT=8000"
set "GOPORT=8080"
set "FEPORT=3000"

set "LOGDIR=%ROOT%\logs"
if not exist "%LOGDIR%" mkdir "%LOGDIR%"

set "PYTHON_SVC_URL=http://localhost:%PYPORT%"
set "GO_SVC_PORT=%GOPORT%"

REM —— 1. Python 智能层（venv + uvicorn）——
echo [ceron] 启动 python-svc :%PYPORT% ...
set "VENV=%PYDIR%\.venv"
if not exist "%VENV%" python -m venv "%VENV%" 2>nul
if exist "%VENV%\Scripts\pip.exe" "%VENV%\Scripts\pip.exe" install -q -r "%PYDIR%\requirements.txt" 2>nul
set "PYEXE=%VENV%\Scripts\python.exe"
if not exist "%PYEXE%" set "PYEXE=python"
for /f "delims=" %%P in ('powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%PYEXE%' -ArgumentList '-m','uvicorn','app.main:app','--host','0.0.0.0','--port','%PYPORT%','--reload' -WorkingDirectory '%PYDIR%' -RedirectStandardOutput '%LOGDIR%\py.log' -RedirectStandardError '%LOGDIR%\py.err' -NoNewWindow -PassThru | Select-Object -ExpandProperty Id"') do set "PYPID=%%P"

REM —— 2. Go 网关 ——
echo [ceron] 启动 go-svc :%GOPORT% ...
for /f "delims=" %%P in ('powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath 'go' -ArgumentList 'run','./cmd/server' -WorkingDirectory '%GODIR%' -RedirectStandardOutput '%LOGDIR%\go.log' -RedirectStandardError '%LOGDIR%\go.err' -NoNewWindow -PassThru | Select-Object -ExpandProperty Id"') do set "GOPID=%%P"

REM —— 3. 前端 ——
echo [ceron] 启动 frontend :%FEPORT% ...
if not exist "%FEDIR%\node_modules" call npm --prefix "%FEDIR%" install >nul 2>&1
for /f "delims=" %%P in ('powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath 'npm' -ArgumentList '--prefix','%FEDIR%','run','dev' -WorkingDirectory '%FEDIR%' -RedirectStandardOutput '%LOGDIR%\fe.log' -RedirectStandardError '%LOGDIR%\fe.err' -NoNewWindow -PassThru | Select-Object -ExpandProperty Id"') do set "FEPID=%%P"

REM 记录 PID，供 stop.bat 使用
echo %PYPID% %GOPID% %FEPID% > "%LOGDIR%\.pids"

REM —— 健康检查 ——
echo [ceron] 等待服务就绪...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$pyok=$false;$gook=$false;for($i=0;$i-lt30;$i++){if(-not $pyok){try{if((Invoke-RestMethod http://localhost:%PYPORT%/health -TimeoutSec 1).status){$pyok=$true;Write-Host '  [ok] python-svc'}}catch{}}if(-not $gook){try{if((Invoke-RestMethod http://localhost:%GOPORT%/health -TimeoutSec 1).status){$gook=$true;Write-Host '  [ok] go-svc'}}catch{}}if($pyok -and $gook){break}Start-Sleep -Seconds 1}"

echo.
echo [ceron] 已全部启动. 前端 http://localhost:%FEPORT%   (按任意键停止)
start "" http://localhost:%FEPORT%
pause >nul

echo [ceron] 停止所有服务...
if defined PYPID taskkill /PID %PYPID% /T /F >nul 2>&1
if defined GOPID taskkill /PID %GOPID% /T /F >nul 2>&1
if defined FEPID taskkill /PID %FEPID% /T /F >nul 2>&1
if exist "%LOGDIR%\.pids" del "%LOGDIR%\.pids" >nul 2>&1
echo [ceron] 已停止。
endlocal
