param(
    [string]$Mode = "navigate",
    [string]$WorldFile = "stage2_lab.wbt",
    [double]$TargetX = 0.8,
    [double]$TargetY = 0.8,
    [double]$Angle = 90,
    [double]$Distance = 0.5,
    [double]$Left = 2.0,
    [double]$Right = 2.0,
    [double]$Duration = 2.0,
    [int]$WaitSeconds = 25
)
$ErrorActionPreference = "Continue"
Get-Process | Where-Object { $_.ProcessName -like "*webots*" -or $_.ProcessName -like "python*" } | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$motionLog = Join-Path $root "logs\motion_controller.log"
$supervisorLog = Join-Path $root "logs\session_supervisor.log"
Remove-Item $motionLog, $supervisorLog -ErrorAction SilentlyContinue
$exe = "C:\Program Files\Webots\msys64\mingw64\bin\webots.exe"
$world = Join-Path $root ("worlds\" + $WorldFile)
$env:SIMULATE_MODE = $Mode
$env:SIMULATE_TARGET_X = "$TargetX"
$env:SIMULATE_TARGET_Y = "$TargetY"
$env:SIMULATE_ANGLE_DEG = "$Angle"
$env:SIMULATE_DISTANCE = "$Distance"
$env:SIMULATE_LEFT = "$Left"
$env:SIMULATE_RIGHT = "$Right"
$env:SIMULATE_DURATION = "$Duration"
"RUN mode=$Mode target=($TargetX,$TargetY) angle=$Angle distance=$Distance left=$Left right=$Right duration=$Duration"
$argLine = '--mode=realtime --batch --minimize --no-rendering --stdout --stderr "' + $world + '"'
$p = Start-Process -FilePath $exe -ArgumentList $argLine -WorkingDirectory $root -PassThru
$deadline = (Get-Date).AddSeconds($WaitSeconds)
while ((Get-Date) -lt $deadline) {
    if (-not (Get-Process -Id $p.Id -ErrorAction SilentlyContinue)) { break }
    Start-Sleep -Seconds 1
}
"STILL_RUNNING=$([bool](Get-Process -Id $p.Id -ErrorAction SilentlyContinue))"
"--- motion log ---"
if (Test-Path $motionLog) { Get-Content $motionLog -Raw } else { "NO MOTION LOG" }
"--- supervisor log ---"
if (Test-Path $supervisorLog) { Get-Content $supervisorLog -Raw } else { "NO SUPERVISOR LOG" }
Get-Process | Where-Object { $_.ProcessName -like "*webots*" -or $_.ProcessName -like "python*" } | Stop-Process -Force -ErrorAction SilentlyContinue
