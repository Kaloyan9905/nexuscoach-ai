"""NexusCoach AI CLI: Main Entry Point."""

import argparse
import io
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Ensure safe UTF-8 output on Windows consoles
if sys.platform == "win32":
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "buffer"):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from nexuscoach.config import resolve_regional_route
from nexuscoach.ingestion.riot_client import RiotClient, RiotAPIError
from nexuscoach.engine.rule_engine import RuleEngine
from nexuscoach.llm.synthesizer import CoachingSynthesizer
from nexuscoach.report.formatter import generate_full_markdown_report, save_report_to_disk
from tests.fixtures.sample_match import get_sample_match_data

def parse_args():
    parser = argparse.ArgumentParser(description="NexusCoach AI: Automated Post-Game Solo Lane Coach")
    parser.add_argument("--riot-id", type=str, help="Riot ID in format GameName#TagLine (e.g. 'Faker#KR1')")
    parser.add_argument("--region", type=str, default="eun1", help="Platform region (e.g. eun1, euw1, na1). Default: eun1")
    parser.add_argument("--match-id", type=str, help="Direct Match ID (e.g. 'EUN1_3498123456')")
    parser.add_argument("--api-key", type=str, help="Riot API Key (or set RIOT_API_KEY env)")
    parser.add_argument("--gemini-key", type=str, help="Gemini API Key (or set GEMINI_API_KEY env)")
    parser.add_argument("--test", action="store_true", help="Run end-to-end test on synthetic sample game without external API")
    parser.add_argument("--serve", action="store_true", help="Launch interactive Web Dashboard UI & API server")
    parser.add_argument("--port", type=int, default=8000, help="Port for the Web Dashboard server (default: 8000)")
    parser.add_argument("--overlay", action="store_true", help="Launch native Desktop Window overlay with automatic LCU match detection")
    parser.add_argument("--watch-lcu", action="store_true", help="Run background daemon that monitors League Client Update for match completions")
    parser.add_argument("--simulate-endgame", action="store_true", help="Simulate an LCU EndOfGame transition and test auto-review pipeline")
    return parser.parse_args()

def run_pipeline(match_dto: dict, timeline_dto: dict, target_puuid: str, gemini_key: str = None) -> str:
    """Run the complete Rule Engine -> LLM Synthesizer -> Report Generation pipeline."""
    print("[1/3] ⚙️  Running Deterministic Rule Engine...")
    engine = RuleEngine(match_dto, timeline_dto, target_puuid)
    analysis = engine.run_analysis()

    if "error" in analysis:
        raise RuntimeError(f"Analysis failed: {analysis['error']}")

    print(f"      -> Detected {analysis['total_anomalies_detected']} total events. Filtered to Top {len(analysis['top_anomalies'])} critical macro deviations.")

    print("[2/3] 🧠 Synthesizing Challenger Coach Takeaways...")
    synthesizer = CoachingSynthesizer(gemini_api_key=gemini_key)
    review_text = synthesizer.generate_review(analysis)

    print("[3/3] 📊 Generating Final Post-Game Report...")
    full_report = generate_full_markdown_report(analysis, review_text)
    report_path = save_report_to_disk(analysis["metadata"]["matchId"], full_report)
    print(f"      -> Report saved to: {report_path.resolve()}\n")

    return full_report

