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
from logging.handlers import RotatingFileHandler
import argparse
import ctypes
from ctypes import wintypes
from pathlib import Path
import psutil
import pygame
from PIL import Image, ImageTk, ImageDraw
import tkinter as tk

ERROR_ALREADY_EXISTS = 183
_MUTEX_HANDLE = None


def acquire_single_instance_lock(mutex_name: str = "Global\\BatteryMemeAlert_SingleInstance_Mutex") -> bool:
    """
    Ensures only one instance of the application runs across the entire system.
    Returns True if this is the primary instance, or False if another instance is already running.
    """
    global _MUTEX_HANDLE
    try:
        kernel32 = ctypes.windll.kernel32
        CreateMutex = kernel32.CreateMutexW
        CreateMutex.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
        CreateMutex.restype = wintypes.HANDLE

        handle = CreateMutex(None, False, mutex_name)
        last_error = kernel32.GetLastError()

        if last_error == ERROR_ALREADY_EXISTS:
            if handle:
                kernel32.CloseHandle(handle)
            return False
        _MUTEX_HANDLE = handle
        return True
    except Exception as e:
        # Fall back to allowing execution if mutex API encounters an unexpected issue
        return True


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
        "subtitle": "Fully charged. Feel free to unplug.",
        "accent": "#10b981",
        "bg": "#1E1E1E",
        "tag": "FULL POWER (100%)"
    },
    50: {
        "title": "BATTERY AT 50%",
        "subtitle": "Halfway down. Keep an eye on battery life.",
        "accent": "#64748b",
        "bg": "#1E1E1E",
        "tag": "50% REMAINING"
    },
    30: {
        "title": "BATTERY AT 30%",
        "subtitle": "Battery getting low. Consider plugging in.",
        "accent": "#f59e0b",
        "bg": "#1E1E1E",
        "tag": "30% WARNING"
    },
    10: {
        "title": "BATTERY CRITICAL (10%)",
        "subtitle": "Charger needed immediately.",
        "accent": "#f97316",
        "bg": "#1E1E1E",
        "tag": "10% CRITICAL"
    },
    5: {
        "title": "BATTERY EMERGENCY (5%)",
        "subtitle": "System shutdown imminent. Plug in now.",
        "accent": "#ef4444",
        "bg": "#1E1E1E",
        "tag": "5% EMERGENCY"
    },
}

# Set up logging with small rotating handler (max 1 MB, 3 backups) for continuous background execution
log_file = PROJECT_ROOT / "battery_meme_alert.log"
file_handler = RotatingFileHandler(
    log_file,
    maxBytes=1_000_000,
    backupCount=3,
    encoding="utf-8"
)
handlers = [file_handler]
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


# In-memory history tracking to prevent back-to-back repeats per tier
LAST_PLAYED_ASSETS = {
    100: {"image": None, "audio": None},
    50: {"image": None, "audio": None},
    30: {"image": None, "audio": None},
    10: {"image": None, "audio": None},
    5: {"image": None, "audio": None},
}


def get_tier_assets(meme_base_dir: Path, tier: int):
    """
    Scans the tier subfolder for image and audio files and randomly selects one of each.
    Guarantees no back-to-back duplicate selection if more than one option is available.
    """
    tier_dir = meme_base_dir / str(tier)
    if not tier_dir.is_dir():
        logger.warning(f"Tier directory '{tier_dir}' not found.")
        return None, None

    images = sorted([
        f for f in tier_dir.iterdir()
        if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
    ])
    audios = sorted([
        f for f in tier_dir.iterdir()
        if f.is_file() and f.suffix.lower() in AUDIO_EXTENSIONS
    ])

    last_assets = LAST_PLAYED_ASSETS.get(tier, {"image": None, "audio": None})
    last_img = last_assets.get("image")
    last_aud = last_assets.get("audio")

    # Select image (exclude last played if alternatives exist)
    if images:
        if len(images) > 1 and last_img in images:
            candidates = [img for img in images if img != last_img]
            selected_image = random.choice(candidates)
        else:
            selected_image = random.choice(images)
    else:
        selected_image = None

    # Select audio (exclude last played if alternatives exist)
    if audios:
        if len(audios) > 1 and last_aud in audios:
            candidates = [aud for aud in audios if aud != last_aud]
            selected_audio = random.choice(candidates)
        else:
            selected_audio = random.choice(audios)
    else:
        selected_audio = None

    # Update history for this tier
    LAST_PLAYED_ASSETS[tier] = {
        "image": selected_image,
        "audio": selected_audio
    }

    if not images:
        logger.warning(f"No image files found in '{tier_dir}'.")
    if not audios:
        logger.warning(f"No audio files found in '{tier_dir}'.")

    return selected_image, selected_audio


