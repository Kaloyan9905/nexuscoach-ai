"""Context Normalizer: generates a compact JSON manifest under 1,500 tokens for the LLM."""

import json
from typing import Any, Dict

def normalize_coaching_context(analysis_data: Dict[str, Any]) -> str:
    """Compress analysis data into a minimal JSON manifest ready for the LLM."""
    meta = analysis_data.get("metadata", {})
    anomalies = analysis_data.get("top_anomalies", [])[:3]

    manifest = {
        "match": {
            "matchId": meta.get("matchId"),
            "duration": meta.get("duration"),
            "champion": meta.get("userChampion"),
            "opponent": meta.get("opponentChampion"),
            "role": meta.get("role"),
            "result": meta.get("result"),
            "kda": meta.get("kda"),
            "cs_per_min": meta.get("cs_per_min")
        },
        "critical_anomalies": []
    }

    for idx, a in enumerate(anomalies, 1):
        item = {
            "index": idx,
            "timestamp": a.get("timestamp"),
            "type": a.get("type"),
            "severity": round(a.get("severity_score", 0), 1)
        }

        if a.get("type") == "DEATH_ANALYSIS":
            item.update({
                "zone": a.get("zone"),
                "killer": a.get("killer"),
                "assisters": a.get("assisters"),
                "engagement": a.get("engagement_type"),
                "had_vision": a.get("had_vision"),
                "flash_available": a.get("flash_available"),
                "plates_lost_after": a.get("plates_lost_after")
            })
        elif a.get("type") == "GOLD_HOARDING":
            item.update({
                "unspent_gold": a.get("held_gold"),
                "duration_seconds": a.get("duration_seconds")
            })
        elif a.get("type") == "FAILED_ROAM":
            item.update({
                "lane": a.get("lane"),
                "plates_lost_on_tower": a.get("plates_lost")
            })
        elif a.get("type") == "OBJECTIVE_DESYNC":
            item.update({
                "objective": a.get("objective"),
                "distance_to_pit": a.get("distance_to_pit"),
                "lost_to_enemy": a.get("lost_to_enemy"),
                "teleport_available": a.get("teleport_available")
            })
        elif a.get("type") == "LEVEL_DEFICIT":
            item.update({
                "level_gap": a.get("level_gap")
            })

        manifest["critical_anomalies"].append(item)

    return json.dumps(manifest, indent=2)
