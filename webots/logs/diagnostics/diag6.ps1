$ErrorActionPreference = "Continue"
Get-Process | Where-Object { $_.ProcessName -like "*webots*" -or $_.ProcessName -like "e-puck*" } | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
$exe = "C:\Program Files\Webots\msys64\mingw64\bin\webots.exe"
$root = "C:\Program Files\Webots\projects\robots\gctronic\e-puck"
$world = Join-Path $root "worlds\e-puck.wbt"
$out = "D:\A.me\Simulate robot\webots\logs\diag6.stdout.txt"
$err = "D:\A.me\Simulate robot\webots\logs\diag6.stderr.txt"
Remove-Item $out, $err -ErrorAction SilentlyContinue
$argLine = '--mode=realtime --batch --minimize --no-rendering --stdout --stderr --heartbeat=1000 "' + $world + '"'
"ARGS=$argLine"
$p = Start-Process -FilePath $exe -ArgumentList $argLine -WorkingDirectory $root -RedirectStandardOutput $out -RedirectStandardError $err -PassThru
Start-Sleep -Seconds 15
"--- windows ---"
Get-Process | Where-Object { $_.ProcessName -like "*webots*" } | Select-Object Id, ProcessName, MainWindowTitle | Format-List
"--- controllers ---"
Get-Process | Where-Object { $_.ProcessName -like "*e-puck*" -or $_.ProcessName -like "*python*" } | Select-Object Id, ProcessName, MainWindowTitle | Format-List
Get-CimInstance Win32_Process | Where-Object { $_.ParentProcessId -eq (Get-Process webots-bin -ErrorAction SilentlyContinue).Id } | Select-Object ProcessId, Name, CommandLine | Format-List
"--- stdout ---"
if (Test-Path $out) { Get-Content $out -Raw }
"--- stderr ---"
if (Test-Path $err) { Get-Content $err -Raw }
Get-Process | Where-Object { $_.ProcessName -like "*webots*" -or $_.ProcessName -like "e-puck*" } | Stop-Process -Force -ErrorAction SilentlyContinue
