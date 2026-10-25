"""Desktop Overlay module for NexusCoach AI."""

import os
import sys
import threading
import time
from typing import Optional

def launch_overlay_window(url: str = "http://127.0.0.1:8000", title: str = "NexusCoach AI - Post-Game Review"):
    """Launch native desktop window using pywebview."""
    try:
        import webview
    except ImportError:
        print("❌ pywebview is not installed. Run: pip install pywebview")
        return

    print(f"🖥️ [Desktop Overlay] Launching native window targeting {url}...")
    window = webview.create_window(
        title=title,
        url=url,
        width=1240,
        height=840,
        min_size=(960, 640),
        background_color='#03060d'
    )
    webview.start()
