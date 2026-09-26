# Install Battery Meme Alert to Windows Task Scheduler with Battery Power enabled
$ErrorActionPreference = "Stop"

$projectDir = (Get-Item "$PSScriptRoot\..").FullName
$scriptPath = Join-Path $projectDir "src\battery_meme_alert.py"

# Find pythonw.exe
$pythonw = (Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source
if (-not $pythonw) {
    $pythonw = "C:\Users\WORK_SNEHA\AppData\Local\Programs\Python\Python311\pythonw.exe"
}

if (-not (Test-Path $pythonw)) {
    Write-Error "pythonw.exe could not be found."
    exit 1
}

Write-Host "Registering Task 'BatteryMemeAlert'..."
Write-Host "Pythonw:    $pythonw"
Write-Host "Script:     $scriptPath"
Write-Host "WorkingDir: $projectDir"

$action = New-ScheduledTaskAction -Execute $pythonw -Argument "`"$scriptPath`"" -WorkingDirectory $projectDir
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Days 0)

Register-ScheduledTask -TaskName "BatteryMemeAlert" -Action $action -Trigger $trigger -Settings $settings -Force

Write-Host "`n[SUCCESS] Task 'BatteryMemeAlert' registered to launch at logon (runs on both AC and Battery)!"
