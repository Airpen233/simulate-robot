param(
    [double[]]$Bearings = @(-90, -45, 0, 45, 90),
    [double[]]$Distances = @(0.03, 0.04, 0.05, 0.06, 0.08, 0.10, 0.13, 0.16, 0.20, 0.25, 0.30, 0.40),
    [double]$WaitSeconds = 14,
    [string]$Runner = ""
)

# Sensor calibration campaign: one static world per (bearing, distance).
#
# Each world has both the robot pose and the obstacle pose written literally into
# the file, so nothing moves and nothing needs synchronising. That is the whole
# point — the earlier Supervisor-driven sweep failed five different ways.
#
# Results land in controllers/calibration_controller/calibration_controller.log,
# which is cleared before every run so a stale file can never be mistaken for a
# fresh one.

$ErrorActionPreference = "Continue"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$runnerScript = Join-Path $root "tools\run_avoid.ps1"
$logPath = Join-Path $root "controllers\calibration_controller\calibration_controller.log"
$genscript = Join-Path $root "tools\generate_calibration.py"
$python = "python"

if (-not $Runner) { $Runner = $env:RUNNER_NAME }
if (-not $Runner) { $Runner = "airpen" }

$total = 0
$collected = 0

foreach ($bearing in $Bearings) {
    foreach ($distance in $Distances) {
        $total++
        $sign = if ($bearing -ge 0) { "p" } else { "m" }
        $name = "calib_b{0}{1:000}_d{2:000}" -f $sign, [math]::Abs($bearing), [math]::Round($distance * 1000)

        & $python $genscript --bearing $bearing --dist $distance | Out-Null
        Remove-Item -LiteralPath $logPath -ErrorAction SilentlyContinue

        Write-Host ("=== [{0}] {1} ===" -f $total, $name) -ForegroundColor Cyan
        & $runnerScript -WorldFile "$name.wbt" -RunName $name -Seed "calib" `
            -Runner $Runner -Timeout 12 -WaitSeconds $WaitSeconds | Out-Null

        if (Test-Path -LiteralPath $logPath) {
            $collected++
            $strongest = Select-String -LiteralPath $logPath -Pattern "READING" |
                ForEach-Object {
                    if ($_.Line -match "sensor=(\w+).*value=([\d.]+)") {
                        [pscustomobject]@{ Sensor = $matches[1]; Value = [double]$matches[2] }
                    }
                } | Sort-Object Value -Descending | Select-Object -First 1
            if ($strongest) {
                "    strongest={0} value={1:N1}" -f $strongest.Sensor, $strongest.Value
            }
        } else {
            Write-Host "    NO LOG" -ForegroundColor Yellow
        }
    }
}

"CALIBRATION_DONE total=$total collected=$collected"
