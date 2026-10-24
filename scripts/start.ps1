# Ceron 一键本地启动（Windows / PowerShell）
# 依次拉起：python-svc(8000) → go-svc(8080) → frontend(3000)，Ctrl+C 一键停止全部。
param(
  [switch]$NoBrowser,   # 不自动打开浏览器
  [switch]$SkipInstall  # 跳过依赖安装（venv/npm install 已就绪时）
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$PyDir  = Join-Path $Root "backend/python-svc"
$GoDir  = Join-Path $Root "backend/go-svc"
$FeDir  = Join-Path $Root "frontend"
$PyPort = 8000; $GoPort = 8080; $FePort = 3000

$env:PYTHON_SVC_URL = "http://localhost:$PyPort"
$env:GO_SVC_PORT    = "$GoPort"

$LogDir = Join-Path $Root "logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

$Procs = @()

function Stop-All {
  Write-Host "`n[ceron] 停止所有服务…" -ForegroundColor Yellow
  foreach ($p in $Procs) {
    if ($null -eq $p -or $p.HasExited) { continue }
    taskkill /PID $p.Id /T /F 2>$null | Out-Null
  }
  Write-Host "[ceron] 已停止。" -ForegroundColor Green
}
# 注册 Ctrl+C / 关闭窗口时清理
$null = Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action { Stop-All }
try {
  [Console]::TreatControlCAsInput = $false
} catch {}

# —— 1. Python 智能层 ——
Write-Host "[ceron] 启动 python-svc :$PyPort …" -ForegroundColor Cyan
$venv = Join-Path $PyDir ".venv"
if (-not (Test-Path $venv)) {
  if (-not $SkipInstall) { & python -m venv $venv | Out-Null }
}
if (-not $SkipInstall -and (Test-Path (Join-Path $venv "Scripts/pip.exe"))) {
  & (Join-Path $venv "Scripts/pip.exe") install -q -r (Join-Path $PyDir "requirements.txt") | Out-Null
}
$pyExe = if (Test-Path (Join-Path $venv "Scripts/python.exe")) {
  Join-Path $venv "Scripts/python.exe"
} else { "python" }
$p = Start-Process -FilePath $pyExe -WorkingDirectory $PyDir `
  -ArgumentList "-m","uvicorn","app.main:app","--host","0.0.0.0","--port","$PyPort","--reload" `
  -RedirectStandardOutput (Join-Path $LogDir "py.log") `
  -RedirectStandardError  (Join-Path $LogDir "py.err") -NoNewWindow -PassThru
$Procs += $p

# —— 2. Go 网关 ——
Write-Host "[ceron] 启动 go-svc :$GoPort …" -ForegroundColor Cyan
$g = Start-Process -FilePath "go" -WorkingDirectory $GoDir `
  -ArgumentList "run","./cmd/server" `
  -RedirectStandardOutput (Join-Path $LogDir "go.log") `
  -RedirectStandardError  (Join-Path $LogDir "go.err") -NoNewWindow -PassThru
$Procs += $g

# —— 3. 前端 ——
Write-Host "[ceron] 启动 frontend :$FePort …" -ForegroundColor Cyan
if (-not $SkipInstall -and -not (Test-Path (Join-Path $FeDir "node_modules"))) {
  & npm --prefix $FeDir install | Out-Null
}
$f = Start-Process -FilePath "npm" -WorkingDirectory $FeDir `
  -ArgumentList "--prefix",$FeDir,"run","dev" `
  -RedirectStandardOutput (Join-Path $LogDir "fe.log") `
  -RedirectStandardError  (Join-Path $LogDir "fe.err") -NoNewWindow -PassThru
$Procs += $f

function Test-Health($url) {
  try { (Invoke-RestMethod -Uri $url -TimeoutSec 1).status } catch { $null }
}
Write-Host "[ceron] 等待服务就绪…" -ForegroundColor Cyan
$pyOk=$false;$goOk=$false
for ($i=0; $i -lt 30; $i++) {
  if (-not $pyOk) { $r=Test-Health "http://localhost:$PyPort/health"; if ($r) { $pyOk=$true; Write-Host "  ✓ python-svc 就绪" -ForegroundColor Green } }
  if (-not $goOk) { $r=Test-Health "http://localhost:$GoPort/health"; if ($r) { $goOk=$true; Write-Host "  ✓ go-svc 就绪" -ForegroundColor Green } }
  if ($pyOk -and $goOk) { break }
  Start-Sleep -Seconds 1
}
Write-Host ""
Write-Host "[ceron] 已全部启动。前端 http://localhost:$FePort   (Ctrl+C 停止)" -ForegroundColor Green
Write-Host "[ceron]   日志目录: $LogDir" -ForegroundColor DarkGray

if (-not $NoBrowser) {
  Start-Sleep -Seconds 3
  try { Start-Process "http://localhost:$FePort" } catch {}
}

try {
  while ($true) { Start-Sleep -Seconds 1 }
} finally {
  Stop-All
}
