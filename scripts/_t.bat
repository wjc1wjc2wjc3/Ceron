@echo off
echo === TEST1: python launch line ===
powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath 'python' -ArgumentList '-m','uvicorn','app.main:app' -WorkingDirectory 'c:\Users\wjc\Desktop\alun\Ceron\backend\python-svc' -NoNewWindow -PassThru | Select-Object -ExpandProperty Id | Out-File -Encoding ascii 'c:\temp\t.pid'"
echo done1
echo === TEST2: health line ===
powershell -NoProfile -ExecutionPolicy Bypass -Command "$pyok=$false;for($i=0;$i-lt2;$i++){Write-Host '  [ok] x'}"
echo done2
