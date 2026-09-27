# Battery Meme Alert (Windows)

A lightweight Windows background application that monitors your laptop's battery percentage and charging state. When your battery crosses predefined milestone thresholds, it displays a borderless floating meme popup window and plays a matching audio clip simultaneously.

---

## Features & Trigger Rules

The app monitors 5 distinct tiers independently with built-in hysteresis and bracket detection:

| Tier | Trigger Condition | Reset Condition (Ready to trigger again) |
| :--- | :--- | :--- |
| **`100`** | Battery reaches **100%** AND laptop is **plugged in / charging**. | Battery drops to **<= 97%** OR laptop is **unplugged**. |
| **`50`** | Laptop is **discharging** (unplugged) AND drops to or through **50%**. | Laptop reconnected to AC and reaches > 50%, OR rises to **>= 53%**. |
| **`30`** | Laptop is **discharging** (unplugged) AND drops to or through **30%**. | Laptop reconnected to AC and reaches > 30%, OR rises to **>= 33%**. |
| **`10`** | Laptop is **discharging** (unplugged) AND drops to or through **10%**. | Laptop reconnected to AC and reaches > 10%, OR rises to **>= 13%**. |
| **`5`**  | Laptop is **discharging** (unplugged) AND drops to or through **5%**. | Laptop reconnected to AC and reaches > 5%, OR rises to **>= 8%**. |

* **Hysteresis Buffer (+3%)**: Prevents rapid double-firing caused by normal battery sensor jitter (e.g., oscillating 49% -> 50% -> 49%). Discharging tiers require recharging or at least a +3% jump above threshold to reset. The 100% tier requires dropping to 97% or unplugging before resetting.
* **Smart Bracket Detection (Rapid Drain & Unplugging)**: If battery drain skips across multiple thresholds between checks (e.g., 55% to 25%), the app marks passed tiers (50%) as fired and fires the current bracket (30%). Unplugging the charger when already sitting at a low battery level instantly fires the current bracket without waiting for further drain.
* **No-Repeat Asset Rotation**: Consecutive triggers within the same tier avoid replaying the same meme image or sound clip if alternatives are available in the folder.
* **Zero File Locking**: Asset files are loaded into memory and closed immediately, allowing you to edit, replace, or delete meme files without stopping the background process.
* **Perfect Audio-Visual Sync**: Image textures and audio streams are fully preloaded into memory before displaying the popup window, ensuring zero desync between visuals and sound.
* **Auto-Closing Dark Notification UI**: Borderless floating dark-mode card with a synchronized 10-second countdown timer, dismissible on click or via `Esc`.
* **Desktop & Driver Fallback**: Gracefully detects if your device has no battery sensor (e.g., desktop PC) and sleeps quietly without unhandled exceptions.

---

## Project Structure

```text
battery/
├── src/
│   ├── __init__.py
│   └── battery_meme_alert.py   # Core monitoring & GUI popup logic
├── scripts/
│   ├── start_background.bat    # 1-click background launcher (silent)
│   ├── stop_background.bat     # 1-click background process stopper
│   ├── install_task.bat        # Automated Windows Task Scheduler installer
│   ├── install_task.ps1        # PowerShell script for COM task registration
│   ├── uninstall_task.bat      # Task Scheduler remover
│   └── BatteryMemeAlert.xml    # XML task definition template with wake/logon triggers
├── meme/                       # Meme assets organized by tier
│   ├── 100/                    # Images & sound clips for 100% plugged
│   ├── 50/                     # Images & sound clips for 50% discharging
│   ├── 30/                     # Images & sound clips for 30% discharging
│   ├── 10/                     # Images & sound clips for 10% discharging
│   └── 5/                      # Images & sound clips for 5% discharging
├── main.py                     # Convenient root launcher
├── requirements.txt            # Python dependencies
├── .gitignore                  # Git exclusions for logs and cache
└── README.md                   # Documentation & setup instructions
```

