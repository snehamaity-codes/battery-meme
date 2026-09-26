#!/usr/bin/env python3
"""
Battery Meme Alert - Convenient Root Launcher
"""
import sys
from pathlib import Path

# Add src to sys.path so modules inside src are importable
SRC_DIR = Path(__file__).resolve().parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from battery_meme_alert import main

if __name__ == "__main__":
    main()
