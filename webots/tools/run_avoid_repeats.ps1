param(
    [ValidateSet("fixed", "random", "all")]
    [string]$Mode = "all",
    [int]$SeedStart = 1,
    [int]$SeedEnd = 10,
    [int]$RepeatStart = 2,
    [int]$RepeatEnd = 3,
    [double]$Timeout = 24.0,
    [int]$WaitSeconds = 34
)

# Repeat-experiment runner for prereg R1.
#
# Unlike run_avoid_suite.ps1, this NEVER overwrites the original run names.
# Each repetition gets its own RunName suffix (e.g. fixed_front_r2), so the
# archived first-run logs stay untouched and every trial stays addressable.
#
# Usage:
#   .\tools\run_avoid_repeats.ps1 -Mode all -RepeatStart 2 -RepeatEnd 3

$ErrorActionPreference = "Continue"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$python = "C:\Users\Airpen\AppData\Local\Programs\Python\Python312\python.exe"
$generator = Join-Path $root "tools\generate_random_world.py"
$runner = Join-Path $root "tools\run_avoid.ps1"

$fixed = @(
    @{ Name = "clear"; World = "stage2_scenario_clear.wbt"; Json = "logs\worlds\stage2_scenario_clear.json" },
    @{ Name = "front"; World = "stage2_scenario_front.wbt"; Json = "logs\worlds\stage2_scenario_front.json" },
    @{ Name = "left_blocked"; World = "stage2_scenario_left_blocked.wbt"; Json = "logs\worlds\stage2_scenario_left_blocked.json" },
    @{ Name = "right_blocked"; World = "stage2_scenario_right_blocked.wbt"; Json = "logs\worlds\stage2_scenario_right_blocked.json" },
    @{ Name = "both_blocked"; World = "stage2_scenario_both_blocked.wbt"; Json = "logs\worlds\stage2_scenario_both_blocked.json" },
    @{ Name = "no_path"; World = "stage2_scenario_no_path.wbt"; Json = "logs\worlds\stage2_scenario_no_path.json" },
    @{ Name = "fixed_seed7"; World = "stage2_random_obstacles.wbt"; Json = "logs\worlds\stage2_random_obstacles.json" }
)

$total = 0
$failed = 0

if ($Mode -in @("fixed", "all")) {
    & $python $generator --scenario scenarios | Out-Null
    & $python $generator --scenario fixed --seed 7 | Out-Null
    foreach ($item in $fixed) {
        foreach ($r in $RepeatStart..$RepeatEnd) {
            $total++
            $runName = "{0}_r{1}" -f $item.Name, $r
            Write-Host ("=== [{0}/{1}] {2} ===" -f $total, "?", $runName) -ForegroundColor Cyan
            & $runner -WorldFile $item.World -JsonFile (Join-Path $root $item.Json) `
                -RunName $runName -Seed $item.Name -Timeout $Timeout -WaitSeconds $WaitSeconds
            if ($LASTEXITCODE -ne 0) { $failed++ }
        }
    }
}

if ($Mode -in @("random", "all")) {
    for ($seed = $SeedStart; $seed -le $SeedEnd; $seed++) {
        & $python $generator --scenario random --seed $seed | Out-Null
        $world = "stage2_random_seed_$seed.wbt"
        $json = Join-Path $root ("logs\worlds\stage2_random_seed_$seed.json")
        foreach ($r in $RepeatStart..$RepeatEnd) {
            $total++
            $runName = "random_seed_${seed}_r$r"
            Write-Host ("=== [{0}] {1} ===" -f $total, $runName) -ForegroundColor Cyan
            & $runner -WorldFile $world -JsonFile $json `
                -RunName $runName -Seed "$seed" -Timeout $Timeout -WaitSeconds $WaitSeconds
            if ($LASTEXITCODE -ne 0) { $failed++ }
        }
    }
}

"REPEATS_DONE total=$total failed=$failed repeats=$RepeatStart..$RepeatEnd"
