"""LCU (League Client Update) connector and process detector."""

import base64
import os
import re
from pathlib import Path
from typing import Dict, Optional, Tuple
import requests
import urllib3

# Suppress insecure HTTPS warning for Riot's self-signed localhost certificate
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

COMMON_LEAGUE_PATHS = [
    Path(r"C:\Riot Games\League of Legends"),
    Path(r"D:\Riot Games\League of Legends"),
    Path(r"E:\Riot Games\League of Legends"),
]

def find_lockfile() -> Optional[Path]:
    """Scan common paths for active LeagueClient lockfile."""
    for base in COMMON_LEAGUE_PATHS:
        lf = base / "lockfile"
        if lf.exists():
            return lf
    return None

def parse_lockfile(lockfile_path: Path) -> Optional[Dict[str, str]]:
    """Parse lockfile format: process_name:pid:port:password:protocol."""
    try:
        with open(lockfile_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
        parts = content.split(":")
        if len(parts) >= 5:
            return {
                "process": parts[0],
                "pid": parts[1],
                "port": parts[2],
                "password": parts[3],
                "protocol": parts[4]
            }
    except Exception:
        return None
    return None

def get_lcu_credentials() -> Optional[Dict[str, str]]:
    """Retrieve LCU port and auth credentials from lockfile."""
    lf = find_lockfile()
    if lf:
        return parse_lockfile(lf)
    return None
