param(
    [Parameter(Mandatory = $true)][string]$WorldFile,
    [string]$JsonFile = "",
    [string]$RunName = "",
    [string]$Seed = "fixed",
    [double]$TargetX = 1.0,
    [double]$TargetY = 0.0,
    [double]$Timeout = 24.0,
    [int]$WaitSeconds = 32,
    [string]$WebotsExe = "",
    [string]$Runner = "",
    [switch]$Gui,
    [switch]$ValidateOnly
)

$ErrorActionPreference = "Continue"

# Who is running this experiment. Archive logs go to logs/random_avoid/<Runner>/
# so two people never overwrite each other's evidence. Resolution order:
#   1. -Runner passed explicitly
#   2. $env:RUNNER_NAME
#   3. "airpen" (the repo owner)
if (-not $Runner) { $Runner = $env:RUNNER_NAME }
if (-not $Runner) { $Runner = "airpen" }
# Keep the value path-safe: it becomes a directory name.
if ($Runner -notmatch '^[A-Za-z0-9._-]+$') {
    throw "Runner name '$Runner' is not allowed. Use letters, digits, dot, underscore or hyphen."
}
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

# Webots executable. Resolved in this order so the repo works on any machine:
#   1. -WebotsExe passed explicitly
#   2. $env:WEBOTS_HOME (set by the Webots installer)
#   3. the usual Windows install location
#   4. webots on PATH
# A teammate cloning this repo should not have to edit a hardcoded path.
function Resolve-WebotsExe {
    param([string]$Explicit)
    if ($Explicit -and (Test-Path -LiteralPath $Explicit -PathType Leaf)) { return (Resolve-Path -LiteralPath $Explicit).Path }
    if ($env:WEBOTS_HOME) {
        foreach ($rel in @("msys64\mingw64\bin\webots.exe", "webots.exe")) {
            $candidate = Join-Path $env:WEBOTS_HOME $rel
            if (Test-Path -LiteralPath $candidate -PathType Leaf) { return (Resolve-Path -LiteralPath $candidate).Path }
        }
    }
    foreach ($candidate in @("C:\Program Files\Webots\msys64\mingw64\bin\webots.exe")) {
        if (Test-Path -LiteralPath $candidate -PathType Leaf) { return $candidate }
    }
    $onPath = Get-Command webots -ErrorAction SilentlyContinue
    if ($onPath) { return $onPath.Source }
    throw "Webots not found. Pass -WebotsExe, set WEBOTS_HOME, or install Webots to the default location."
}

