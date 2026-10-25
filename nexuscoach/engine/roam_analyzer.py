"""Failed Roam Analyzer: detects roams with zero return and high opportunity cost."""

import math
from typing import Any, Dict, List, Optional
from nexuscoach.config import MID_CENTER, FAILED_ROAM_MIN_DURATION_MS
from nexuscoach.engine.coordinates import ms_to_timestamp

class RoamAnalyzer:
    """Analyzes solo laner roaming efficiency and opportunity cost."""

    def __init__(self, target_id: int, target_role: str, target_team_id: int):
        self.target_id = target_id
        self.target_role = target_role.upper()
        self.target_team_id = target_team_id

    def is_outside_home_lane(self, pos: Dict[str, Any]) -> bool:
        """Determine if player position is outside their assigned primary lane."""
        x = float(pos.get("x", 8000))
        y = float(pos.get("y", 8000))

        if "MID" in self.target_role:
            # Mid lane is diagonal band near center
            dist_center = math.hypot(x - MID_CENTER[0], y - MID_CENTER[1])
            dist_diagonal = abs(x - y) / math.sqrt(2)
            # Outside if far from center and not along the diagonal lane
            return dist_center > 2600 and dist_diagonal > 1600
        elif "TOP" in self.target_role:
            # Top lane is top-left edge
            return x > 4500 and y < 11000
        return False

    def analyze_roams(self, frames: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify roams during laning phase (0-14 min) that yielded zero takedowns."""
        anomalies: List[Dict[str, Any]] = []

        # We look at laning phase frames (0 to 14)
        for idx in range(1, min(len(frames) - 1, 15)):
            frame = frames[idx]
            ts = frame.get("timestamp", idx * 60_000)
            p_frames = frame.get("participantFrames", {})
            user_data = p_frames.get(str(self.target_id), {})
            pos = user_data.get("position", {})

            if not pos:
                continue

            if self.is_outside_home_lane(pos):
                # Check for takedowns (kills or assists) in this minute window
                takedowns = 0
                for ev in frame.get("events", []):
                    if ev.get("type") == "CHAMPION_KILL":
                        if ev.get("killerId") == self.target_id or self.target_id in ev.get("assistingParticipantIds", []):
                            takedowns += 1

                # If no takedowns, check if enemy team took plates or pushed tower
                plates_lost = 0
                for ev in frame.get("events", []):
                    if ev.get("type") == "BUILDING_TURRET_PLATE_DESTROYED":
                        # If destroyed by enemy
                        plate_killer = ev.get("killerId", 0)
                        if plate_killer != self.target_id:
                            plates_lost += 1

                if takedowns == 0:
                    anomalies.append({
                        "type": "FAILED_ROAM",
                        "timestamp_ms": ts,
                        "timestamp": ms_to_timestamp(ts),
                        "lane": self.target_role,
                        "plates_lost": plates_lost,
                        "severity_score": 3.0 + (plates_lost * 1.5)
                    })

        return anomalies
