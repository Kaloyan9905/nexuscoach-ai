"""Objective Synchronization Engine: detects absenteeism and cross-map desync at epic monsters."""

import math
from typing import Any, Dict, List, Optional
from nexuscoach.config import DRAGON_PIT, BARON_PIT, OBJECTIVE_PRE_SPAWN_START_MS, OBJECTIVE_PRE_SPAWN_END_MS
from nexuscoach.engine.coordinates import ms_to_timestamp, euclidean_distance

class ObjectiveSyncEngine:
    """Analyzes player spatial positioning around epic objectives."""

    def __init__(self, target_id: int, target_team_id: int, summoner_spells: List[str]):
        self.target_id = target_id
        self.target_team_id = target_team_id
        self.has_teleport = any("Teleport" in s for s in summoner_spells)

    def analyze_objectives(self, frames: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify instances where player was absent from major objective fights without TP."""
        anomalies: List[Dict[str, Any]] = []

        # Find all elite monster kill events
        for frame_idx, frame in enumerate(frames):
            for event in frame.get("events", []):
                if event.get("type") == "ELITE_MONSTER_KILL":
                    m_type = event.get("monsterType", "")
                    if m_type not in ["DRAGON", "BARON_NASHOR", "RIFTHERALD"]:
                        continue

                    obj_time_ms = event.get("timestamp", 0)
                    killer_team_id = event.get("killerTeamId", 0)
                    pit_pos = {"x": DRAGON_PIT[0], "y": DRAGON_PIT[1]} if m_type == "DRAGON" else {"x": BARON_PIT[0], "y": BARON_PIT[1]}

                    # Pre-fight window: look at player position in the nearest frame
                    player_pos = None
                    p_frames = frame.get("participantFrames", {})
                    if str(self.target_id) in p_frames:
                        player_pos = p_frames[str(self.target_id)].get("position")

                    # If not in this frame, look at preceding frame
                    if not player_pos and frame_idx > 0:
                        prev_p_frames = frames[frame_idx - 1].get("participantFrames", {})
                        if str(self.target_id) in prev_p_frames:
                            player_pos = prev_p_frames[str(self.target_id)].get("position")

                    if not player_pos:
                        continue

                    dist_to_obj = euclidean_distance(player_pos, pit_pos)

                    # Player was cross-map (> 6000 units away)
                    is_cross_map = dist_to_obj > 6500

                    # If player was cross map and enemy team took it (or team lost it)
                    lost_objective = (killer_team_id != self.target_team_id)

                    if is_cross_map and (lost_objective or not self.has_teleport):
                        anomalies.append({
                            "type": "OBJECTIVE_DESYNC",
                            "timestamp_ms": obj_time_ms,
                            "timestamp": ms_to_timestamp(obj_time_ms),
                            "objective": m_type,
                            "distance_to_pit": int(dist_to_obj),
                            "lost_to_enemy": lost_objective,
                            "teleport_available": self.has_teleport,
                            "severity_score": 4.0 if lost_objective else 2.5
                        })

        return anomalies
