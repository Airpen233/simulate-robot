$ErrorActionPreference = "Continue"
Get-Process | Where-Object { $_.ProcessName -like "*webots*" -or $_.ProcessName -like "e-puck*" -or $_.ProcessName -like "python*" } | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
$marker = "D:\A.me\Simulate robot\webots\logs\probe_entered.txt"
Remove-Item $marker -ErrorAction SilentlyContinue
$exe = "C:\Program Files\Webots\msys64\mingw64\bin\webots.exe"
$root = "D:\A.me\Simulate robot\webots"
$world = Join-Path $root "worlds\probe_https.wbt"
$out = Join-Path $root "logs\diag7.stdout.txt"
$err = Join-Path $root "logs\diag7.stderr.txt"
Remove-Item $out, $err -ErrorAction SilentlyContinue
$argLine = '--mode=realtime --batch --minimize --no-rendering --stdout --stderr --heartbeat=1000 "' + $world + '"'
$p = Start-Process -FilePath $exe -ArgumentList $argLine -WorkingDirectory $root -RedirectStandardOutput $out -RedirectStandardError $err -PassThru
Start-Sleep -Seconds 12
"--- windows ---"
Get-Process | Where-Object { $_.ProcessName -like "*webots*" } | Select-Object Id, ProcessName, MainWindowTitle | Format-List
"--- python/controller processes ---"
Get-Process | Where-Object { $_.ProcessName -like "*python*" -or $_.ProcessName -like "*puck*" } | Select-Object Id, ProcessName, MainWindowTitle | Format-List
"MARKER=$(Test-Path $marker)"
if (Test-Path $marker) { Get-Content $marker }
"--- stdout ---"
if (Test-Path $out) { Get-Content $out -Raw }
"--- stderr ---"
if (Test-Path $err) { Get-Content $err -Raw }
Get-Process | Where-Object { $_.ProcessName -like "*webots*" -or $_.ProcessName -like "e-puck*" -or $_.ProcessName -like "python*" } | Stop-Process -Force -ErrorAction SilentlyContinue