$exe = Resolve-WebotsExe -Explicit $WebotsExe
$world = if ([System.IO.Path]::IsPathRooted($WorldFile)) { $WorldFile } else { Join-Path $root ("worlds\" + $WorldFile) }
if (-not (Test-Path -LiteralPath $world -PathType Leaf)) { throw "world not found: $world" }
$world = (Resolve-Path -LiteralPath $world).Path

if (-not $JsonFile) {
    $candidate = Join-Path $root ("logs\worlds\" + [System.IO.Path]::GetFileNameWithoutExtension($world) + ".json")
    if (Test-Path -LiteralPath $candidate -PathType Leaf) { $JsonFile = $candidate }
} elseif (-not [System.IO.Path]::IsPathRooted($JsonFile)) {
    $JsonFile = Join-Path $root $JsonFile
}
if ($JsonFile) {
    if (-not (Test-Path -LiteralPath $JsonFile -PathType Leaf)) { throw "sidecar JSON not found: $JsonFile" }
    $JsonFile = (Resolve-Path -LiteralPath $JsonFile).Path
}

# A unique default name keeps archived runs from overwriting earlier samples.
if (-not $RunName) {
    $prefix = if ($Gui) { "beginner_" } else { "" }
    $RunName = $prefix + [System.IO.Path]::GetFileNameWithoutExtension($world) + "_" + (Get-Date -Format "yyyyMMdd_HHmmss")
}

$headlessArgLine = '--mode=realtime --batch --no-rendering --stdout --stderr "' + $world + '"'
$guiArgLine = '--mode=pause --stdout --stderr "' + $world + '"'

$controllerDir = Join-Path $root "controllers\avoid_controller"
$supervisorDir = Join-Path $root "controllers\avoid_supervisor"
$logicDir = Join-Path $root "controllers\robot_controller\logic"
$controllerRuntime = Join-Path $controllerDir "runtime.ini"
$supervisorRuntime = Join-Path $supervisorDir "runtime.ini"

# Static dependency checks. They run before any log file is touched, so
# -ValidateOnly is a safe dry run that never starts a simulation.
$required = @(
    @{ Name = "webots"; Path = $exe },
    @{ Name = "controller"; Path = (Join-Path $controllerDir "avoid_controller.py") },
    @{ Name = "controller_runtime"; Path = $controllerRuntime },
    @{ Name = "supervisor"; Path = (Join-Path $supervisorDir "avoid_supervisor.py") },
    @{ Name = "supervisor_runtime"; Path = $supervisorRuntime },
    @{ Name = "logic_avoidance"; Path = (Join-Path $logicDir "avoidance.py") },
    @{ Name = "logic_kinematics"; Path = (Join-Path $logicDir "kinematics.py") }
)

$missing = @()
foreach ($item in $required) {
    if (Test-Path -LiteralPath $item.Path -PathType Leaf) {
        "VALIDATE $($item.Name)=OK $($item.Path)"
    } else {
        "VALIDATE $($item.Name)=MISSING $($item.Path)"
        $missing += ("missing " + $item.Name + ": " + $item.Path)
    }
}

foreach ($runtime in @($controllerRuntime, $supervisorRuntime)) {
    if (-not (Test-Path -LiteralPath $runtime -PathType Leaf)) { continue }
    $match = Select-String -LiteralPath $runtime -Pattern '^\s*COMMAND\s*=\s*(.+?)\s*$' | Select-Object -First 1
    if (-not $match) {
        "VALIDATE python=UNKNOWN $runtime"
        $missing += ("missing COMMAND in " + $runtime)
        continue
    }
    $python = $match.Matches[0].Groups[1].Value.Trim()
    if (Test-Path -LiteralPath $python -PathType Leaf) {
        "VALIDATE python=OK $python"
    } else {
        "VALIDATE python=MISSING $python"
        $missing += ("missing python: " + $python)
    }
}

if ($JsonFile) {
    try {
        $scene = Get-Content -LiteralPath $JsonFile -Raw -Encoding UTF8 | ConvertFrom-Json
        $obstacleCount = @($scene.obstacles).Count
        "VALIDATE json=OK seed=$($scene.seed) obstacles=$obstacleCount"
    } catch {
        "VALIDATE json=INVALID $JsonFile"
        $missing += ("invalid sidecar JSON: " + $JsonFile + " (" + $_.Exception.Message + ")")
    }
} else {
    "VALIDATE json=MISSING (the controller will log SCENE_JSON_MISSING)"
}

$worldText = Get-Content -LiteralPath $world -Raw
foreach ($controllerName in @("avoid_controller", "avoid_supervisor")) {
    if ($worldText -match ('controller\s+"' + [regex]::Escape($controllerName) + '"')) {
        "VALIDATE world_controller_$controllerName=OK"
    } else {
        "VALIDATE world_controller_$controllerName=MISSING"
        $missing += ("world does not reference " + $controllerName)
    }
}

"VALIDATE_ARG_HEADLESS=$headlessArgLine"
"VALIDATE_ARG_GUI=$guiArgLine"

if ($missing.Count -gt 0) {
    throw ("missing dependencies: " + ($missing -join "; "))
}

if ($ValidateOnly) {
    "VALIDATE_OK"
    return
}

if ($Gui) {
    $running = @(Get-Process -Name "webots", "webots-bin" -ErrorAction SilentlyContinue)
    if ($running.Count -gt 0) {
        $names = ($running | ForEach-Object { $_.ProcessName } | Sort-Object -Unique) -join ", "
        throw ("Webots is already running (" + $names + "). Close the existing Webots window before starting this experiment.")
    }
}

$outDir = Join-Path $root (Join-Path "logs\random_avoid" $Runner)
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$controllerLog = Join-Path $root "logs\avoid_controller.log"
$supervisorLog = Join-Path $root "logs\avoid_supervisor.log"
Remove-Item -LiteralPath $controllerLog, $supervisorLog -ErrorAction SilentlyContinue

if (-not $Gui) {
    # Only stop Webots processes, never unrelated Python processes.
    Get-Process | Where-Object { $_.ProcessName -like "webots*" } | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 300
}

$env:SIMULATE_TARGET_X = "$TargetX"
$env:SIMULATE_TARGET_Y = "$TargetY"
$env:SIMULATE_TIMEOUT = "$Timeout"
$env:SIMULATE_SCENE = $world
$env:SIMULATE_SEED = "$Seed"
$env:SIMULATE_SCENE_JSON = "$JsonFile"

"RUN $RunName world=$world seed=$Seed json=$JsonFile timeout=$Timeout gui=$Gui"
if ($Gui) {
    "GUI: Webots starts paused. Click Run in Webots to start the robot."
    "GUI: Close the Webots window when done; this console will then print the results."
}

$startedAt = Get-Date
$argLine = if ($Gui) { $guiArgLine } else { $headlessArgLine }
$process = Start-Process -FilePath $exe -ArgumentList $argLine -WorkingDirectory $root -PassThru -ErrorAction Stop

if ($Gui) {
    # Wait for the launcher and the actual Webots process. Closing Webots,
    # or the supervisor's simulationQuit(0), ends this wait.
    Wait-Process -Id $process.Id -ErrorAction SilentlyContinue
    while (@(Get-Process -Name "webots", "webots-bin" -ErrorAction SilentlyContinue).Count -gt 0) {
        Start-Sleep -Seconds 1
    }
    $stillRunning = $false
} else {
    $deadline = (Get-Date).AddSeconds($WaitSeconds)
    while ((Get-Date) -lt $deadline) {
        if (-not (Get-Process -Id $process.Id -ErrorAction SilentlyContinue)) { break }
        Start-Sleep -Seconds 1
    }
    $stillRunning = [bool](Get-Process -Id $process.Id -ErrorAction SilentlyContinue)
    if ($stillRunning) {
        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
    }
}
Start-Sleep -Milliseconds 500

$elapsed = ((Get-Date) - $startedAt).TotalSeconds
$webotsExit = $null
try {
    $process.Refresh()
    if ($process.HasExited) { $webotsExit = $process.ExitCode }
} catch {
}

"STILL_RUNNING=$stillRunning"
"WEBOTS_EXIT_CODE=$webotsExit"
"ELAPSED_SECONDS=$([math]::Round($elapsed, 1))"

$controllerOut = Join-Path $outDir ($RunName + "_controller.log")
$supervisorOut = Join-Path $outDir ($RunName + "_supervisor.log")
if (Test-Path -LiteralPath $controllerLog) {
    Copy-Item -LiteralPath $controllerLog -Destination $controllerOut -Force
    "CONTROLLER_LOG=$controllerOut"
} else {
    "NO CONTROLLER LOG"
}
if (Test-Path -LiteralPath $supervisorLog) {
    Copy-Item -LiteralPath $supervisorLog -Destination $supervisorOut -Force
    "SUPERVISOR_LOG=$supervisorOut"
} else {
    "NO SUPERVISOR LOG"
}
if ($JsonFile -and (Test-Path -LiteralPath $JsonFile)) {
    Copy-Item -LiteralPath $JsonFile -Destination (Join-Path $outDir ($RunName + "_world.json")) -Force
}

$controllerResult = if (Test-Path -LiteralPath $controllerOut) { (Select-String -LiteralPath $controllerOut -Pattern "RESULT:" | Select-Object -Last 1).Line } else { $null }
$supervisorResult = if (Test-Path -LiteralPath $supervisorOut) { (Select-String -LiteralPath $supervisorOut -Pattern "RESULT: true_end" | Select-Object -Last 1).Line } else { $null }
"CONTROLLER_RESULT=" + $controllerResult
"SUPERVISOR_RESULT=" + $supervisorResult

if ($Gui -and -not (Test-Path -LiteralPath $controllerLog) -and -not (Test-Path -LiteralPath $supervisorLog)) {
    if ($elapsed -lt 3.0) {
        "LAUNCH_PROBLEM: Webots exited after $([math]::Round($elapsed, 1)) s without producing controller logs."
        exit 1
    }
    "NO_LOGS: Webots was closed before the simulation ran. Next time click Run in Webots."
}
