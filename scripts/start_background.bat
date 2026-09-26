@echo off
setlocal
cd /d "%~dp0.."
echo Starting Battery Meme Alert in the background...
start "" pythonw "%~dp0..\src\battery_meme_alert.py"
echo [OK] Started! Running silently with pythonw.exe (no console window).
echo Logs are saved to battery_meme_alert.log
ping 127.0.0.1 -n 3 >nul 2>&1
endlocal
