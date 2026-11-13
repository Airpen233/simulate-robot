$ErrorActionPreference = "Continue"
$ctrl = "D:\A.me\Simulate robot\webots\controllers\probe"
$py = "C:\Users\Airpen\AppData\Local\Programs\Python\Python312\python.exe"
$out = "D:\A.me\Simulate robot\webots\logs\manual_probe.stdout.txt"
$err = "D:\A.me\Simulate robot\webots\logs\manual_probe.stderr.txt"
Remove-Item $out, $err -ErrorAction SilentlyContinue
Remove-Item (Join-Path $ctrl "..\..\logs\probe_entered.txt") -ErrorAction SilentlyContinue
$env:PYTHONPATH = "C:\Program Files\Webots\lib\controller\python"
$env:WEBOTS_ROBOT_NAME = "e-puck"
$env:PYTHONIOENCODING = "UTF-8"
Push-Location $ctrl
"--- version check ---"
& $py -u -c "import sys;print(sys.version);print(sys.maxsize > 2**32)"
"EXIT=$LASTEXITCODE"
"--- launch probe.py (5s timeout) ---"
$p = Start-Process -FilePath $py -ArgumentList '-u probe.py' -WorkingDirectory $ctrl -RedirectStandardOutput $out -RedirectStandardError $err -PassThru
Start-Sleep -Seconds 5
if (-not $p.HasExited) { $p.Kill(); Start-Sleep -Seconds 1; "KILLED=YES" } else { "KILLED=NO" }
Pop-Location
"--- stdout ---"
if (Test-Path $out) { Get-Content $out -Raw }
"--- stderr ---"
if (Test-Path $err) { Get-Content $err -Raw }
"MARKER=$(Test-Path 'D:\A.me\Simulate robot\webots\logs\probe_entered.txt')"
