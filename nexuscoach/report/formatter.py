"""Report formatting utilities for console output, Markdown export, and Discord Webhooks."""

from pathlib import Path
from typing import Any, Dict
from nexuscoach.report.minimap_renderer import render_ascii_minimap

REPORTS_DIR = Path("reports")

def generate_full_markdown_report(analysis_data: Dict[str, Any], review_text: str) -> str:
    """Combine metadata, ASCII minimap, and coaching review into a complete Markdown document."""
    meta = analysis_data.get("metadata", {})
    deaths = [a for a in analysis_data.get("top_anomalies", []) if a.get("type") == "DEATH_ANALYSIS"]
    minimap_ascii = render_ascii_minimap(deaths)

    report_lines = [
        f"# 🏆 NexusCoach AI Post-Game Review",
        f"**Match ID:** `{meta.get('matchId')}` | **Duration:** {meta.get('duration')} | **Result:** **{meta.get('result')}**",
        f"**Champion:** {meta.get('userChampion')} ({meta.get('role')}) vs {meta.get('opponentChampion')}",
        f"**KDA:** {meta.get('kda')} | **CS:** {meta.get('cs')} ({meta.get('cs_per_min')} CS/min)",
        "",
        "## 🗺️ Карта на инцидентите (Death Locations & Objective Points)",
        "```text",
        minimap_ascii,
        "```",
        "",
        "## 🎯 Тактически анализ на треньора",
        review_text,
        "",
        "---",
        "*Генерирано автоматично от NexusCoach AI - Детерминистичен анализ без халюцинации.*"
    ]

    return "\n".join(report_lines)

def save_report_to_disk(match_id: str, markdown_content: str) -> Path:
    """Save the final markdown report into the reports directory."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = match_id.replace("/", "_").replace("\\", "_")
    report_path = REPORTS_DIR / f"report_{safe_name}.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(markdown_content)
    return report_path
