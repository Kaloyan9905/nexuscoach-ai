"""Synthetic realistic sample match and timeline data for testing."""

from typing import Any, Dict, Tuple

SAMPLE_PUUID = "sample-player-puuid-ahri-mid"

def get_sample_match_data() -> Tuple[Dict[str, Any], Dict[str, Any], str]:
    """Return synthetic (match_dto, timeline_dto, puuid)."""
    match_dto = {
        "metadata": {
            "matchId": "EUN1_SAMPLE_354129988",
            "participants": [SAMPLE_PUUID, "opp-puuid-syndra-mid"]
        },
        "info": {
            "gameDuration": 1694,  # ~28:14
            "participants": [
                {
                    "participantId": 1,
                    "puuid": SAMPLE_PUUID,
                    "teamId": 100,
                    "championName": "Ahri",
                    "teamPosition": "MIDDLE",
                    "individualPosition": "MIDDLE",
                    "kills": 3,
                    "deaths": 5,
                    "assists": 2,
                    "totalMinionsKilled": 160,
                    "neutralMinionsKilled": 12,
                    "win": False,
                    "summoner1Id": 4,   # Flash
                    "summoner2Id": 14   # Ignite (No Teleport)
                },
                {
                    "participantId": 6,
                    "puuid": "opp-puuid-syndra-mid",
                    "teamId": 200,
                    "championName": "Syndra",
                    "teamPosition": "MIDDLE",
                    "individualPosition": "MIDDLE",
                    "kills": 7,
                    "deaths": 1,
                    "assists": 6,
                    "totalMinionsKilled": 195,
                    "neutralMinionsKilled": 4,
                    "win": True,
                    "summoner1Id": 4,
                    "summoner2Id": 12   # Teleport
                },
                {
                    "participantId": 7,
                    "puuid": "jungle-puuid-jarvan",
                    "teamId": 200,
                    "championName": "JarvanIV",
                    "teamPosition": "JUNGLE",
                    "individualPosition": "JUNGLE"
                }
            ]
        }
    }

    # Generate 28 frames
    frames = []
    for m in range(29):
        ts = m * 60_000
        p_frames = {
            "1": {
                "participantId": 1,
                "position": {"x": 8200, "y": 7900},
                "currentGold": 1850 if 11 <= m <= 14 else 450,
                "totalGold": m * 450,
                "level": min(18, 1 + (m // 2)),
                "minionsKilled": m * 6
            },
            "6": {
                "participantId": 6,
                "position": {"x": 7800, "y": 8100},
                "currentGold": 300,
                "totalGold": m * 520,
                "level": min(18, 1 + (m // 2)),
                "minionsKilled": m * 7
            }
        }

        events = []

        # Event 1: Minute 7 (07:12) Gank death without vision and with Flash held
        if m == 7:
            events.append({
                "type": "CHAMPION_KILL",
                "timestamp": 7 * 60_000 + 12_000,
                "killerId": 6,  # Syndra
                "victimId": 1,  # Ahri
                "assistingParticipantIds": [7],  # Jarvan IV
                "position": {"x": 8300, "y": 7800}
            })
            events.append({
                "type": "BUILDING_TURRET_PLATE_DESTROYED",
                "timestamp": 7 * 60_000 + 40_000,
                "killerId": 6
            })

        # Event 2: Minute 19 (19:30) Dragon taken by Red team while Ahri is top lane
        if m == 19:
            # Player is at top lane
            p_frames["1"]["position"] = {"x": 2200, "y": 12800}
            events.append({
                "type": "ELITE_MONSTER_KILL",
                "timestamp": 19 * 60_000 + 30_000,
                "killerId": 7,
                "killerTeamId": 200,
                "monsterType": "DRAGON",
                "monsterSubType": "FIRE_DRAGON",
                "position": {"x": 9800, "y": 4400}
            })

        frames.append({
            "timestamp": ts,
            "participantFrames": p_frames,
            "events": events
        })

    timeline_dto = {
        "metadata": {
            "matchId": "EUN1_SAMPLE_354129988"
        },
        "info": {
            "frameInterval": 60000,
            "frames": frames
        }
    }

    return match_dto, timeline_dto, SAMPLE_PUUID
