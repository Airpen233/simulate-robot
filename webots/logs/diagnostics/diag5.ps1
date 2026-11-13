$ErrorActionPreference = "Continue"
Get-Process | Where-Object { $_.ProcessName -like "*webots*" -or $_.ProcessName -like "e-puck*" } | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
$exe = "C:\Program Files\Webots\msys64\mingw64\bin\webots.exe"
$world = "C:\Program Files\Webots\projects\robots\gctronic\e-puck\worlds\e-puck.wbt"
$argLine = '--minimize "' + $world + '"'
"ARGS=$argLine"
$p = Start-Process -FilePath $exe -ArgumentList $argLine -WorkingDirectory "C:\Program Files\Webots\projects\robots\gctronic\e-puck" -PassThru
Start-Sleep -Seconds 12
"--- processes ---"
Get-Process | Where-Object { $_.ProcessName -like "*webots*" -or $_.ProcessName -like "*puck*" -or $_.ProcessName -like "*python*" } | Select-Object Id, ProcessName, MainWindowTitle | Format-List
"--- webots process tree ---"
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'webots|e-puck' } | Select-Object ProcessId, ParentProcessId, Name, CommandLine | Format-List
Get-Process | Where-Object { $_.ProcessName -like "*webots*" -or $_.ProcessName -like "e-puck*" } | Stop-Process -Force -ErrorAction SilentlyContinue
