param(
    [ValidateSet("clear", "blocked")]
    [string]$Scenario = "clear",
    [int]$WaitSeconds = 32,
    [string]$Command = "",
    [double]$TimeoutSeconds = 0
)
$ErrorActionPreference = "Continue"
Get-Process | Where-Object { $_.ProcessName -like "*webots*" -or $_.ProcessName -like "e-puck*" -or $_.ProcessName -like "python*" } | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$log = Join-Path $root "logs\robot_controller.log"
Remove-Item $log -ErrorAction SilentlyContinue
$exe = "C:\Program Files\Webots\msys64\mingw64\bin\webots.exe"
$world = Join-Path $root ("worlds\demo_" + $Scenario + ".wbt")
$argLine = '--mode=realtime --batch --minimize --no-rendering --stdout --stderr "' + $world + '"'
"SCENARIO=$Scenario"
"COMMAND=$Command"
"ARGS=$argLine"
if ($Command) { $env:SIMULATE_ROBOT_COMMAND = $Command } else { Remove-Item Env:SIMULATE_ROBOT_COMMAND -ErrorAction SilentlyContinue }
if ($TimeoutSeconds -gt 0) { $env:SIMULATE_ROBOT_TIMEOUT = "$TimeoutSeconds" } else { Remove-Item Env:SIMULATE_ROBOT_TIMEOUT -ErrorAction SilentlyContinue }
$p = Start-Process -FilePath $exe -ArgumentList $argLine -WorkingDirectory $root -PassThru
$deadline = (Get-Date).AddSeconds($WaitSeconds)
while ((Get-Date) -lt $deadline) {
    if (-not (Get-Process -Id $p.Id -ErrorAction SilentlyContinue)) { break }
    Start-Sleep -Seconds 1
}
"STILL_RUNNING=$([bool](Get-Process -Id $p.Id -ErrorAction SilentlyContinue))"
"--- controller log ---"
if (Test-Path $log) { Get-Content $log -Raw } else { "NO CONTROLLER LOG" }
"--- supervisor log ---"
$sup = Join-Path $root "logs\session_supervisor.log"
if (Test-Path $sup) { Get-Content $sup -Raw } else { "NO SUPERVISOR LOG" }
Get-Process | Where-Object { $_.ProcessName -like "*webots*" -or $_.ProcessName -like "e-puck*" -or $_.ProcessName -like "python*" } | Stop-Process -Force -ErrorAction SilentlyContinue