def load_audio_asset(audio_path: Path):
    """
    Pre-loads and decodes an audio file into a pygame.mixer.Sound object in memory
    so it can be triggered instantaneously with zero decoding latency.
    Handles device invalidation (e.g. after sleep/wake) by re-initializing the mixer.
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
    except pygame.error as pge:
        logger.warning(f"Pygame audio device error ({pge}). Re-initializing mixer (system may have resumed from sleep)...")
        try:
            pygame.mixer.quit()
            time.sleep(0.3)
            pygame.mixer.init()
            sound = pygame.mixer.Sound(str(audio_path))
            sound.set_volume(0.9)
            logger.info(f"Pre-loaded audio into memory after mixer reset: {audio_path.name}")
            return sound
        except Exception as e:
            logger.error(f"Audio mixer re-init failed for {audio_path}: {e}")
            return None
    except Exception as e:
        logger.warning(f"Failed to load audio {audio_path} into Sound ({e}). Trying music fallback...")
        try:
            pygame.mixer.music.load(str(audio_path))
            pygame.mixer.music.set_volume(0.9)
            return "music"
        except Exception as e2:
            logger.error(f"Music fallback also failed for {audio_path}: {e2}")
            return None


def apply_rounded_corners(img: Image.Image, radius: int = 8, bg_hex: str = "#1E1E1E") -> Image.Image:
    """
    Applies anti-aliased rounded corners to a PIL Image composited onto a solid background.
    """
    try:
        img = img.convert("RGBA")
        w, h = img.size
        scale = 2
        mask = Image.new("L", (w * scale, h * scale), 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle((0, 0, w * scale - 1, h * scale - 1), radius=radius * scale, fill=255)
        mask = mask.resize((w, h), Image.Resampling.LANCZOS)

        bg_rgb = tuple(int(bg_hex.lstrip("#")[i:i+2], 16) for i in (0, 2, 4))
        bg = Image.new("RGBA", (w, h), bg_rgb + (255,))
        bg.paste(img, (0, 0), mask=mask)
        return bg
    except Exception as e:
        logger.debug(f"Could not apply rounded corners: {e}")
        return img


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
        "accent": "#71717a",
        "bg": "#1e1e1e",
        "tag": f"{tier}% REMAINING"
    })

    root = tk.Tk()
    root.withdraw()  # Keep completely hidden while loading and positioning
    root.title(f"Battery Meme Alert - {tier}%")
    root.overrideredirect(True)  # Borderless window
    root.attributes("-topmost", True)  # Always on top

    # VS Code / Linear style dark palette
    bg_color = "#1E1E1E"        # Dark charcoal background
    border_color = "#3C3C3C"    # Subtle dark-gray 1px border (#3A3A3A - #454545)
    badge_bg = "#2A2A2E"        # Muted charcoal badge background
    badge_border = "#3F3F46"    # Subtle badge border
    badge_fg = "#E4E4E7"        # Off-white / light-gray badge text
    subtext_color = "#A1A1AA"   # Muted light-gray supporting text
    footer_color = "#52525B"    # Low-contrast secondary text
    close_fg_idle = "#71717A"   # Muted gray close button
    close_fg_hover = "#F4F4F5"  # Bright off-white on hover
    close_bg_hover = "#2A2A2E"  # Subtle hover box

    # 1px subtle dark-gray outer border
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

    # Main content container with clean padding (1px offset produces the 1px border)
    container = tk.Frame(root, bg=bg_color, padx=16, pady=14)
    container.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)
    container.bind("<Button-1>", close_popup)

    # Header section
    header_frame = tk.Frame(container, bg=bg_color)
    header_frame.pack(fill=tk.X, pady=(0, 6))
    header_frame.bind("<Button-1>", close_popup)

    # Muted charcoal / dark-gray badge with 1px border and off-white text
    badge_frame = tk.Frame(header_frame, bg=badge_border, padx=1, pady=1)
    badge_frame.pack(side=tk.LEFT)
    badge_frame.bind("<Button-1>", close_popup)

    badge_label = tk.Label(
        badge_frame,
        text=theme["tag"],
        font=("Segoe UI", 8, "bold"),
        fg=badge_fg,
        bg=badge_bg,
        padx=7,
        pady=2
    )
    badge_label.pack()
    badge_label.bind("<Button-1>", close_popup)

    # Close button '✕' with subtle hover state
    close_btn = tk.Label(
        header_frame,
        text="✕",
        font=("Segoe UI", 9, "bold"),
        fg=close_fg_idle,
        bg=bg_color,
        padx=4,
        pady=1,
        cursor="hand2"
    )
    close_btn.pack(side=tk.RIGHT)
    close_btn.bind("<Button-1>", close_popup)

    def on_close_enter(e):
        close_btn.configure(fg=close_fg_hover, bg=close_bg_hover)

    def on_close_leave(e):
        close_btn.configure(fg=close_fg_idle, bg=bg_color)

    close_btn.bind("<Enter>", on_close_enter)
    close_btn.bind("<Leave>", on_close_leave)

    # Subtitle / Message in muted light-gray
    msg_label = tk.Label(
        container,
        text=theme["subtitle"],
        font=("Segoe UI", 9),
        fg=subtext_color,
        bg=bg_color,
        wraplength=320,
        justify=tk.LEFT
    )
    msg_label.pack(anchor="w", pady=(0, 8))
    msg_label.bind("<Button-1>", close_popup)

    # -------------------------------------------------------------
    # Step 3: Load, scale and round corners of meme image
    # -------------------------------------------------------------
    try:
        with Image.open(image_path) as opened_img:
            pil_img = opened_img.copy()

        pil_img.thumbnail((320, 260), Image.Resampling.LANCZOS)
        rounded_img = apply_rounded_corners(pil_img, radius=8, bg_hex=bg_color)
        photo = ImageTk.PhotoImage(rounded_img)

        img_label = tk.Label(container, image=photo, bg=bg_color)
        img_label.image = photo  # Keep reference
        img_label.pack(pady=(2, 6))
        img_label.bind("<Button-1>", close_popup)
    except Exception as e:
        logger.error(f"Error loading image {image_path}: {e}")
        err_label = tk.Label(container, text="[Meme Image Unavailable]", fg="#71717A", bg=bg_color, font=("Segoe UI", 9))
        err_label.pack(pady=10)

    # Footer note: smaller and lower-contrast secondary text
    footer_label = tk.Label(
        container,
        text=f"Auto-closing in {duration_ms // 1000}s  •  Click to dismiss",
        font=("Segoe UI", 8),
        fg=footer_color,
        bg=bg_color
    )
    footer_label.pack(pady=(4, 0))
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
        try:
            image_path, audio_path = get_tier_assets(self.meme_dir, tier)
            if not image_path and not audio_path:
                logger.warning(f"No assets found for tier {tier} in {self.meme_dir / str(tier)}")
                return

            show_meme_popup(tier, image_path, audio_path, duration_ms=POPUP_DURATION_MS)
        except Exception as e:
            logger.error(f"Error displaying meme alert for tier {tier}: {e}", exc_info=True)

    @staticmethod
    def get_tier_bracket(percent: int):
        """
        Determines which tier bracket a given battery percentage belongs to.
        Returns: 50, 30, 10, 5, or None (if > 50%).
        """
        for t in [5, 10, 30, 50]:
            if percent <= t:
                return t
        return None

    def check_battery(self):
        """Single evaluation of battery status against trigger rules."""
        try:
            battery = psutil.sensors_battery()
        except Exception as e:
            logger.warning(f"Failed to query battery status (subsystem may be resuming): {e}")
            return

        if battery is None:
            logger.warning("Battery sensor query returned None (power subsystem may be resuming from sleep). Retrying next cycle.")
            return

        percent = int(battery.percent)
        plugged = bool(battery.power_plugged)
        logger.info(f"Battery check: {percent}% (Plugged: {plugged}), Fired flags: {self.fired}")

        # -------------------------------------------------------------
        # Reset rules (with Hysteresis):
        # Discharging tiers (50, 30, 10, 5) reset ONLY when:
        # 1. Plugged in AND battery has recharged above the tier (percent > tier)
        # 2. OR still unplugged BUT battery has risen at least 3% above that tier (percent >= tier + 3)
        # -------------------------------------------------------------
        for tier in [50, 30, 10, 5]:
            if self.fired[tier]:
                can_reset = False
                reset_reason = ""
                if plugged and percent > tier:
                    can_reset = True
                    reset_reason = f"plugged in and recharged to {percent}% (above {tier}%)"
                elif not plugged and percent >= (tier + 3):
                    can_reset = True
                    reset_reason = f"battery rose to {percent}% (>= {tier + 3}% hysteresis threshold while unplugged)"

                if can_reset:
                    self.fired[tier] = False
                    logger.info(f"Tier {tier}% re-armed: {reset_reason}")

        # Tier 100 reset: resets if unplugged, or if battery drops to <= 97% to prevent 99-100% plugged jitter
        if (not plugged or percent <= 97) and self.fired[100]:
            self.fired[100] = False
            logger.info(f"Tier 100% reset: battery is now {percent}%, plugged={plugged}")

        # -------------------------------------------------------------
        # Trigger rules:
        # -------------------------------------------------------------
        # 1. Tier 100: Fires only when at 100% and plugged in / charging.
        if percent >= 100 and plugged:
            if not self.fired[100]:
                self.fired[100] = True
                self.trigger_tier(100, percent, plugged)

        # 2. Tiers 50, 30, 10, 5: Fire only when discharging (not plugged)
        if not plugged:
            target_tier = self.get_tier_bracket(percent)

            if target_tier is not None:
                # Rule A: Mark every tier strictly ABOVE target_tier as already-fired (without triggering them)
                for t in [50, 30, 10, 5]:
                    if t > target_tier and not self.fired[t]:
                        self.fired[t] = True
                        logger.info(f"Marking skipped tier {t}% as already-fired (battery at {percent}%, in {target_tier}% bracket)")

                # Rule B: Determine if target_tier should fire:
                # It fires if not already fired AND:
                # - First check while discharging (self.last_percent is None)
                # - OR charger was just unplugged (self.last_plugged is True)
                # - OR battery crossed down through/into target_tier (self.last_percent > target_tier)
                should_trigger = False
                if not self.fired[target_tier]:
                    if self.last_percent is None:
                        should_trigger = True
                    elif self.last_plugged is True:
                        should_trigger = True
                    elif self.last_percent > target_tier:
                        should_trigger = True

                if should_trigger:
                    self.fired[target_tier] = True
                    self.trigger_tier(target_tier, percent, plugged)

        self.last_percent = percent
        self.last_plugged = plugged

    def run(self):
        """Main monitoring loop with robust crash recovery."""
        logger.info(f"Battery Meme Alert started. Monitoring every {self.poll_interval}s...")
        logger.info(f"Asset directory: {self.meme_dir}")

        while True:
            try:
                self.check_battery()
            except Exception as e:
                logger.error(f"Error during battery check cycle: {e}", exc_info=True)

            try:
                time.sleep(self.poll_interval)
            except Exception as e:
                logger.warning(f"Sleep interval interrupted: {e}")
                time.sleep(1)


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

    # Check for duplicate running instances (Windows named mutex)
    if not acquire_single_instance_lock():
        logger.info("Another instance of Battery Meme Alert is already running in the background. Exiting duplicate instance.")
        sys.exit(0)

    try:
        app = BatteryMemeAlert(meme_dir=meme_path, poll_interval=args.interval)
        app.run()
    except KeyboardInterrupt:
        logger.info("Battery Meme Alert stopped by user (KeyboardInterrupt).")
    except Exception as e:
        logger.critical(f"Fatal crash in Battery Meme Alert main process: {e}", exc_info=True)
        time.sleep(1)
        sys.exit(1)


if __name__ == "__main__":
    main()
