# Install Battery Meme Alert to Windows Task Scheduler
# Features: Wake-from-sleep auto-start, AC/Battery power conditions unchecked, and duplicate instance prevention
$ErrorActionPreference = "Stop"

# Self-elevation check
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "[INFO] Requesting Administrator privileges to configure Task Scheduler..." -ForegroundColor Cyan
    try {
        $process = Start-Process powershell.exe -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs -PassThru
        $process.WaitForExit()
        exit $process.ExitCode
    } catch {
        Write-Host "[WARNING] Elevation was cancelled or unavailable: $($_.Exception.Message)" -ForegroundColor Yellow
        Write-Host "Please right-click 'scripts\install_task.bat' and choose 'Run as administrator'." -ForegroundColor Yellow
    }
}

$projectDir = (Get-Item "$PSScriptRoot\..").FullName
$scriptPath = Join-Path $projectDir "src\battery_meme_alert.py"
$xmlPath = Join-Path $projectDir "scripts\BatteryMemeAlert.xml"

# Find pythonw.exe
$pythonw = (Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source
if (-not $pythonw) {
    $candidates = @(
        "$env:LOCALAPPDATA\Programs\Python\Python311\pythonw.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python312\pythonw.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python310\pythonw.exe",
        "C:\Python311\pythonw.exe",
        "C:\Python312\pythonw.exe"
    )
    foreach ($c in $candidates) {
        if (Test-Path $c) {
            $pythonw = $c
            break
        }
    }
}

if (-not $pythonw -or -not (Test-Path $pythonw)) {
    Write-Error "pythonw.exe could not be found. Please ensure Python is installed and added to PATH."
    exit 1
}

Write-Host "=========================================================="
Write-Host "  Registering Task 'BatteryMemeAlert' in Task Scheduler"
Write-Host "=========================================================="
Write-Host "Pythonw:     $pythonw"
Write-Host "Script:      $scriptPath"
Write-Host "Working Dir: $projectDir"
Write-Host "XML Config:  $xmlPath"
Write-Host ""

$currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name

# Generate XML definition with exact user settings
$taskXml = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.3" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Battery Meme Alert - Continuous Background Battery Monitor with Sleep/Wake Auto-Resume</Description>
    <URI>\BatteryMemeAlert</URI>
  </RegistrationInfo>
  <Triggers>
    <!-- Trigger 1: Run at User Log On -->
    <LogonTrigger>
      <Enabled>true</Enabled>
    </LogonTrigger>
    <!-- Trigger 2: Wake from Sleep (System -> Microsoft-Windows-Power-Troubleshooter -> Event ID 1) -->
    <EventTrigger>
      <Enabled>true</Enabled>
      <Subscription>&lt;QueryList&gt;&lt;Query Id="0" Path="System"&gt;&lt;Select Path="System"&gt;*[System[Provider[@Name='Microsoft-Windows-Power-Troubleshooter'] and EventID=1]]&lt;/Select&gt;&lt;/Query&gt;&lt;/QueryList&gt;</Subscription>
    </EventTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <UserId>$currentUser</UserId>
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <!-- If task is already running, do not start a new instance -->
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <!-- Uncheck 'Start the task only if the computer is on AC power' -->
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <!-- Uncheck 'Stop if the computer switches to battery power' -->
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <Priority>7</Priority>
    <RestartOnFailure>
      <Interval>PT1M</Interval>
      <Count>3</Count>
    </RestartOnFailure>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>$pythonw</Command>
      <Arguments>`"$scriptPath`"</Arguments>
      <WorkingDirectory>$projectDir</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
"@

# Save task XML with Unicode encoding matching header
[System.IO.File]::WriteAllText($xmlPath, $taskXml, [System.Text.Encoding]::Unicode)

# Register via schtasks using the XML file
$regSuccess = $false
try {
    $p = Start-Process -FilePath "schtasks.exe" -ArgumentList "/create /tn `"BatteryMemeAlert`" /xml `"$xmlPath`" /f" -Wait -NoNewWindow -PassThru
    if ($p.ExitCode -eq 0) {
        $regSuccess = $true
    }
} catch {
    $regSuccess = $false
}

if (-not $regSuccess) {
    # Fallback to COM Schedule.Service user registration
    try {
        $service = New-Object -ComObject Schedule.Service
        $service.Connect()
        $root = $service.GetFolder("\")
        $def = $service.NewTask(0)
        $def.RegistrationInfo.Description = "Battery Meme Alert - Continuous Background Battery Monitor with Sleep/Wake Auto-Resume"

        # Settings
        $def.Settings.DisallowStartIfOnBatteries = $false
        $def.Settings.StopIfGoingOnBatteries = $false
        $def.Settings.MultipleInstances = 2 # TASK_INSTANCES_IGNORE_NEW
        $def.Settings.ExecutionTimeLimit = "PT0S"
        $def.Settings.AllowHardTerminate = $true
        $def.Settings.StartWhenAvailable = $true

        # Action
        $action = $def.Actions.Create(0)
        $action.Path = $pythonw
        $action.Arguments = "`"$scriptPath`""
        $action.WorkingDirectory = $projectDir

        # EventTrigger: Wake from Sleep
        $trigEvent = $def.Triggers.Create(0)
        $trigEvent.Subscription = "<QueryList><Query Id='0' Path='System'><Select Path='System'>*[System[Provider[@Name='Microsoft-Windows-Power-Troubleshooter'] and EventID=1]]</Select></Query></QueryList>"
        $trigEvent.Enabled = $true

        # RegistrationTrigger: Starts upon registration
        $trigReg = $def.Triggers.Create(7)
        $trigReg.Enabled = $true

        $task = $root.RegisterTaskDefinition("BatteryMemeAlert", $def, 6, $null, $null, 3)
        $regSuccess = $true
    } catch {
        $regSuccess = $false
    }
}

if ($regSuccess) {
    Write-Host "[SUCCESS] Task 'BatteryMemeAlert' registered successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Configured Conditions:"
    Write-Host "  [UNCHECKED] 'Start the task only if the computer is on AC power'"
    Write-Host "  [UNCHECKED] 'Stop if the computer switches to battery power'"
    Write-Host ""
    Write-Host "Configured Triggers:"
    Write-Host "  [ENABLED] Wake from Sleep (System Log -> Power-Troubleshooter -> Event ID 1)"
    Write-Host ""
    Write-Host "Configured Settings:"
    Write-Host "  [ENABLED] 'If the task is already running: Do not start a new instance' (IgnoreNew)"
    Write-Host ""
    # Start task now
    Start-Process -FilePath "schtasks.exe" -ArgumentList "/run /tn `"BatteryMemeAlert`"" -Wait -NoNewWindow -ErrorAction SilentlyContinue
    Write-Host "[OK] Task started in background." -ForegroundColor Cyan
} else {
    Write-Host "[WARNING] Could not register task directly in this session." -ForegroundColor Yellow
    Write-Host "To register with full permissions, right-click 'scripts\install_task.bat' and select 'Run as administrator'." -ForegroundColor Yellow
    Write-Host "Or in Task Scheduler GUI (taskschd.msc), click 'Import Task...' and choose 'scripts\BatteryMemeAlert.xml'." -ForegroundColor Yellow
}
