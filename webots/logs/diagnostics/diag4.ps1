$ErrorActionPreference = "Continue"
$exe = "C:\Program Files\Webots\msys64\mingw64\bin\webots.exe"
$root = "D:\A.me\Simulate robot\webots"
$world = Join-Path $root "worlds\probe.wbt"
$out = Join-Path $root "logs\diag4.stdout.txt"
$err = Join-Path $root "logs\diag4.stderr.txt"
Remove-Item $out, $err -ErrorAction SilentlyContinue
$argLine = '--mode=realtime --batch --minimize --stdout --stderr --heartbeat=1000 "' + $world + '"'
$p = Start-Process -FilePath $exe -ArgumentList $argLine -WorkingDirectory $root -RedirectStandardOutput $out -RedirectStandardError $err -PassThru
Start-Sleep -Seconds 20
"--- webots processes and titles ---"
Get-Process | Where-Object { $_.ProcessName -like "*webots*" } | Select-Object Id, ProcessName, SessionId, Responding, MainWindowTitle | Format-List
"--- child processes ---"
$bin = Get-Process -Name "webots-bin" -ErrorAction SilentlyContinue
if ($bin) {
    Get-CimInstance Win32_Process -Filter "ParentProcessId=$($bin.Id)" | Select-Object ProcessId, Name, CommandLine | Format-List
}
"--- python processes ---"
Get-Process -Name "python*" -ErrorAction SilentlyContinue | Select-Object Id, ProcessName, SessionId, MainWindowTitle | Format-List
"--- stdout ---"
if (Test-Path $out) { Get-Content $out -Raw }
"--- stderr ---"
if (Test-Path $err) { Get-Content $err -Raw }
"MARKER_EXISTS=$(Test-Path (Join-Path $root 'logs\probe_entered.txt'))"
"--- temp dirs ---"
Get-ChildItem "$env:LOCALAPPDATA\Temp" -Filter "webots-*" -Directory -ErrorAction SilentlyContinue | Select-Object Name, LastWriteTime | Format-Table
Get-Process | Where-Object { $_.ProcessName -like "*webots*" } | Stop-Process -Force -ErrorAction SilentlyContinue
