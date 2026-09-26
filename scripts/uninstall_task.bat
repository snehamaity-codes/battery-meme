@echo off
setlocal
echo ==========================================================
echo   Uninstalling Battery Meme Alert Task from Task Scheduler
echo ==========================================================
echo.

schtasks /delete /tn "BatteryMemeAlert" /f

if %ERRORLEVEL% equ 0 (
    echo.
    echo [SUCCESS] Task "BatteryMemeAlert" was removed from Task Scheduler.
) else (
    echo.
    echo [INFO] Task "BatteryMemeAlert" was not found or already removed.
)

echo.
pause
endlocal
