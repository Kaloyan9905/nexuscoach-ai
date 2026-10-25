"""LCU Client for communicating directly with the running League of Legends desktop client."""

import base64
from typing import Any, Dict, Optional
import requests
import urllib3

from nexuscoach.lcu.lockfile import get_lcu_credentials

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class LCUClient:
    """Client for querying the local League Client Update (LCU) REST API."""

    def __init__(self, port: Optional[str] = None, password: Optional[str] = None):
        self.port = port
        self.password = password
        self.session = requests.Session()
        self.session.verify = False  # Riot uses self-signed localhost certificates

        if not self.port or not self.password:
            self.refresh_credentials()

    def refresh_credentials(self) -> bool:
        """Attempt to read credentials from active League lockfile."""
        creds = get_lcu_credentials()
        if creds:
            self.port = creds["port"]
            self.password = creds["password"]
            token = base64.b64encode(f"riot:{self.password}".encode("ascii")).decode("ascii")
            self.session.headers.update({
                "Authorization": f"Basic {token}",
                "Accept": "application/json"
            })
            return True
        return False

    @property
    def base_url(self) -> Optional[str]:
        if self.port:
            return f"https://127.0.0.1:{self.port}"
        return None

    def start_league_client(self) -> bool:
        """Directly launch the League of Legends client / Riot Client if not running."""
        import subprocess
        from pathlib import Path
        import json

        # 1. Check RiotClientInstalls.json
        installs_json = Path(r"C:\ProgramData\Riot Games\RiotClientInstalls.json")
        if installs_json.exists():
            try:
                with open(installs_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
                rc_path = data.get("rc_default") or data.get("rc_live")
                if rc_path and Path(rc_path).exists():
                    cmd = [str(rc_path), "--launch-product=league_of_legends", "--launch-patchline=live"]
                    subprocess.Popen(cmd, close_fds=True)
                    return True
            except Exception:
                pass

        # 2. Check common installation directories
        for base in [Path(r"C:\Riot Games"), Path(r"D:\Riot Games"), Path(r"E:\Riot Games")]:
            rc = base / "Riot Client" / "RiotClientServices.exe"
            if rc.exists():
                cmd = [str(rc), "--launch-product=league_of_legends", "--launch-patchline=live"]
                subprocess.Popen(cmd, close_fds=True)
                return True
            lc = base / "League of Legends" / "LeagueClient.exe"
            if lc.exists():
                subprocess.Popen([str(lc)], close_fds=True)
                return True

        return False

    def is_client_running(self) -> bool:
        """Check if League client is running and responding."""
        if not self.base_url or not self.port:
            if not self.refresh_credentials():
                return False
        try:
            r = self.session.get(f"{self.base_url}/lol-gameflow/v1/gameflow-phase", timeout=2)
            if r.status_code == 200:
                return True
        except Exception:
            pass

        # Re-check credentials in case the client restarted on a new port
        if self.refresh_credentials():
            try:
                r = self.session.get(f"{self.base_url}/lol-gameflow/v1/gameflow-phase", timeout=2)
                return r.status_code == 200
            except Exception:
                pass

        return False

    def get_gameflow_phase(self) -> Optional[str]:
        """Fetch current game phase (e.g. InProgress, PreEndGame, EndOfGame, Lobby, None)."""
        if not self.base_url and not self.refresh_credentials():
            return None
        try:
            r = self.session.get(f"{self.base_url}/lol-gameflow/v1/gameflow-phase", timeout=2)
            if r.status_code == 200:
                # May return string with quotes e.g. '"EndOfGame"'
                return r.text.strip('"').strip()
        except Exception:
            pass
        return None

    def get_current_summoner(self) -> Optional[Dict[str, Any]]:
        """Fetch currently logged-in summoner info from client."""
        if not self.base_url and not self.refresh_credentials():
            return None
        try:
            r = self.session.get(f"{self.base_url}/lol-summoner/v1/current-summoner", timeout=3)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        return None

    def launch_replay(self, game_id: str) -> bool:
        """Request the League client to download and launch the match replay."""
        if not self.base_url and not self.refresh_credentials():
            return False
        # Clean game_id: if format is EUN1_4019210467, extract numerical gameId
        clean_id = game_id.split("_")[-1] if "_" in game_id else game_id
        payload = {"contextData": "MATCH_HISTORY", "componentType": "REPLAY"}
        try:
            # 1. Graceful download
            self.session.post(f"{self.base_url}/lol-replays/v1/rofls/{clean_id}/download/graceful", json=payload, timeout=5)
            # 2. Watch replay
            r = self.session.post(f"{self.base_url}/lol-replays/v1/rofls/{clean_id}/watch", json=payload, timeout=5)
            if r.status_code in [200, 204]:
                return True

            # If downloading, retry watching briefly
            import time
            for _ in range(8):
                time.sleep(1.0)
                st = self.session.get(f"{self.base_url}/lol-replays/v1/rofls/{clean_id}", timeout=3)
                if st.status_code == 200 and st.json().get("state") == "watch":
                    w = self.session.post(f"{self.base_url}/lol-replays/v1/rofls/{clean_id}/watch", json=payload, timeout=5)
                    return w.status_code in [200, 204]
            return False
        except Exception:
            return False

    def seek_replay_time(self, seconds: float) -> bool:
        """Seek in-game spectator/replay playback time directly via port 2999."""
        try:
            r = requests.post(
                "https://127.0.0.1:2999/replay/playback",
                json={"time": max(0.0, float(seconds)), "paused": False},
                verify=False,
                timeout=2
            )
            return r.status_code == 200
        except Exception:
            return False

    def set_replay_camera(
        self,
        champion_name: Optional[str] = None,
        x: Optional[float] = None,
        y: Optional[float] = None,
        camera_attached: bool = True
    ) -> bool:
        """Position and lock the spectator camera on the player champion via port 2999."""
        try:
            payload: Dict[str, Any] = {
                "cameraMode": "top"
            }
            if champion_name:
                # Always attach and lock spectator camera strictly to player's champion
                payload["selectionName"] = champion_name
                payload["cameraAttached"] = True
            elif x is not None and y is not None:
                # Fallback to coordinate position only if champion name is unavailable
                payload["cameraPosition"] = {
                    "x": float(x),
                    "y": 1900.0,
                    "z": float(y)
                }
                payload["cameraAttached"] = False

            r = requests.post(
                "https://127.0.0.1:2999/replay/render",
                json=payload,
                verify=False,
                timeout=2
            )
            return r.status_code == 200
        except Exception:
            return False