---

## Prerequisites

* **Operating System**: Windows 10 or Windows 11
* **Python**: Python 3.8+ (Make sure `Add Python to PATH` was selected during Python installation)

---

## Installation

1. **Clone or download this repository**:
   ```bash
   git clone https://github.com/snehamaity-codes/battery-meme.git
   cd battery-meme
   ```

2. **Install required dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   *(Required packages: `psutil`, `pygame`, `pillow`)*

---

## How to Test (Verify Audio & Popup)

You do **not** need to wait for your laptop battery to drain to test if the application works!

Run manual test commands from the project root:

```bash
# Test 100% full charge tier
python main.py --test 100

# Test 50% tier
python main.py --test 50

# Test 30% tier
python main.py --test 30

# Test 10% tier
python main.py --test 10

# Test 5% tier
python main.py --test 5
```

**What to expect during test:**
1. A small borderless dark-themed card will appear in the bottom-right corner of your screen showing a randomly selected meme from that tier.
2. The matching audio clip will play simultaneously with zero delay.
3. The popup will automatically dismiss after 10 seconds (with a synchronized countdown label), or immediately if you click on it or press `Esc`.

---

## How to Run in the Background

### Starting the Application
To run silently without keeping a Command Prompt window open:
* **Option A**: Double-click `scripts\start_background.bat`
* **Option B**: Run with `pythonw.exe`:
  ```bash
  pythonw src\battery_meme_alert.py
  ```

### Checking Application Logs
When running in background mode, logs are continuously written to:
```text
battery_meme_alert.log
```
Open this file at any time to verify monitoring cycles and tier triggers.

### Stopping the Application
To stop the background process:
* Double-click `scripts\stop_background.bat`
* Or terminate via PowerShell:
  ```powershell
  Get-Process pythonw | Where-Object { $_.CommandLine -like "*battery_meme_alert*" } | Stop-Process
  ```

