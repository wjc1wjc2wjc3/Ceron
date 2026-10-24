# Ceron stop script: kill recorded PIDs and anything listening on 8000/8080/3000.
$ports = @(8000, 8080, 3000)
$killed = @()
foreach ($p in $ports) {
  try {
    (Get-NetTCPConnection -LocalPort $p -ErrorAction SilentlyContinue).OwningProcess |
      Sort-Object -Unique | ForEach-Object {
        if ($_) { taskkill /PID $_ /T /F 2>$null | Out-Null; $killed += $_ }
      }
  } catch {}
}
$pidFile = Join-Path $PSScriptRoot "..\logs\.pids"
if (Test-Path $pidFile) {
  Get-Content $pidFile | ForEach-Object {
    $id = (($_.Trim()) -split '\s+')[-1]
    if ($id) { taskkill /PID $id /T /F 2>$null | Out-Null }
  }
  Remove-Item $pidFile -ErrorAction SilentlyContinue
}
Write-Host ("[ceron] stopped. killed PIDs: " + ($killed -join ","))
