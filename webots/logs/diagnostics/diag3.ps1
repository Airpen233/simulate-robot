$ErrorActionPreference = "Continue"
$exe = "C:\Program Files\Webots\msys64\mingw64\bin\webots.exe"
$root = "D:\A.me\Simulate robot\webots"
$out = Join-Path $root "logs\diag3.stdout.txt"
$err = Join-Path $root "logs\diag3.stderr.txt"
$world = Join-Path $root "worlds\probe.wbt"
Remove-Item $out, $err -ErrorAction SilentlyContinue
$argLine = '--mode=realtime --batch --no-rendering --minimize --stdout --stderr --heartbeat=1000 "' + $world + '"'
"ARGS=$argLine"
$p = Start-Process -FilePath $exe -ArgumentList $argLine -WorkingDirectory $root -RedirectStandardOutput $out -RedirectStandardError $err -PassThru
Start-Sleep -Seconds 15
$alive = Get-Process -Id $p.Id -ErrorAction SilentlyContinue
if ($alive) {
    "ALIVE_AFTER_15S=YES"
    $alive | Select-Object Id, ProcessName
    "--- child processes ---"
    Get-CimInstance Win32_Process -Filter "ParentProcessId=$($p.Id)" | Select-Object ProcessId, Name, CommandLine | Format-List
    Stop-Process -Id $p.Id -Force
    Start-Sleep -Seconds 2
} else {
    "ALIVE_AFTER_15S=NO"
}
"--- STDOUT ---"
if (Test-Path $out) { Get-Content $out -Raw }
"--- STDERR ---"
if (Test-Path $err) { Get-Content $err -Raw }
"MARKER_EXISTS=$(Test-Path (Join-Path $root 'logs\probe_entered.txt'))"
"--- webots processes ---"
Get-Process | Where-Object { $_.ProcessName -like "*webots*" } | Select-Object Id, ProcessName
