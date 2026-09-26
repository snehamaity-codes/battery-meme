"""
Battery Meme Alert - Background Windows Battery Monitor
Watches battery percentage and charging state, popping up random meme images
and matching audio clips when reaching specific milestones (100, 50, 30, 10, 5).
"""

import os
import sys
import time
import random
import logging
import argparse
from pathlib import Path
import psutil
import pygame
from PIL import Image, ImageTk
import tkinter as tk


def get_project_root() -> Path:
    """Returns the root directory of the project."""
    script_dir = Path(__file__).resolve().parent
    if script_dir.name.lower() == "src":
        return script_dir.parent
    return script_dir


PROJECT_ROOT = get_project_root()


def get_default_meme_dir() -> Path:
    """Finds the meme asset directory across common root locations."""
    candidates = [
        PROJECT_ROOT / "meme",
        Path.cwd() / "meme",
        Path(__file__).resolve().parent / "meme",
    ]
    for c in candidates:
        if c.is_dir():
            return c.resolve()
    return (PROJECT_ROOT / "meme").resolve()


# Configuration Defaults
DEFAULT_MEME_DIR = get_default_meme_dir()
POLL_INTERVAL_SEC = 25
POPUP_DURATION_MS = 10000  # 10 seconds display time (single source of truth)
POPUP_DURATION_SEC = POPUP_DURATION_MS // 1000

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".ogg"}

# Visual theme configurations per tier
TIER_THEMES = {
    100: {
        "title": "BATTERY FULL (100%)",
        "subtitle": "Fully charged! Feel free to unplug.",
        "accent": "#22c55e",  # Green
        "bg": "#0f172a",
        "tag": "FULL POWER (100%)"
    },
    50: {
        "title": "BATTERY AT 50%",
        "subtitle": "Halfway down! Keep an eye on your battery.",
        "accent": "#3b82f6",  # Blue
        "bg": "#0f172a",
        "tag": "50% REMAINING"
    },
    30: {
        "title": "BATTERY AT 30%",
        "subtitle": "Battery getting low! Consider plugging in.",
        "accent": "#f59e0b",  # Amber
        "bg": "#0f172a",
        "tag": "30% WARNING"
    },
    10: {
        "title": "BATTERY CRITICAL (10%)",
        "subtitle": "Charger needed immediately!",
        "accent": "#f97316",  # Orange
        "bg": "#18181b",
        "tag": "10% CRITICAL"
    },
    5: {
        "title": "BATTERY EMERGENCY (5%)",
        "subtitle": "System shutdown imminent! Plug in NOW!",
        "accent": "#ef4444",  # Danger Red
        "bg": "#18181b",
        "tag": "5% EMERGENCY"
    },
}

# Set up logging with rotating/safe handlers for pythonw.exe
log_file = PROJECT_ROOT / "battery_meme_alert.log"
handlers = [logging.FileHandler(log_file, encoding="utf-8")]
if sys.stdout is not None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    handlers.append(logging.StreamHandler(sys.stdout))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=handlers
)
logger = logging.getLogger("BatteryMemeAlert")


def get_tier_assets(meme_base_dir: Path, tier: int):
    """
    Scans the tier subfolder for image and audio files and randomly selects one of each.
    """
    tier_dir = meme_base_dir / str(tier)
    if not tier_dir.is_dir():
        logger.warning(f"Tier directory '{tier_dir}' not found.")
        return None, None

    images = [
        f for f in tier_dir.iterdir()
        if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
    ]
    audios = [
        f for f in tier_dir.iterdir()
        if f.is_file() and f.suffix.lower() in AUDIO_EXTENSIONS
    ]

    selected_image = random.choice(images) if images else None
    selected_audio = random.choice(audios) if audios else None

    if not images:
        logger.warning(f"No image files found in '{tier_dir}'.")
    if not audios:
        logger.warning(f"No audio files found in '{tier_dir}'.")

    return selected_image, selected_audio


