"""Local disk cache for Riot API match and timeline payloads."""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

DEFAULT_CACHE_DIR = Path(".cache/matches")

class MatchCache:
    """Handles caching of immutable match JSON payloads on disk."""

    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or DEFAULT_CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_path(self, match_id: str, suffix: str) -> Path:
        safe_id = match_id.replace("/", "_").replace("\\", "_")
        return self.cache_dir / f"{safe_id}_{suffix}.json"

    def get_match(self, match_id: str) -> Optional[Dict[str, Any]]:
        path = self._get_path(match_id, "match")
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return None
        return None

    def save_match(self, match_id: str, data: Dict[str, Any]) -> None:
        path = self._get_path(match_id, "match")
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def get_timeline(self, match_id: str) -> Optional[Dict[str, Any]]:
        path = self._get_path(match_id, "timeline")
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return None
        return None

    def save_timeline(self, match_id: str, data: Dict[str, Any]) -> None:
        path = self._get_path(match_id, "timeline")
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass
