$ErrorActionPreference = "Continue"
$bin = "C:\Program Files\Webots\msys64\mingw64\bin\webots-bin.exe"
$exe = "C:\Program Files\Webots\msys64\mingw64\bin\webots.exe"
$root = "D:\A.me\Simulate robot\webots"
$out = Join-Path $root "logs\diag2.stdout.txt"
$err = Join-Path $root "logs\diag2.stderr.txt"
$perf = Join-Path $root "logs\diag2_perf.txt"
$world = Join-Path $root "worlds\probe.wbt"
Remove-Item $out, $err, $perf -ErrorAction SilentlyContinue
"--- webots.exe --version ---"
& $exe --version 2>&1
"EXIT=$LASTEXITCODE"
"--- webots-bin.exe --version ---"
& $bin --version 2>&1
"EXIT=$LASTEXITCODE"
"--- launch probe via webots-bin.exe ---"
$args = @("--mode=fast", "--batch", "--no-rendering", "--minimize", "--stdout", "--stderr", "--log-performance=$perf,200", $world)
$p = Start-Process -FilePath $bin -ArgumentList $args -WorkingDirectory $root -RedirectStandardOutput $out -RedirectStandardError $err -PassThru
$p.WaitForExit(30000) | Out-Null
if (-not $p.HasExited) { $p.Kill(); Start-Sleep -Seconds 1; "KILLED=YES" } else { "KILLED=NO" }
try { "EXITCODE=$($p.ExitCode)" } catch { "EXITCODE=unavailable" }
if (Test-Path $out) { "--- STDOUT ---"; Get-Content $out -Raw }
if (Test-Path $err) { "--- STDERR ---"; Get-Content $err -Raw }
if (Test-Path $perf) { "PERF_EXISTS=YES"; Get-Content $perf -Raw } else { "PERF_EXISTS=NO" }
"MARKER_EXISTS=$(Test-Path (Join-Path $root 'logs\probe_entered.txt'))"
"--- recent app errors ---"
Get-WinEvent -FilterHashtable @{LogName='Application'; StartTime=(Get-Date).AddMinutes(-15)} -ErrorAction SilentlyContinue |
    Where-Object { $_.Message -match 'webots' -or $_.ProviderName -match 'Application Error|Windows Error Reporting' } |
    Select-Object -First 8 TimeCreated, ProviderName, Id, LevelDisplayName, Message |
    Format-List
