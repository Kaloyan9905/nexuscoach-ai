"""Video Clipper module: automates in-game replay recording via Riot's native Replay API."""

import json
import os
import re
import threading
import time
from pathlib import Path
from typing import Dict, Optional
import requests
import urllib3

from nexuscoach.lcu.client import LCUClient

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

GAME_CFG_PATHS = [
    Path(r"C:\Riot Games\League of Legends\Config\game.cfg"),
    Path(r"D:\Riot Games\League of Legends\Config\game.cfg"),
]

VIDEOS_DIR = Path(__file__).parent.parent / "web" / "static" / "videos"
VIDEOS_DIR.mkdir(parents=True, exist_ok=True)

def enable_replay_api_in_cfg() -> bool:
    """Ensure EnableReplayApi=1 is set in game.cfg so the game engine opens port 2999."""
    for cfg_path in GAME_CFG_PATHS:
        if cfg_path.exists():
            try:
                with open(cfg_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                if "EnableReplayApi=1" in content:
                    return True

                if "[General]" in content:
                    new_content = content.replace("[General]", "[General]\nEnableReplayApi=1")
                    with open(cfg_path, "w", encoding="utf-8") as f:
                        f.write(new_content)
                    print(f"[Video Clipper] Enabled Replay API in {cfg_path}")
                    return True
            except Exception as e:
                print(f"[Video Clipper] Could not update {cfg_path}: {e}")
    return False

class VideoClipper:
    """Controls the League Client native video recorder for post-game error highlights."""

    def __init__(self):
        self.lcu = LCUClient()
        enable_replay_api_in_cfg()

    def get_clip_path(self, match_id: str, timestamp_str: str) -> Path:
        """Return the target file path for a clip."""
        safe_match = match_id.replace("/", "_").replace("\\", "_")
        safe_ts = timestamp_str.replace(":", "_")
        return VIDEOS_DIR / f"{safe_match}_{safe_ts}.webm"

    def clip_exists(self, match_id: str, timestamp_str: str) -> bool:
        """Check if clip already exists on disk."""
        return self.get_clip_path(match_id, timestamp_str).exists()

    def start_recording(self, output_path: Path) -> bool:
        """Call POST /replay/recording on port 2999."""
        try:
            payload = {
                "recording": True,
                "format": "webm",
                "path": str(output_path.resolve())
            }
            r = requests.post("https://127.0.0.1:2999/replay/recording", json=payload, verify=False, timeout=3)
            return r.status_code == 200
        except Exception:
            return False

    def stop_recording(self) -> bool:
        """Call POST /replay/recording to stop capture."""
        try:
            r = requests.post("https://127.0.0.1:2999/replay/recording", json={"recording": False}, verify=False, timeout=3)
            return r.status_code == 200
        except Exception:
            return False

    def get_recording_status(self) -> Optional[Dict]:
        """Query GET /replay/recording."""
        try:
            r = requests.get("https://127.0.0.1:2999/replay/recording", verify=False, timeout=2)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        return None

    def capture_clip_async(self, match_id: str, timestamp_str: str, time_seconds: float) -> Dict:
        """Asynchronously triggers replay seek and recording via Riot Replay API."""
        target_path = self.get_clip_path(match_id, timestamp_str)
        clip_filename = f"{match_id.replace('/', '_').replace('\\', '_')}_{timestamp_str.replace(':', '_')}.webm"

        if target_path.exists():
            return {
                "status": "ready",
                "exists": True,
                "video_url": f"/static/videos/{clip_filename}"
            }

        start_time = max(0.0, time_seconds - 6.0)
        end_time = time_seconds + 6.0

        def record_worker():
            try:
                # 1. Seek replay to start of incident
                self.lcu.seek_replay_time(start_time)
                time.sleep(1.0)
                # 2. Trigger recording via Riot 2999 API
                payload = {
                    "recording": True,
                    "startTime": start_time,
                    "endTime": end_time,
                    "codec": "webm",
                    "path": str(target_path.resolve())
                }
                requests.post("https://127.0.0.1:2999/replay/recording", json=payload, verify=False, timeout=3)
            except Exception as e:
                print(f"[Video Clipper Worker] Error capturing clip: {e}")

        threading.Thread(target=record_worker, daemon=True).start()
        return {
            "status": "recording",
            "exists": False,
            "video_url": f"/static/videos/{clip_filename}"
        }
