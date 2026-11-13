@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "VALIDATE_MODE="
if /I "%~1"=="--validate" set "VALIDATE_MODE=-ValidateOnly"

set "WORLD=%~dp0worlds\stage2_random_obstacles.wbt"
set "JSON=%~dp0logs\worlds\stage2_random_obstacles.json"
set "RUNNER=%~dp0tools\run_avoid.ps1"

echo ============================================================
echo  Simulate Robot - random obstacle experiment
echo ============================================================
echo Project : %~dp0
echo World   : %WORLD%
if defined VALIDATE_MODE echo Mode    : static validation only
echo.

if not exist "%WORLD%" goto :missing_world
if not exist "%JSON%" goto :missing_json
if not exist "%RUNNER%" goto :missing_runner

if defined VALIDATE_MODE (
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%RUNNER%" -ValidateOnly -WorldFile "%WORLD%" -JsonFile "%JSON%" -Seed "fixed_seed7" -Timeout 24
) else (
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%RUNNER%" -Gui -WorldFile "%WORLD%" -JsonFile "%JSON%" -Seed "fixed_seed7" -Timeout 24
)
set "RC=%ERRORLEVEL%"
echo.
if not "%RC%"=="0" goto :launcher_failed

if defined VALIDATE_MODE goto :success_validate
echo [DONE] Webots is closed. Check the result lines above and the log files.
echo.
echo Archived logs:
echo   %~dp0logs\random_avoid\
goto :end

:success_validate
echo [OK] Static validation passed. No simulation was started.
goto :end

:launcher_failed
echo [ERROR] The launcher exited with code %RC%.
echo Copy this entire window and send it to ChatGPT.

:end
echo.
if defined VALIDATE_MODE exit /b %RC%
pause
exit /b %RC%

:missing_world
echo [ERROR] World file not found:
echo         %WORLD%
set "RC=1"
goto :end

:missing_json
echo [ERROR] Sidecar JSON not found:
echo         %JSON%
set "RC=1"
goto :end

:missing_runner
echo [ERROR] Runner script not found:
echo         %RUNNER%
set "RC=1"
goto :end
