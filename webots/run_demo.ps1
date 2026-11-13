param(
    [ValidateSet("clear", "blocked")]
    [string]$Scenario = "clear"
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$exe = "C:\Program Files\Webots\msys64\mingw64\bin\webots.exe"
$world = Join-Path $root ("worlds\demo_" + $Scenario + ".wbt")

if (-not (Test-Path -LiteralPath $exe)) {
    throw "Webots executable not found: $exe"
}
if (-not (Test-Path -LiteralPath $world)) {
    throw "World not found: $world"
}

Write-Host "Starting Webots R2025a..."
Write-Host "World: $world"
Write-Host "Expected RESULT: reached (clear) or blocked (blocked)."
Write-Host "The session supervisor quits Webots automatically after 25 s."

& $exe --mode=realtime --batch --stdout --stderr $world
