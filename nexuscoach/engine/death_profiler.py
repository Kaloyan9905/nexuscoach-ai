"""Death Context Profiler: analyzes conditions, vision, and consequences of player deaths."""

from typing import Any, Dict, List, Optional
from nexuscoach.config import DANGER_DISTANCE, VISION_PROXIMITY_RADIUS, VISION_EXPIRY_MS
from nexuscoach.engine.coordinates import euclidean_distance, ms_to_timestamp, classify_map_zone

class DeathProfiler:
    """Analyzes context for all deaths of the target participant."""

    def __init__(self, target_id: int, target_team_id: int, participants_map: Dict[int, Dict[str, Any]]):
        self.target_id = target_id
        self.target_team_id = target_team_id
        self.participants = participants_map

    def analyze_deaths(self, frames: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Scan frames and events to profile each death of the target player."""
        deaths: List[Dict[str, Any]] = []

        # 1. Collect all allied ward placements: (timestamp, position)
        allied_wards: List[Dict[str, Any]] = []
        for frame in frames:
            for event in frame.get("events", []):
                if event.get("type") == "WARD_PLACED":
                    creator_id = event.get("creatorId", 0)
                    creator = self.participants.get(creator_id, {})
                    if creator.get("teamId") == self.target_team_id:
                        # Wards can have position in event or approximate from participant
                        allied_wards.append({
                            "timestamp": event.get("timestamp", 0),
                            "wardType": event.get("wardType", "STEALTH_WARD"),
                            "position": event.get("position")
                        })

        # 2. Iterate through all champion kill events
        for frame_idx, frame in enumerate(frames):
            frame_timestamp = frame.get("timestamp", 0)
            participant_frames = frame.get("participantFrames", {})

            for event in frame.get("events", []):
                if event.get("type") == "CHAMPION_KILL" and event.get("victimId") == self.target_id:
                    death_ts = event.get("timestamp", frame_timestamp)
                    pos = event.get("position") or {}
                    if not pos and str(self.target_id) in participant_frames:
                        pos = participant_frames[str(self.target_id)].get("position", {})

                    killer_id = event.get("killerId", 0)
                    assisting_ids = event.get("assistingParticipantIds", [])
                    killer_info = self.participants.get(killer_id, {})
                    assisters = [self.participants.get(aid, {}) for aid in assisting_ids]

                    # Total enemies actively credited with the kill
                    enemies_involved_count = 1 + len(assisting_ids) if killer_id != 0 else len(assisting_ids)
                    if enemies_involved_count == 1:
                        engagement_type = "1v1 Solo Death"
                    elif enemies_involved_count == 2:
                        engagement_type = "1v2 Gank"
                    else:
                        engagement_type = f"1v{enemies_involved_count} Collapse"

                    # Vision check: Any allied ward in 1800 units placed in prior 90 seconds
                    had_vision = False
                    for ward in allied_wards:
                        w_ts = ward.get("timestamp", 0)
                        w_pos = ward.get("position")
                        # Must be within past 90 seconds (90,000 ms)
                        if 0 <= (death_ts - w_ts) <= VISION_EXPIRY_MS and w_pos and pos:
                            dist = euclidean_distance(pos, w_pos)
                            if dist <= VISION_PROXIMITY_RADIUS:
                                had_vision = True
                                break

                    # Check flash status: victimDamageDealt / spells
                    # In League match-v5, summoner spell casts can be detected or check held flash
                    flash_available = True
                    # Look at recent events within 300s to see if Flash was used
                    for check_frame in frames:
                        for ev in check_frame.get("events", []):
                            if (ev.get("type") == "SPELL_CAST" and 
                                ev.get("participantId") == self.target_id and 
                                ev.get("spellName") == "SummonerFlash"):
                                spell_ts = ev.get("timestamp", 0)
                                if 0 <= (death_ts - spell_ts) < 300_000:
                                    flash_available = False
                                    break

                    zone = classify_map_zone(pos.get("x", 8000), pos.get("y", 8000))

                    # Assess consequence (plates or turrets lost in subsequent 60s)
                    plates_lost = 0
                    for follow_frame in frames[frame_idx:frame_idx + 2]:
                        for ev in follow_frame.get("events", []):
                            if (ev.get("type") == "BUILDING_TURRET_PLATE_DESTROYED" and 
                                0 <= (ev.get("timestamp", 0) - death_ts) <= 60_000):
                                plates_lost += 1

                    deaths.append({
                        "type": "DEATH_ANALYSIS",
                        "timestamp_ms": death_ts,
                        "timestamp": ms_to_timestamp(death_ts),
                        "position": pos,
                        "zone": zone,
                        "killer": killer_info.get("championName", "Unknown"),
                        "killer_role": killer_info.get("role", "UNKNOWN"),
                        "assisters": [a.get("championName", "Unknown") for a in assisters],
                        "engagement_type": engagement_type,
                        "enemies_count": enemies_involved_count,
                        "had_vision": had_vision,
                        "flash_available": flash_available,
                        "plates_lost_after": plates_lost,
                        "severity_score": 3.0 + (1.5 if not had_vision else 0) + (1.0 if flash_available else 0) + (plates_lost * 1.5)
                    })

        return deaths
