"""Configuration constants and region mappings for NexusCoach AI."""

from typing import Dict, Tuple

# Summoner's Rift Map Bounds & Landmarks (0 to 16000)
MAP_MIN = 0
MAP_MAX = 16000
MID_CENTER = (8000, 8000)
BARON_PIT = (4900, 10400)
DRAGON_PIT = (9800, 4400)
BLUE_FOUNTAIN = (400, 400)
RED_FOUNTAIN = (15600, 15600)

# Detection Thresholds
DANGER_DISTANCE = 1500.0          # Distance to consider enemies "involved" in collapse
VISION_PROXIMITY_RADIUS = 1800.0  # Max distance to consider a ward providing vision
VISION_EXPIRY_MS = 90_000         # 90 seconds ward relevance window
GOLD_HOARDING_THRESHOLD = 1500    # Unspent gold threshold
GOLD_HOARDING_DURATION_MS = 120_000  # 120 seconds holding threshold
FAILED_ROAM_MIN_DURATION_MS = 30_000 # 30 seconds away from lane
OBJECTIVE_PRE_SPAWN_START_MS = 45_000 # T-45s before objective
OBJECTIVE_PRE_SPAWN_END_MS = 15_000   # T-15s before objective

# Platform to Regional Routing Mappings for Riot API
PLATFORM_TO_REGION: Dict[str, str] = {
    # Europe
    "eun1": "europe",
    "euw1": "europe",
    "tr1": "europe",
    "ru": "europe",
    # Americas
    "na1": "americas",
    "br1": "americas",
    "la1": "americas",
    "la2": "americas",
    # Asia
    "kr": "asia",
    "jp1": "asia",
    # SEA
    "oc1": "sea",
    "ph2": "sea",
    "sg2": "sea",
    "th2": "sea",
    "tw2": "sea",
    "vn2": "sea",
}

def resolve_regional_route(platform_id: str) -> str:
    """Resolve regional routing value (e.g. eun1 -> europe)."""
    norm = platform_id.lower().strip()
    return PLATFORM_TO_REGION.get(norm, "europe")
