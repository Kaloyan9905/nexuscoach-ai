"""Rule Engine Orchestrator: Combines deterministic detectors into a unified coaching context."""

from typing import Any, Dict, List, Optional
from nexuscoach.engine.coordinates import ms_to_timestamp
from nexuscoach.engine.death_profiler import DeathProfiler
from nexuscoach.engine.economy_tracker import EconomyTracker
from nexuscoach.engine.roam_analyzer import RoamAnalyzer
from nexuscoach.engine.objective_sync import ObjectiveSyncEngine

class RuleEngine:
    """Master orchestrator for deterministic post-game League of Legends analysis."""

    def __init__(self, match_dto: Dict[str, Any], timeline_dto: Dict[str, Any], target_puuid: str):
        self.match = match_dto
        self.timeline = timeline_dto
        self.target_puuid = target_puuid

        # Extract target participant details from match DTO
        info = self.match.get("info", {})
        participants = info.get("participants", [])

        self.target_participant = None
        self.target_id = None
        self.target_team_id = None
        self.target_role = "MIDDLE"
        self.target_champion = "Unknown"
        self.opponent_participant = None
        self.opponent_id = None

        self.participants_map: Dict[int, Dict[str, Any]] = {}
        for p in participants:
            p_id = p.get("participantId")
            self.participants_map[p_id] = p
            if p.get("puuid") == self.target_puuid:
                self.target_participant = p
                self.target_id = p_id
                self.target_team_id = p.get("teamId", 100)
                self.target_role = p.get("teamPosition") or p.get("individualPosition") or "MIDDLE"
                self.target_champion = p.get("championName", "Unknown")

        if not self.target_participant and participants:
            # Fallback to first participant if not explicitly found
            self.target_participant = participants[0]
            self.target_id = self.target_participant.get("participantId")
            self.target_team_id = self.target_participant.get("teamId", 100)
            self.target_role = self.target_participant.get("teamPosition") or "MIDDLE"
            self.target_champion = self.target_participant.get("championName", "Unknown")

        # Locate lane opponent (same position, opposite team)
        for p in participants:
            if (p.get("teamId") != self.target_team_id and 
                (p.get("teamPosition") == self.target_role or p.get("individualPosition") == self.target_role)):
                self.opponent_participant = p
                self.opponent_id = p.get("participantId")
                break

        # Extract summoner spells for target
        self.summoner_spells = []
        if self.target_participant:
            s1 = self.target_participant.get("summoner1Id")
            s2 = self.target_participant.get("summoner2Id")
            # 12 = Teleport, 4 = Flash, 14 = Ignite, etc.
            if 12 in [s1, s2]:
                self.summoner_spells.append("Teleport")
            if 4 in [s1, s2]:
                self.summoner_spells.append("Flash")

    def run_analysis(self) -> Dict[str, Any]:
        """Execute all analyzers and return consolidated match metrics and top anomalies."""
        timeline_info = self.timeline.get("info", {})
        frames = timeline_info.get("frames", [])

        if not frames or not self.target_id:
            return {"error": "Missing timeline frames or participant data"}

        # 1. Run Analyzers
        death_profiler = DeathProfiler(self.target_id, self.target_team_id, self.participants_map)
        deaths = death_profiler.analyze_deaths(frames)

        economy_tracker = EconomyTracker(self.target_id, self.opponent_id, self.target_role)
        economy_anomalies = economy_tracker.analyze_economy(frames)

        roam_analyzer = RoamAnalyzer(self.target_id, self.target_role, self.target_team_id)
        roam_anomalies = roam_analyzer.analyze_roams(frames)

        obj_engine = ObjectiveSyncEngine(self.target_id, self.target_team_id, self.summoner_spells)
        obj_anomalies = obj_engine.analyze_objectives(frames)

        # 2. Combine and Rank Anomalies
        all_anomalies = deaths + economy_anomalies + roam_anomalies + obj_anomalies
        all_anomalies.sort(key=lambda a: a.get("severity_score", 0), reverse=True)

        # Diverse selection: ensure top takeaways cover multiple macro categories if available
        selected_anomalies: List[Dict[str, Any]] = []
        seen_types = set()
        for a in all_anomalies:
            a_type = a.get("type")
            if a_type not in seen_types:
                selected_anomalies.append(a)
                seen_types.add(a_type)
            if len(selected_anomalies) >= 3:
                break

        for a in all_anomalies:
            if a not in selected_anomalies:
                selected_anomalies.append(a)
            if len(selected_anomalies) >= 5:
                break

        # 3. Overall Match Summary & Timeline Series
        game_duration_sec = self.match.get("info", {}).get("gameDuration", 0)
        minutes = max(1.0, game_duration_sec / 60.0)
        cs = self.target_participant.get("totalMinionsKilled", 0) + self.target_participant.get("neutralMinionsKilled", 0)
        cs_per_min = round(cs / minutes, 1)
        win = self.target_participant.get("win", False)

        timeline_series = []
        for idx, frame in enumerate(frames):
            p_frames = frame.get("participantFrames", {})
            u_data = p_frames.get(str(self.target_id), {})
            o_data = p_frames.get(str(self.opponent_id), {}) if self.opponent_id else {}

            u_total_g = u_data.get("totalGold", 0)
            o_total_g = o_data.get("totalGold", 0)
            u_curr_g = u_data.get("currentGold", 0)
            u_lvl = u_data.get("level", 1)
            o_lvl = o_data.get("level", 1)

            timeline_series.append({
                "minute": idx,
                "timestamp": ms_to_timestamp(frame.get("timestamp", idx * 60_000)),
                "userCurrentGold": u_curr_g,
                "userTotalGold": u_total_g,
                "oppTotalGold": o_total_g,
                "goldDelta": u_total_g - o_total_g,
                "userLevel": u_lvl,
                "oppLevel": o_lvl,
                "userCs": u_data.get("minionsKilled", 0) + u_data.get("jungleMinionsKilled", 0),
                "oppCs": o_data.get("minionsKilled", 0) + o_data.get("jungleMinionsKilled", 0)
            })

        return {
            "metadata": {
                "matchId": self.match.get("metadata", {}).get("matchId", "UNKNOWN"),
                "duration": ms_to_timestamp(game_duration_sec * 1000),
                "duration_seconds": game_duration_sec,
                "userChampion": self.target_champion,
                "opponentChampion": self.opponent_participant.get("championName", "Unknown") if self.opponent_participant else "Unknown",
                "role": self.target_role,
                "result": "Victory" if win else "Defeat",
                "kda": f"{self.target_participant.get('kills', 0)}/{self.target_participant.get('deaths', 0)}/{self.target_participant.get('assists', 0)}",
                "cs": cs,
                "cs_per_min": cs_per_min
            },
            "top_anomalies": selected_anomalies,
            "all_anomalies": all_anomalies,
            "deaths": deaths,
            "timeline_series": timeline_series,
            "total_anomalies_detected": len(all_anomalies)
        }
