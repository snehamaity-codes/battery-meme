@echo off
setlocal
echo Stopping Battery Meme Alert background processes...
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*battery_meme_alert.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force; Write-Host ('Stopped process PID: ' + $_.ProcessId) }"
echo [OK] Done.
ping 127.0.0.1 -n 3 >nul 2>&1
endlocal
