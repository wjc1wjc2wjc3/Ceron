# Ceron one-click local launcher (Windows / PowerShell)
# Starts python-svc(8000) -> go-svc(8080) -> frontend(3000), Ctrl+C stops all.
param(
  [switch]$NoBrowser,   # do not open browser
  [switch]$SkipInstall  # skip dependency install (venv / npm install)
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

function Test-Health($url) {
  try { (Invoke-RestMethod -Uri $url -TimeoutSec 1).status } catch { $null }
}
function Test-Port($port) {
  try { [bool](Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) } catch { $false }
}

function Stop-All {
  Write-Host "`n[ceron] stopping all services..." -ForegroundColor Yellow
  foreach ($p in $Procs) {
    if ($null -eq $p -or $p.HasExited) { continue }
    taskkill /PID $p.Id /T /F 2>$null | Out-Null
  }
  Remove-Item (Join-Path $LogDir ".pids") -ErrorAction SilentlyContinue
  Write-Host "[ceron] stopped." -ForegroundColor Green
}
$null = Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action { Stop-All }
try { [Console]::TreatControlCAsInput = $false } catch {}

# --- 1. Python intelligence layer (non-fatal: do not block go/frontend) ---
Write-Host "[ceron] starting python-svc :$PyPort ..." -ForegroundColor Cyan
if (Test-Port $PyPort) {
  Write-Host "[ceron] :$PyPort already in use - python-svc assumed running (skip)" -ForegroundColor DarkCyan
} else {
try {
  $venv = Join-Path $PyDir ".venv"
  if (-not (Test-Path $venv)) {
    if (-not $SkipInstall) { & py -m venv $venv | Out-Null }
  }
  if (-not $SkipInstall -and (Test-Path (Join-Path $venv "Scripts/pip.exe"))) {
    & (Join-Path $venv "Scripts/pip.exe") install -q -r (Join-Path $PyDir "requirements.txt") | Out-Null
  }
  $pyExe = if (Test-Path (Join-Path $venv "Scripts/python.exe")) {
    Join-Path $venv "Scripts/python.exe"
  } else { "py" }
  if (-not (Get-Command $pyExe -ErrorAction SilentlyContinue)) {
    throw "python interpreter not found (try: py -m pip install -r requirements.txt)"
  }
  $p = Start-Process -FilePath $pyExe -WorkingDirectory $PyDir `
    -ArgumentList "-m","uvicorn","app.main:app","--host","0.0.0.0","--port","$PyPort","--reload" `
    -RedirectStandardOutput (Join-Path $LogDir "py.log") `
    -RedirectStandardError  (Join-Path $LogDir "py.err") -NoNewWindow -PassThru
  $Procs += $p
} catch {
  Write-Host "[ceron] WARNING: python-svc not started: $_" -ForegroundColor Yellow
}
}

# --- 2. Go gateway (build once, then run the binary so the recorded PID is the server) ---
Write-Host "[ceron] starting go-svc :$GoPort ..." -ForegroundColor Cyan
if (Test-Port $GoPort) {
  Write-Host "[ceron] :$GoPort already in use - go-svc assumed running (skip)" -ForegroundColor DarkCyan
} else {
try {
  $goBin = Join-Path $env:TEMP "ceron-gateway.exe"
  Push-Location $GoDir
  try {
    & go build -o $goBin ./cmd/server 2>&1 | Out-Null
  } finally {
    Pop-Location
  }
  if (-not (Test-Path $goBin)) { throw "go build failed" }
  $g = Start-Process -FilePath $goBin -WorkingDirectory $GoDir `
    -RedirectStandardOutput (Join-Path $LogDir "go.log") `
    -RedirectStandardError  (Join-Path $LogDir "go.err") -NoNewWindow -PassThru
  $Procs += $g
} catch {
  Write-Host "[ceron] WARNING: go-svc not started: $_" -ForegroundColor Yellow
}
}

# --- 3. Frontend ---
Write-Host "[ceron] starting frontend :$FePort ..." -ForegroundColor Cyan
if (-not $SkipInstall -and -not (Test-Path (Join-Path $FeDir "node_modules"))) {
  & npm --prefix $FeDir install | Out-Null
}
# npm on Windows is npm.cmd, launch via cmd /c
$f = Start-Process -FilePath "cmd.exe" -WorkingDirectory $FeDir `
  -ArgumentList "/c","npm","--prefix",$FeDir,"run","dev" `
  -RedirectStandardOutput (Join-Path $LogDir "fe.log") `
  -RedirectStandardError  (Join-Path $LogDir "fe.err") -NoNewWindow -PassThru
$Procs += $f

# Persist PIDs for external stop.bat
$Procs | ForEach-Object { $_.Id } | Where-Object { $_ -ne 0 } | Out-File -Encoding ascii (Join-Path $LogDir ".pids")

Write-Host "[ceron] waiting for services..." -ForegroundColor Cyan
$pyOk = Test-Port $PyPort; $goOk = Test-Port $GoPort
for ($i = 0; $i -lt 30; $i++) {
  if (-not $pyOk) { $r = Test-Health "http://localhost:$PyPort/health"; if ($r) { $pyOk = $true; Write-Host "  OK python-svc" -ForegroundColor Green } }
  if (-not $goOk) { $r = Test-Health "http://localhost:$GoPort/health"; if ($r) { $goOk = $true; Write-Host "  OK go-svc" -ForegroundColor Green } }
  if ($pyOk -and $goOk) { break }
  Start-Sleep -Seconds 1
}
# --- 4. Wait for frontend readiness (first Next.js compile may take tens of seconds) ---
Write-Host "[ceron] waiting for frontend (first compile may take ~30s)..." -ForegroundColor Cyan
$feOk = $false
for ($i = 0; $i -lt 90; $i++) {
  try {
    $resp = Invoke-WebRequest "http://localhost:$FePort" -TimeoutSec 2 -UseBasicParsing
    if ($resp.StatusCode -eq 200) { $feOk = $true; break }
  } catch {}
  Start-Sleep -Seconds 1
}
if ($feOk) { Write-Host "  OK frontend" -ForegroundColor Green }
else { Write-Host "  WARN frontend not ready after 90s (check logs\fe.log / logs\fe.err)" -ForegroundColor Yellow }

Write-Host ""
Write-Host "[ceron] all started. Frontend http://localhost:$FePort   (Ctrl+C or scripts\stop.bat to stop)" -ForegroundColor Green
Write-Host "[ceron]   logs: $LogDir" -ForegroundColor DarkGray

if (-not $NoBrowser -and $feOk) {
  try { Start-Process "http://localhost:$FePort" } catch {}
}

try {
  while ($true) { Start-Sleep -Seconds 1 }
} finally {
  Stop-All
}
