# Battery Meme Alert (Windows)

A lightweight Windows background application that monitors your laptop's battery percentage and charging state. When your battery crosses predefined milestone thresholds, it displays a borderless floating meme popup window and plays a matching audio clip simultaneously.

---

## Features & Trigger Rules

The app monitors 5 distinct tiers independently:

| Tier | Trigger Condition | Reset Condition (Ready to trigger again) |
| :--- | :--- | :--- |
| **`100`** | Battery is at **100%** AND laptop is **plugged in / charging**. | Battery drops below 100% OR is unplugged. |
| **`50`** | Laptop is **discharging** (unplugged) AND drops to or through **50%**. | Battery recharges above 50%. |
| **`30`** | Laptop is **discharging** (unplugged) AND drops to or through **30%**. | Battery recharges above 30%. |
| **`10`** | Laptop is **discharging** (unplugged) AND drops to or through **10%**. | Battery recharges above 10%. |
| **`5`**  | Laptop is **discharging** (unplugged) AND drops to or through **5%**. | Battery recharges above 5%. |

* **Single-fire per crossing**: Each tier fires once per crossing. It will not repeat until the battery recharges above that tier's threshold.
* **Smart startup**: Prevents sudden notification spam if you boot your laptop with an already low battery.
* **Desktop fallback**: Gracefully detects if your device has no battery sensor (e.g. desktop PC) and sleeps quietly without errors.
* **Auto-closing UI**: The popup window auto-dismisses after 10 seconds, or immediately if you click anywhere on the card or press `Esc`.

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
│   └── uninstall_task.bat      # Task Scheduler remover
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
2. The matching audio clip will play simultaneously.
3. The popup will automatically dismiss after a few seconds, or immediately if you click on it or press `Esc`.

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

## Run Automatically at Windows Login

Setting this up ensures the battery monitor starts automatically every time you log in to Windows.

### Method 1: Automatic 1-Click Setup (Recommended)
1. Navigate to the `scripts\` folder.
2. Double-click **`install_task.bat`** (or right-click and choose **Run as administrator**).
3. The script detects your Python path and creates the `BatteryMemeAlert` task in Windows Task Scheduler.

*(To remove it later, simply run `scripts\uninstall_task.bat`)*

---

### Method 2: Manual Setup via Windows Task Scheduler GUI

If you prefer to configure it manually:

1. Press `Win + R`, type **`taskschd.msc`**, and press `Enter`.
2. In the right-hand panel, click **Create Task...** (do not choose "Create Basic Task").
3. **General Tab**:
   * **Name**: `BatteryMemeAlert`
   * Select: **Run only when user is logged on**.
4. **Triggers Tab**:
   * Click **New...**
   * **Begin the task**: Select **At log on**.
   * Under settings, leave **Any user** or choose your account, then click **OK**.
5. **Actions Tab**:
   * Click **New...**
   * **Action**: Select **Start a program**.
   * **Program/script**:
     ```text
     pythonw.exe
     ```
     *(If `pythonw.exe` is not recognized, supply its full path, e.g.: `C:\Users\<YourUser>\AppData\Local\Programs\Python\Python311\pythonw.exe`)*
   * **Add arguments**:
     ```text
     "src\battery_meme_alert.py"
     ```
   * **Start in (mandatory)**:
     Set this to your project folder path (e.g., `D:\HACKATHON\battery`).
   * Click **OK**.
6. **Conditions Tab (Critical Step)**:
   * **Uncheck** *"Start the task only if the computer is on AC power"*.
   * **Uncheck** *"Stop if the computer switches to battery power"*.
   *(If you leave these checked, Windows will prevent the app from launching while running on battery!)*
7. **Settings Tab**:
   * Check **Allow task to be run on demand**.
   * Click **OK** to save.

You can verify it by right-clicking `BatteryMemeAlert` in the Task Scheduler library and clicking **Run**.

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
