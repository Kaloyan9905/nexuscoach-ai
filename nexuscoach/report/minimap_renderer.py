"""Summoner's Rift ASCII Minimap Renderer: Visualizes death coordinates and objectives."""

from typing import Any, Dict, List

MAP_WIDTH = 25
MAP_HEIGHT = 25

def render_ascii_minimap(deaths: List[Dict[str, Any]]) -> str:
    """Render a 25x25 ASCII minimap of Summoner's Rift with death markers."""
    # Create empty grid
    grid = [["." for _ in range(MAP_WIDTH)] for _ in range(MAP_HEIGHT)]

    # Draw diagonal mid lane
    for i in range(min(MAP_WIDTH, MAP_HEIGHT)):
        grid[MAP_HEIGHT - 1 - i][i] = "·"

    # Bases
    grid[MAP_HEIGHT - 1][0] = "B"  # Blue base bottom-left
    grid[0][MAP_WIDTH - 1] = "R"   # Red base top-right

    # Pits
    # Dragon pit: ~ (9800, 4400) -> x=15, y=7
    d_x = int(9800 / 16000 * (MAP_WIDTH - 1))
    d_y = MAP_HEIGHT - 1 - int(4400 / 16000 * (MAP_HEIGHT - 1))
    grid[d_y][d_x] = "D"

    # Baron pit: ~ (4900, 10400) -> x=7, y=16
    b_x = int(4900 / 16000 * (MAP_WIDTH - 1))
    b_y = MAP_HEIGHT - 1 - int(10400 / 16000 * (MAP_HEIGHT - 1))
    grid[b_y][b_x] = "Ω"

    # Place death markers
    for idx, d in enumerate(deaths[:5], 1):
        pos = d.get("position", {})
        x = pos.get("x", 8000)
        y = pos.get("y", 8000)
        gx = max(0, min(MAP_WIDTH - 1, int(x / 16000 * (MAP_WIDTH - 1))))
        gy = max(0, min(MAP_HEIGHT - 1, MAP_HEIGHT - 1 - int(y / 16000 * (MAP_HEIGHT - 1))))
        grid[gy][gx] = str(idx)

    lines = ["+-------------------------+  LEGEND:"]
    lines.append("|" + "".join(grid[0]) + "|  B: Blue Fountain  R: Red Fountain")
    lines.append("|" + "".join(grid[1]) + "|  Ω: Baron Pit      D: Dragon Pit")
    lines.append("|" + "".join(grid[2]) + "|  1..5: Death Locations")
    for r in range(3, MAP_HEIGHT):
        lines.append("|" + "".join(grid[r]) + "|")
    lines.append("+-------------------------+")
    return "\n".join(lines)
