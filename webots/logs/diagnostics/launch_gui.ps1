$exe = "C:\Program Files\Webots\msys64\mingw64\bin\webots.exe"
$root = "D:\A.me\Simulate robot\webots"
$world = Join-Path $root "worlds\probe.wbt"
$argLine = '--mode=pause "' + $world + '"'
$p = Start-Process -FilePath $exe -ArgumentList $argLine -WorkingDirectory $root -PassThru
Start-Sleep -Seconds 12
"LAUNCHER_PID=$($p.Id)"
Get-Process | Where-Object { $_.ProcessName -like "*webots*" } | Select-Object Id, ProcessName, MainWindowTitle | Format-List
