$ErrorActionPreference = "Stop"
$root = "D:\A.me\Simulate robot\webots"
$exe = "C:\Program Files\Webots\msys64\mingw64\bin\webots.exe"
$out = Join-Path $root "logs\diag.stdout.txt"
$err = Join-Path $root "logs\diag.stderr.txt"
$perf = Join-Path $root "logs\diag_perf.txt"
$world = Join-Path $root "worlds\probe.wbt"
Remove-Item $out, $err, $perf -ErrorAction SilentlyContinue
$args = @("--mode=fast", "--batch", "--no-rendering", "--minimize", "--stdout", "--stderr", "--log-performance=$perf,200", $world)
$p = Start-Process -FilePath $exe -ArgumentList $args -WorkingDirectory $root -RedirectStandardOutput $out -RedirectStandardError $err -PassThru
Start-Sleep -Seconds 25
$running = -not $p.HasExited
if ($running) {
    $p.Kill()
    Start-Sleep -Seconds 2
}
"PID=$($p.Id) WAS_RUNNING=$running"
if (Test-Path $out) { "--- STDOUT ---"; Get-Content $out -Raw }
if (Test-Path $err) { "--- STDERR ---"; Get-Content $err -Raw }
if (Test-Path $perf) { "--- PERF (exists) ---"; Get-Content $perf -Raw } else { "PERF_EXISTS=NO" }
$marker = Join-Path $root "logs\probe_entered.txt"
"MARKER_EXISTS=$(Test-Path $marker)"
Get-Process | Where-Object { $_.ProcessName -like "*webots*" } | Select-Object Id, ProcessName
