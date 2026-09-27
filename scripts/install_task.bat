@echo off
setlocal
cd /d "%~dp0.."
set "PROJECT_DIR=%CD%"

echo ========================================================
echo   Installing Battery Meme Alert to Windows Task Scheduler
echo ========================================================
echo.

:: Check for Administrator privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [INFO] Requesting Administrator privileges to configure Task Scheduler...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process cmd.exe -ArgumentList '/c \"\"%~f0\"\"' -Verb RunAs"
    exit /b
)

:: Run the comprehensive PowerShell installation script
powershell -NoProfile -ExecutionPolicy Bypass -File "%PROJECT_DIR%\scripts\install_task.ps1"

echo.
pause
endlocal
