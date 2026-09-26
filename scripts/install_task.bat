@echo off
setlocal
cd /d "%~dp0.."
set "PROJECT_DIR=%CD%"

echo ========================================================
echo   Installing Battery Meme Alert to Windows Task Scheduler
echo ========================================================
echo.

set PYTHONW_PATH=
for /f "delims=" %%I in ('where pythonw.exe 2^>nul') do (
    set "PYTHONW_PATH=%%I"
    goto :found
)

:found
if not defined PYTHONW_PATH (
    echo [ERROR] pythonw.exe could not be found in your PATH.
    echo Please make sure Python is installed and added to PATH.
    pause
    exit /b 1
)

echo Detected pythonw at: %PYTHONW_PATH%
echo Script path:        %PROJECT_DIR%\src\battery_meme_alert.py
echo Working directory:  %PROJECT_DIR%
echo.

schtasks /create /tn "BatteryMemeAlert" /tr "\"%PYTHONW_PATH%\" \"%PROJECT_DIR%\src\battery_meme_alert.py\"" /sc onlogon /f

if %ERRORLEVEL% equ 0 (
    echo.
    echo [SUCCESS] Task "BatteryMemeAlert" registered successfully to launch at login!
) else (
    echo.
    echo [FAILED] Could not register task. Please try running this script as Administrator.
)

echo.
pause
endlocal
