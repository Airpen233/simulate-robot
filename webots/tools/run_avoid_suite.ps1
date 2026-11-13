param(
    [ValidateSet("fixed", "random", "all")]
    [string]$Mode = "all",
    [int]$SeedStart = 1,
    [int]$SeedEnd = 10,
    [double]$Timeout = 24.0
)

$ErrorActionPreference = "Continue"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$python = "C:\Users\Airpen\AppData\Local\Programs\Python\Python312\python.exe"
$generator = Join-Path $root "tools\generate_random_world.py"
$runner = Join-Path $root "tools\run_avoid.ps1"

if ($Mode -in @("fixed", "all")) {
    & $python $generator --scenario scenarios
    & $python $generator --scenario fixed --seed 7
    $fixed = @(
        @{ Name = "clear"; World = "stage2_scenario_clear.wbt"; Json = "logs\worlds\stage2_scenario_clear.json" },
        @{ Name = "front"; World = "stage2_scenario_front.wbt"; Json = "logs\worlds\stage2_scenario_front.json" },
        @{ Name = "left_blocked"; World = "stage2_scenario_left_blocked.wbt"; Json = "logs\worlds\stage2_scenario_left_blocked.json" },
        @{ Name = "right_blocked"; World = "stage2_scenario_right_blocked.wbt"; Json = "logs\worlds\stage2_scenario_right_blocked.json" },
        @{ Name = "both_blocked"; World = "stage2_scenario_both_blocked.wbt"; Json = "logs\worlds\stage2_scenario_both_blocked.json" },
        @{ Name = "no_path"; World = "stage2_scenario_no_path.wbt"; Json = "logs\worlds\stage2_scenario_no_path.json" },
        @{ Name = "fixed_seed7"; World = "stage2_random_obstacles.wbt"; Json = "logs\worlds\stage2_random_obstacles.json" }
    )
    foreach ($item in $fixed) {
        & $runner -WorldFile $item.World -JsonFile (Join-Path $root $item.Json) -RunName ("fixed_" + $item.Name) -Seed $item.Name -Timeout $Timeout
    }
}

if ($Mode -in @("random", "all")) {
    for ($seed = $SeedStart; $seed -le $SeedEnd; $seed++) {
        & $python $generator --scenario random --seed $seed
        $world = "stage2_random_seed_$seed.wbt"
        $json = Join-Path $root ("logs\worlds\stage2_random_seed_$seed.json")
        & $runner -WorldFile $world -JsonFile $json -RunName ("random_seed_$seed") -Seed "$seed" -Timeout $Timeout
    }
}

"SUITE_DONE mode=$Mode seeds=$SeedStart..$SeedEnd"
