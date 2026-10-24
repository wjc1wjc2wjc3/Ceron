@echo off
REM Ceron 停止脚本：读取 scripts/start.bat 写入的 PID 并结束全部服务进程树。
setlocal
set "LOGDIR=%~dp0..\logs"
if not exist "%LOGDIR%\.pids" (
  echo [ceron] 未找到 PID 记录（可能未通过 start.bat 启动）。
  exit /b 1
)
for /f "tokens=1,2,3" %%a in (%LOGDIR%\.pids) do (
  if not "%%a"=="" taskkill /PID %%a /T /F >nul 2>&1
  if not "%%b"=="" taskkill /PID %%b /T /F >nul 2>&1
  if not "%%c"=="" taskkill /PID %%c /T /F >nul 2>&1
)
del "%LOGDIR%\.pids" >nul 2>&1
echo [ceron] 已停止。
endlocal
