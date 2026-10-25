"""Geometric calculations and spatial zone mapping for Summoner's Rift."""

import math
from typing import Any, Dict, Tuple

def euclidean_distance(p1: Dict[str, Any], p2: Dict[str, Any]) -> float:
    """Calculate 2D Euclidean distance between two points with 'x' and 'y' keys."""
    x1, y1 = float(p1.get("x", 0)), float(p1.get("y", 0))
    x2, y2 = float(p2.get("x", 0)), float(p2.get("y", 0))
    return math.hypot(x2 - x1, y2 - y1)

def ms_to_timestamp(ms: int) -> str:
    """Convert millisecond game time to formatted string MM:SS."""
    total_seconds = max(0, int(ms / 1000))
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes:02d}:{seconds:02d}"

def is_point_in_radius(center: Tuple[int, int], target: Dict[str, Any], radius: float) -> bool:
    """Check if target point lies within radius of given center (x, y)."""
    tx, ty = float(target.get("x", 0)), float(target.get("y", 0))
    return math.hypot(tx - center[0], ty - center[1]) <= radius

def classify_map_zone(x: float, y: float) -> str:
    """Classify (x, y) coordinates into Summoner's Rift zones."""
    # Fountain / Bases
    if x < 2000 and y < 2000:
        return "BLUE_BASE"
    if x > 14000 and y > 14000:
        return "RED_BASE"

    # River & Pits
    if math.hypot(x - 9800, y - 4400) < 1800:
        return "DRAGON_PIT"
    if math.hypot(x - 4900, y - 10400) < 1800:
        return "BARON_PIT"

    # Mid Lane (approximate diagonal band: x - y is close to 0)
    # The line y = x runs straight through mid lane.
    dist_to_mid_diagonal = abs(x - y) / math.sqrt(2)
    if dist_to_mid_diagonal < 1600 and 3000 <= x <= 13000:
        return "MID_LANE"

    # Top Lane (runs along upper-left border: small x, large y)
    if x < 4000 or y > 12000:
        return "TOP_LANE"

    # Bot Lane (runs along lower-right border: large x, small y)
    if x > 12000 or y < 4000:
        return "BOT_LANE"

    # Jungles / River
    if y > x:
        return "TOP_RIVER_JUNGLE"
    else:
        return "BOT_RIVER_JUNGLE"