def load_audio_asset(audio_path: Path):
    """
    Pre-loads and decodes an audio file into a pygame.mixer.Sound object in memory
    so it can be triggered instantaneously with zero decoding latency.
    """
    if not audio_path or not audio_path.exists():
        return None
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        sound = pygame.mixer.Sound(str(audio_path))
        sound.set_volume(0.9)
        logger.info(f"Pre-loaded audio into memory: {audio_path.name}")
        return sound
    except Exception as e:
        logger.warning(f"Failed to load audio {audio_path} into Sound ({e}). Trying music fallback...")
        try:
            pygame.mixer.music.load(str(audio_path))
            pygame.mixer.music.set_volume(0.9)
            return "music"
        except Exception as e2:
            logger.error(f"Music fallback also failed for {audio_path}: {e2}")
            return None


def show_meme_popup(tier: int, image_path: Path, audio_path: Path = None, duration_ms: int = POPUP_DURATION_MS):
    """
    Displays a modern, borderless popup window on top of all windows
    positioned in the bottom-right corner of the screen.

    Both the image and the audio are fully pre-loaded and prepared before either
    is triggered, ensuring the audio playback and the window reveal happen at
    the exact same moment with zero lag.
    """
    # -------------------------------------------------------------
    # Step 1: Pre-load and decode audio into memory buffer first
    # -------------------------------------------------------------
    sound = load_audio_asset(audio_path) if audio_path else None

    if not image_path or not image_path.exists():
        logger.warning("No image to display for popup.")
        if sound:
            if isinstance(sound, pygame.mixer.Sound):
                sound.play()
            else:
                pygame.mixer.music.play()
        time.sleep(duration_ms / 1000.0)
        return

    # -------------------------------------------------------------
    # Step 2: Initialize hidden window & construct all widgets
    # -------------------------------------------------------------
    theme = TIER_THEMES.get(tier, {
        "title": f"BATTERY {tier}%",
        "subtitle": "Battery status update",
        "accent": "#3b82f6",
        "bg": "#0f172a",
        "tag": f"⚡ {tier}%"
    })

    root = tk.Tk()
    root.withdraw()  # Keep completely hidden while loading and positioning
    root.title(f"Battery Meme Alert - {tier}%")
    root.overrideredirect(True)  # Borderless window
    root.attributes("-topmost", True)  # Always on top

    bg_color = theme["bg"]
    accent_color = theme["accent"]
    border_color = accent_color
    subtext_color = "#94a3b8"

    root.configure(bg=border_color)

    def close_popup(event=None):
        try:
            if sound:
                if isinstance(sound, pygame.mixer.Sound):
                    sound.stop()
                else:
                    pygame.mixer.music.stop()
            root.destroy()
        except Exception:
            pass

    # Key and click bindings to dismiss
    root.bind("<Escape>", close_popup)
    root.bind("<Button-1>", close_popup)

    # Auto-close timer derived strictly from duration_ms (default: 10000ms / 10s)
    root.after(duration_ms, close_popup)

    # Outer border container (2px border effect)
    container = tk.Frame(root, bg=bg_color, padx=14, pady=12)
    container.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
    container.bind("<Button-1>", close_popup)

    # Header section
    header_frame = tk.Frame(container, bg=bg_color)
    header_frame.pack(fill=tk.X, pady=(0, 8))
    header_frame.bind("<Button-1>", close_popup)

    # Tier Badge / Tag
    badge_label = tk.Label(
        header_frame,
        text=theme["tag"],
        font=("Segoe UI", 9, "bold"),
        fg=bg_color,
        bg=accent_color,
        padx=8,
        pady=2
    )
    badge_label.pack(side=tk.LEFT)
    badge_label.bind("<Button-1>", close_popup)

    # Close button '✕'
    close_btn = tk.Label(
        header_frame,
        text="✕",
        font=("Segoe UI", 11, "bold"),
        fg="#64748b",
        bg=bg_color,
        cursor="hand2"
    )
    close_btn.pack(side=tk.RIGHT)
    close_btn.bind("<Button-1>", close_popup)

    # Subtitle / Message
    msg_label = tk.Label(
        container,
        text=theme["subtitle"],
        font=("Segoe UI", 9),
        fg=subtext_color,
        bg=bg_color,
        wraplength=340,
        justify=tk.LEFT
    )
    msg_label.pack(anchor="w", pady=(0, 8))
    msg_label.bind("<Button-1>", close_popup)

    # -------------------------------------------------------------
    # Step 3: Load and scale meme image into displayable PhotoImage
    # -------------------------------------------------------------
    try:
        pil_img = Image.open(image_path)
        pil_img.thumbnail((340, 300), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(pil_img)

        img_label = tk.Label(container, image=photo, bg=bg_color)
        img_label.image = photo  # Keep reference
        img_label.pack(pady=4)
        img_label.bind("<Button-1>", close_popup)
    except Exception as e:
        logger.error(f"Error loading image {image_path}: {e}")
        err_label = tk.Label(container, text="[Meme Image Unavailable]", fg="#ef4444", bg=bg_color)
        err_label.pack(pady=10)

    # Footer note: reads duration directly from duration_ms (guaranteed in sync)
    footer_label = tk.Label(
        container,
        text=f"Auto-closing in {duration_ms // 1000}s  •  Click to dismiss",
        font=("Segoe UI", 8),
        fg="#64748b",
        bg=bg_color
    )
    footer_label.pack(pady=(8, 0))
    footer_label.bind("<Button-1>", close_popup)

    # Calculate geometry while window remains hidden
    root.update_idletasks()
    win_w = root.winfo_reqwidth()
    win_h = root.winfo_reqheight()
    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()

    x = max(10, screen_w - win_w - 24)
    y = max(10, screen_h - win_h - 56)
    root.geometry(f"{win_w}x{win_h}+{x}+{y}")

    # -------------------------------------------------------------
    # Step 4: Synchronized trigger (Audio + Popup together)
    # Both assets are 100% prepared in memory. Call play() on the
    # audio and deiconify() on the window back-to-back with zero delay.
    # -------------------------------------------------------------
    if sound:
        if isinstance(sound, pygame.mixer.Sound):
            sound.play()
        else:
            pygame.mixer.music.play()
    root.deiconify()
    root.update()

    try:
        root.mainloop()
    except Exception as e:
        logger.error(f"Error in Tkinter loop: {e}")


class BatteryMemeAlert:
    """
    Monitors battery status and triggers meme alerts when crossing predefined tiers.
    """
    def __init__(self, meme_dir: Path, poll_interval: int = POLL_INTERVAL_SEC):
        self.meme_dir = Path(meme_dir).resolve()
        self.poll_interval = poll_interval

        # Independent fired state for each tier (5 flags total)
        self.fired = {
            100: False,
            50: False,
            30: False,
            10: False,
            5: False,
        }
        self.last_percent = None
        self.last_plugged = None

        try:
            pygame.mixer.init()
        except Exception as e:
            logger.warning(f"Could not pre-initialize pygame mixer: {e}")

    def trigger_tier(self, tier: int, current_percent: int, plugged: bool):
        """Picks random assets and triggers the popup & sound for the tier."""
        logger.info(f"[TRIGGER] Tier {tier}% fired (Current: {current_percent}%, Plugged: {plugged})")
        image_path, audio_path = get_tier_assets(self.meme_dir, tier)
        if not image_path and not audio_path:
            logger.warning(f"No assets found for tier {tier} in {self.meme_dir / str(tier)}")
            return

        show_meme_popup(tier, image_path, audio_path, duration_ms=POPUP_DURATION_MS)

    def check_battery(self):
        """Single evaluation of battery status against trigger rules."""
        battery = psutil.sensors_battery()
        if battery is None:
            logger.debug("No battery sensor detected.")
            return

        percent = int(battery.percent)
        plugged = bool(battery.power_plugged)
        logger.info(f"Battery check: {percent}% (Plugged: {plugged}), Fired flags: {self.fired}")

        # -------------------------------------------------------------
        # Reset rules:
        # When battery recharges above a tier threshold, reset that flag
        # so it is armed to trigger again on the next drain cycle.
        # -------------------------------------------------------------
        for tier in [50, 30, 10, 5]:
            if percent > tier and self.fired[tier]:
                self.fired[tier] = False
                logger.info(f"Tier {tier} reset: battery recharged to {percent}% (above {tier}%)")

        if (percent < 100 or not plugged) and self.fired[100]:
            self.fired[100] = False
            logger.info(f"Tier 100 reset: battery is now {percent}%, plugged={plugged}")

        # -------------------------------------------------------------
        # Trigger rules:
        # -------------------------------------------------------------
        # 1. Tier 100: Fires only when at 100% and plugged in / charging.
        if percent >= 100 and plugged:
            if not self.fired[100]:
                self.fired[100] = True
                self.trigger_tier(100, percent, plugged)

        # 2. Tiers 50, 30, 10, 5: Fire only when discharging (not plugged)
        #    and only when percentage drops down to or through that number.
        if not plugged:
            for tier in [50, 30, 10, 5]:
                crossed = False
                if self.last_percent is not None:
                    # Continuous monitoring: crossed from above to at or below threshold
                    # OR charger was unplugged while already at or below threshold
                    if (self.last_percent > tier >= percent) or (self.last_plugged is True and percent <= tier):
                        crossed = True
                else:
                    # On initial startup while discharging:
                    # Identify which tier bracket the battery is currently in
                    active_tier = None
                    for t in [5, 10, 30, 50]:
                        if percent <= t:
                            active_tier = t
                            break
                    if active_tier:
                        # Mark tiers higher than active_tier as already fired
                        for t in [50, 30, 10, 5]:
                            if t > active_tier:
                                self.fired[t] = True
                        if tier == active_tier:
                            crossed = True

                if crossed and not self.fired[tier]:
                    self.fired[tier] = True
                    self.trigger_tier(tier, percent, plugged)
                    break

        self.last_percent = percent
        self.last_plugged = plugged

    def run(self):
        """Main monitoring loop."""
        logger.info(f"Battery Meme Alert started. Monitoring every {self.poll_interval}s...")
        logger.info(f"Asset directory: {self.meme_dir}")

        while True:
            try:
                self.check_battery()
            except Exception as e:
                logger.error(f"Error during battery check cycle: {e}", exc_info=True)

            time.sleep(self.poll_interval)


def main():
    parser = argparse.ArgumentParser(description="Battery Meme Alert for Windows")
    parser.add_argument(
        "--path",
        type=str,
        default=str(DEFAULT_MEME_DIR),
        help="Path to folder containing tier subfolders (100, 50, 30, 10, 5)"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=POLL_INTERVAL_SEC,
        help=f"Battery check interval in seconds (default: {POLL_INTERVAL_SEC})"
    )
    parser.add_argument(
        "--test",
        type=int,
        nargs="?",
        const=100,
        choices=[100, 50, 30, 10, 5],
        help="Test popup and sound for a specific tier immediately and exit (e.g. --test 50)"
    )
    args = parser.parse_args()

    meme_path = Path(args.path).resolve()

    if args.test is not None:
        logger.info(f"--- Running manual test for tier {args.test}% ---")
        img, audio = get_tier_assets(meme_path, args.test)
        logger.info(f"Selected Image: {img}")
        logger.info(f"Selected Audio: {audio}")
        show_meme_popup(args.test, img, audio, duration_ms=POPUP_DURATION_MS)
        logger.info("Test completed successfully.")
        return

    app = BatteryMemeAlert(meme_dir=meme_path, poll_interval=args.interval)
    app.run()


if __name__ == "__main__":
    main()
