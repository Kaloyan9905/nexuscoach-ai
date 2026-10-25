"""Economy and Laning Phase Tracker: analyzes Gold Hoarding, XP and Level deficits."""

from typing import Any, Dict, List, Optional
from nexuscoach.config import GOLD_HOARDING_THRESHOLD, GOLD_HOARDING_DURATION_MS
from nexuscoach.engine.coordinates import ms_to_timestamp

class EconomyTracker:
    """Tracks gold retention and lane XP advantages/disadvantages."""

    def __init__(self, target_id: int, opponent_id: Optional[int], target_role: str):
        self.target_id = target_id
        self.opponent_id = opponent_id
        self.target_role = target_role

    def analyze_economy(self, frames: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Scan frames for gold hoarding and XP/Level disparities."""
        anomalies: List[Dict[str, Any]] = []

        # 1. Gold Hoarding Detection
        hoarding_start_frame: Optional[int] = None
        hoarding_peak_gold = 0

        for idx, frame in enumerate(frames):
            ts = frame.get("timestamp", idx * 60_000)
            p_frames = frame.get("participantFrames", {})
            user_data = p_frames.get(str(self.target_id), {})
            current_gold = user_data.get("currentGold", 0)

            if current_gold >= GOLD_HOARDING_THRESHOLD:
                if hoarding_start_frame is None:
                    hoarding_start_frame = idx
                    hoarding_peak_gold = current_gold
                else:
                    hoarding_peak_gold = max(hoarding_peak_gold, current_gold)
            else:
                if hoarding_start_frame is not None:
                    duration_frames = idx - hoarding_start_frame
                    duration_seconds = duration_frames * 60
                    if duration_seconds >= 120:  # 2 or more minutes
                        start_ts = frames[hoarding_start_frame].get("timestamp", hoarding_start_frame * 60_000)
                        anomalies.append({
                            "type": "GOLD_HOARDING",
                            "timestamp_ms": start_ts,
                            "timestamp": ms_to_timestamp(start_ts),
                            "held_gold": hoarding_peak_gold,
                            "duration_seconds": duration_seconds,
                            "severity_score": 3.5 + min(2.0, (hoarding_peak_gold - 1500) / 1000.0)
                        })
                    hoarding_start_frame = None
                    hoarding_peak_gold = 0

        # Check if game ended while hoarding
        if hoarding_start_frame is not None:
            duration_frames = len(frames) - 1 - hoarding_start_frame
            duration_seconds = duration_frames * 60
            if duration_seconds >= 120:
                start_ts = frames[hoarding_start_frame].get("timestamp", hoarding_start_frame * 60_000)
                anomalies.append({
                    "type": "GOLD_HOARDING",
                    "timestamp_ms": start_ts,
                    "timestamp": ms_to_timestamp(start_ts),
                    "held_gold": hoarding_peak_gold,
                    "duration_seconds": duration_seconds,
                    "severity_score": 3.5 + min(2.0, (hoarding_peak_gold - 1500) / 1000.0)
                })

        # 2. XP & Level Deficit Tracking (Laning phase: 0 to 14 mins)
        if self.opponent_id:
            max_level_deficit = 0
            worst_deficit_frame = -1
            worst_deficit_ts = 0

            for idx, frame in enumerate(frames):
                ts = frame.get("timestamp", idx * 60_000)
                # Focus primarily on early-to-mid lane phase (up to minute 15)
                if ts > 15 * 60_000:
                    break

                p_frames = frame.get("participantFrames", {})
                user_data = p_frames.get(str(self.target_id), {})
                opp_data = p_frames.get(str(self.opponent_id), {})

                u_lvl = user_data.get("level", 1)
                o_lvl = opp_data.get("level", 1)
                deficit = o_lvl - u_lvl

                if deficit >= 1 and deficit > max_level_deficit:
                    max_level_deficit = deficit
                    worst_deficit_frame = idx
                    worst_deficit_ts = ts

            if max_level_deficit >= 1 and worst_deficit_ts > 0:
                anomalies.append({
                    "type": "LEVEL_DEFICIT",
                    "timestamp_ms": worst_deficit_ts,
                    "timestamp": ms_to_timestamp(worst_deficit_ts),
                    "level_gap": max_level_deficit,
                    "severity_score": 2.0 + (max_level_deficit * 1.0)
                })

        return anomalies
