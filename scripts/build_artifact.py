"""Script to build the standalone preloaded dashboard HTML artifact."""

import json
from pathlib import Path
from nexuscoach.web.app import analyze_match, get_match_history

def main():
    print("Generating preloaded dashboard artifact...")
    # Fetch data for user's recent games
    history_resp = get_match_history("stream#cls63", "eun1", 5)
    history = history_resp.get("history", [])

    preloaded_matches = {}
    for h in history[:3]:
        m_id = h["matchId"]
        try:
            res = analyze_match(riot_id="stream#cls63", match_id=m_id, region="eun1")
            preloaded_matches[m_id] = res["analysis"]
            print(f"  -> Preloaded {m_id} ({h['champion']} vs {h['opponent']})")
        except Exception as e:
            print(f"  -> Could not preload {m_id}: {e}")

    # Read base index.html
    static_file = Path("nexuscoach/web/static/index.html")
    with open(static_file, "r", encoding="utf-8") as f:
        html = f.read()

    injection = (
        "<script>\n"
        f"window.PRELOADED_HISTORY = {json.dumps(history)};\n"
        f"window.PRELOADED_MATCHES = {json.dumps(preloaded_matches)};\n"
        "</script>\n"
    )

    full_html = html.replace("</head>", injection + "</head>")

    target_artifact = Path("C:/Users/Kaloyan Milchev/.gemini/antigravity/brain/0ebc2576-ef4f-4429-80b6-f1fd6dbe19c8/nexuscoach_dashboard.html")
    with open(target_artifact, "w", encoding="utf-8") as f:
        f.write(full_html)

    print(f"Artifact successfully generated at: {target_artifact}")

if __name__ == "__main__":
    main()
