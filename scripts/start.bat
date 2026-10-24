@echo off
REM Ceron 一键本地启动（Windows 批处理）
REM 薄包装：调用同目录的 start.ps1（纯 PowerShell，无 cmd 引号陷阱），
REM 依次拉起 python-svc(8000) -> go-svc(8080) -> frontend(3000)，Ctrl+C 停止。
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1" %*
endlocal