def main():
    load_dotenv()
    args = parse_args()

    # Mode 0: Web Dashboard Server Mode
    if args.serve:
        import uvicorn
        print("\n=======================================================")
        print("  🌐 NexusCoach AI: Starting Web Dashboard UI")
        print(f"  👉 Open your browser at: http://127.0.0.1:{args.port}")
        print("=======================================================\n")
        uvicorn.run("nexuscoach.web.app:app", host="127.0.0.1", port=args.port, reload=False)
        return

    # Mode 1: Self-contained Test Mode
    if args.test:
        print("\n=======================================================")
        print("  🚀 NexusCoach AI: Running Synthetic Fixture Test")
        print("=======================================================\n")
        sample_match, sample_timeline, sample_puuid = get_sample_match_data()
        report = run_pipeline(sample_match, sample_timeline, sample_puuid, gemini_key=args.gemini_key)
        print(report)
        print("\n✅ Test completed successfully!")
        return

    # Mode 1.5: LCU Simulation Mode
    if args.simulate_endgame:
        from nexuscoach.lcu.watcher import LCUWatcher
        print("\n=======================================================")
        print("  🧪 NexusCoach AI: Simulating LCU EndOfGame Event")
        print("=======================================================\n")

        api_key = args.api_key or os.getenv("RIOT_API_KEY")
        client = RiotClient(api_key=api_key)
        riot_id = args.riot_id or "stream#cls63"
        name, tag = riot_id.split("#", 1)
        p = client.get_puuid_by_riot_id(name, tag, regional_route=resolve_regional_route(args.region))
        recent = client.get_recent_match_ids(p, regional_route=resolve_regional_route(args.region), count=1)
        m_id = recent[0]

        def on_simulated_end():
            print(f"📥 [Auto-Pipeline] Downloading Match Details & Timeline for {m_id}...")
            m_dto = client.get_match_details(m_id, regional_route=resolve_regional_route(args.region))
            t_dto = client.get_match_timeline(m_id, regional_route=resolve_regional_route(args.region))
            run_pipeline(m_dto, t_dto, p)

        watcher = LCUWatcher(on_match_end=on_simulated_end)
        watcher.simulate_match_end()
        print("✅ LCU Simulation verified successfully!")
        return

    # Mode 1.6: Background LCU Watcher Daemon
    if args.watch_lcu:
        from nexuscoach.lcu.watcher import LCUWatcher
        from nexuscoach.lcu.client import LCUClient
        import time

        print("\n=======================================================")
        print("  👀 NexusCoach AI: LCU Matchflow Daemon Active")
        print("  Waiting for League of Legends game completion...")
        print("=======================================================\n")

        api_key = args.api_key or os.getenv("RIOT_API_KEY")
        if not api_key:
            print("❌ Error: RIOT_API_KEY is required in .env")
            sys.exit(1)

        client = RiotClient(api_key=api_key)
        riot_id = args.riot_id or "stream#cls63"
        name, tag = riot_id.split("#", 1)
        regional_route = resolve_regional_route(args.region)
        p = client.get_puuid_by_riot_id(name, tag, regional_route=regional_route)

        def on_game_ended():
            print("\n🏆 Match ended! Pulling latest game from Riot API...")
            time.sleep(3) # Give Riot server a moment to finalize
            recent = client.get_recent_match_ids(p, regional_route=regional_route, count=1)
            if recent:
                m_id = recent[0]
                m_dto = client.get_match_details(m_id, regional_route=regional_route)
                t_dto = client.get_match_timeline(m_id, regional_route=regional_route)
                run_pipeline(m_dto, t_dto, p)

        watcher = LCUWatcher(on_match_end=on_game_ended, poll_interval=2.0)
        watcher.start()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            watcher.stop()
            print("🛑 LCU Watcher stopped.")
        return

    # Mode 1.7: Native Desktop Window Overlay
    if args.overlay:
        from nexuscoach.desktop.overlay import launch_overlay_window
        import threading
        import time
        import urllib.request

        # Ensure server is running
        def is_server_up():
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{args.port}/api/status", timeout=1)
                return True
            except Exception:
                return False

        if not is_server_up():
            import uvicorn
            print(f"🚀 Starting background web server on port {args.port}...")
            server_thread = threading.Thread(
                target=lambda: uvicorn.run("nexuscoach.web.app:app", host="127.0.0.1", port=args.port, log_level="warning"),
                daemon=True
            )
            server_thread.start()
            time.sleep(1.5)

        launch_overlay_window(url=f"http://127.0.0.1:{args.port}")
        return

    # Mode 2: Live Game Review
    api_key = args.api_key or os.getenv("RIOT_API_KEY")
    if not api_key:
        print("❌ Error: Riot API Key is required. Provide --api-key or set RIOT_API_KEY in .env")
        print("   Get a free developer key at: https://developer.riotgames.com")
        print("   Or run self-test with: python -m nexuscoach.main --test")
        sys.exit(1)

    gemini_key = args.gemini_key or os.getenv("GEMINI_API_KEY")
    regional_route = resolve_regional_route(args.region)
    client = RiotClient(api_key=api_key)

    match_id = args.match_id
    target_puuid = None

    try:
        if args.riot_id:
            if "#" not in args.riot_id:
                print("❌ Error: --riot-id must include a tag line (e.g. 'Player#EUN1')")
                sys.exit(1)
            name, tag = args.riot_id.split("#", 1)
            print(f"🔍 Looking up Riot ID: {name}#{tag} on region '{regional_route}'...")
            target_puuid = client.get_puuid_by_riot_id(name, tag, regional_route=regional_route)
            print(f"   -> PUUID: {target_puuid}")

            if not match_id:
                print(f"📥 Fetching latest match ID for player...")
                recent_matches = client.get_recent_match_ids(target_puuid, regional_route=regional_route, count=1)
                if not recent_matches:
                    print("❌ No recent matches found for this account.")
                    sys.exit(1)
                match_id = recent_matches[0]
                print(f"   -> Latest Match ID: {match_id}")

        if not match_id:
            print("❌ Error: Must specify either --riot-id or --match-id")
            sys.exit(1)

        print(f"📥 Downloading Match Details & Timeline for {match_id}...")
        match_dto = client.get_match_details(match_id, regional_route=regional_route)
        timeline_dto = client.get_match_timeline(match_id, regional_route=regional_route)

        if not target_puuid:
            # Fallback to first participant
            target_puuid = match_dto.get("info", {}).get("participants", [{}])[0].get("puuid", "")

        print("\n=======================================================")
        print(f"  ⚔️  NexusCoach AI: Analyzing Match {match_id}")
        print("=======================================================\n")
        report = run_pipeline(match_dto, timeline_dto, target_puuid, gemini_key=gemini_key)
        print(report)
        print("\n✅ Coaching analysis delivered successfully!")

    except RiotAPIError as e:
        print(f"\n❌ Riot API Error: {e.message}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