### Automatic Startup via Task Scheduler
For hands-off background operation that automatically starts on login and resumes whenever your laptop wakes from sleep, see the [Automatic Startup & Wake-from-Sleep Auto-Resume](#automatic-startup--wake-from-sleep-auto-resume-windows-task-scheduler) section below.

---

## Resource & Memory Usage (RAM)

Battery Meme Alert is lightweight and virtually imperceptible to your system's performance:

| Metric | Measurement | Impact & Context |
| :--- | :--- | :--- |
| **Physical RAM (Working Set)** | **~40 – 43 MB** | Extremely small (~0.26% on a 16 GB laptop). |
| **CPU Usage** | **0.0%** | The process sleeps 99.9% of the time. It queries the Windows battery sensor in < 1 ms, then returns to a deep sleep state. |
| **Battery Drain Impact** | **Virtually Zero** | Consumes less than 0.01 seconds of total CPU execution time per minute. |

### Memory Comparison with Everyday Software
To put **~42 MB** in perspective against other everyday applications:
* **Single blank tab (Chrome / Edge)**: ~150 – 300 MB *(~4x to 7x more RAM)*
* **Discord / Slack / Spotify**: ~250 – 500 MB *(~6x to 12x more RAM)*
* **Code Editor (VS Code / PyCharm)**: ~600 MB – 1.8 GB *(~15x to 40x more RAM)*
* **Windows Task Manager itself**: ~35 – 50 MB *(roughly identical)*
* **Battery Meme Alert**: **~42 MB**

---

## Automatic Startup & Wake-from-Sleep Auto-Resume (Windows Task Scheduler)

Configuring Windows Task Scheduler ensures the app automatically launches whenever your computer boots, user logs in, or the laptop wakes from sleep or hibernation—with zero manual intervention.

### Method 1: Automatic 1-Click Setup (Recommended)

1. Right-click **`scripts\install_task.bat`** and select **Run as administrator** (or execute `scripts\install_task.ps1` in an elevated PowerShell terminal).
2. The installation script automatically configures the `BatteryMemeAlert` task with:
   * **Dual Triggers**:
     * **At log on**: Starts the monitoring loop upon user session login.
     * **On wake from sleep**: Subscribes to `Microsoft-Windows-Power-Troubleshooter` (Event ID `1`) in the System event log to instantly revive the background process when waking from sleep or hibernation.
   * **Power Conditions**:
     * Unchecks *"Start the task only if the computer is on AC power"*.
     * Unchecks *"Stop if the computer switches to battery power"*.
     *(This ensures the app continues running when the laptop is unplugged).*
   * **Instance Policy**:
     * Configured to *"Do not start a new instance"* (`TASK_INSTANCES_IGNORE_NEW`) to prevent duplicate processes from accumulating.

To verify registration at any time:
```cmd
schtasks /query /tn "BatteryMemeAlert" /fo LIST /v
```

To remove the scheduled task:
```cmd
scripts\uninstall_task.bat
```

---

### Method 2: Import Task Template XML

An exportable task definition is included in `scripts\BatteryMemeAlert.xml`.

1. Open **Command Prompt** or **PowerShell** as administrator.
2. Run:
   ```cmd
   schtasks /create /tn "BatteryMemeAlert" /xml "scripts\BatteryMemeAlert.xml"
   ```
   *(Ensure the `<Command>` path inside the XML matches your `pythonw.exe` location and `<WorkingDirectory>` matches your repository path).*

---

### Method 3: Manual Setup via Windows Task Scheduler GUI

If you prefer to configure the task by hand:

1. Press `Win + R`, type **`taskschd.msc`**, and press `Enter`.
2. In the right-hand panel, click **Create Task...** (do not choose "Create Basic Task").
3. **General Tab**:
   * **Name**: `BatteryMemeAlert`
   * Select: **Run only when user is logged on**.
4. **Triggers Tab**:
   * **Trigger 1**: Click **New...** -> Select **At log on** -> Click **OK**.
   * **Trigger 2**: Click **New...** -> Select **On an event** -> Log: `System` -> Source: `Power-Troubleshooter` -> Event ID: `1` -> Click **OK**.
5. **Actions Tab**:
   * Click **New...** -> Action: **Start a program**.
   * **Program/script**: `pythonw.exe` (or full path to your Python installation's `pythonw.exe`).
   * **Add arguments**: `"src\battery_meme_alert.py"`
   * **Start in (mandatory)**: Full path to your project folder (e.g. `D:\HACKATHON\battery`).
   * Click **OK**.
6. **Conditions Tab (Critical Step)**:
   * **Uncheck** *"Start the task only if the computer is on AC power"*.
   * **Uncheck** *"Stop if the computer switches to battery power"*.
7. **Settings Tab**:
   * Check **Allow task to be run on demand**.
   * Under *"If the task is already running, then the following rule applies"*, select **Do not start a new instance**.
   * Click **OK** to save.

---

## Adding Your Own Memes & Audio

You can easily customize the memes and sounds:
1. Open the subfolder matching the tier you want to customize (`meme\100`, `meme\50`, `meme\30`, `meme\10`, `meme\5`).
2. Add your favorite images (`.png`, `.jpg`, `.jpeg`, `.webp`, `.gif`) or audio clips (`.mp3`, `.wav`, `.ogg`).
3. The app will automatically include them in the random rotation next time that tier triggers.

---

## Troubleshooting FAQ

* **No audio is playing**:
  Ensure your Windows system volume is not muted. If using headphones or Bluetooth audio devices, verify they are set as the default playback device.
* **Task Scheduler doesn't run when on battery**:
  Check step 6 under Task Scheduler setup. Ensure *"Start the task only if the computer is on AC power"* is unchecked.
* **Desktop PC shows no alerts**:
  Desktops without an uninterruptible battery sensor will log `No battery sensor detected` and safely sleep. You can still test visual alerts and audio using the `--test` command.
