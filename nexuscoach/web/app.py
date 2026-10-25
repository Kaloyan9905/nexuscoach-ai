"""FastAPI Web Server for NexusCoach AI Interactive Dashboard."""

import os
from pathlib import Path
from typing import Any, Dict, Optional
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from nexuscoach.config import resolve_regional_route
from nexuscoach.ingestion.cache import MatchCache
from nexuscoach.ingestion.riot_client import RiotClient, RiotAPIError
from nexuscoach.engine.rule_engine import RuleEngine
from nexuscoach.llm.synthesizer import CoachingSynthesizer
from tests.fixtures.sample_match import get_sample_match_data

load_dotenv()

app = FastAPI(title="NexusCoach AI Dashboard", version="1.0.0")

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

cache = MatchCache()

STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
VIDEOS_DIR = STATIC_DIR / "videos"
VIDEOS_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static/videos", StaticFiles(directory=VIDEOS_DIR), name="videos")

@app.get("/", response_class=HTMLResponse)
def get_index():
    """Serve the single-page dashboard HTML."""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        with open(index_file, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>NexusCoach AI Dashboard is building...</h1>"

@app.get("/api/status")
def get_status():
    """Return backend status and API key configuration state."""
    has_riot_key = bool(os.getenv("RIOT_API_KEY"))
    has_gemini_key = bool(os.getenv("GEMINI_API_KEY"))
    return {
        "status": "online",
        "has_riot_key": has_riot_key,
        "has_gemini_key": has_gemini_key
    }

@app.get("/api/cached")
def get_cached_matches():
    """List locally cached matches for instant viewing."""
    matches = []
    for file in cache.cache_dir.glob("*_match.json"):
        try:
            match_id = file.stem.replace("_match", "")
            match_data = cache.get_match(match_id)
            if match_data:
                info = match_data.get("info", {})
                participants = info.get("participants", [])
                p0 = participants[0] if participants else {}
                matches.append({
                    "matchId": match_id,
                    "durationSeconds": info.get("gameDuration", 0),
                    "gameMode": info.get("gameMode", "CLASSIC"),
                    "participantsCount": len(participants),
                    "samplePlayer": f"{p0.get('riotIdGameName', '')}#{p0.get('riotIdTagline', '')}"
                })
        except Exception:
            continue
    return {"matches": matches}

@app.get("/api/history")
def get_match_history(
    riot_id: str = Query("stream#cls63", description="GameName#TagLine"),
    region: str = Query("eun1", description="Region code"),
    count: int = Query(5, description="Number of matches")
):
    """Fetch summaries of recent matches for quick switching in the UI."""
    api_key = os.getenv("RIOT_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(status_code=400, detail="RIOT_API_KEY is missing.")

    regional_route = resolve_regional_route(region)
    client = RiotClient(api_key=api_key, cache=cache)

    try:
        if "#" not in riot_id:
            raise HTTPException(status_code=400, detail="Riot ID must include '#'")
        name, tag = riot_id.split("#", 1)
        puuid = client.get_puuid_by_riot_id(name, tag, regional_route=regional_route)
        match_ids = client.get_recent_match_ids(puuid, regional_route=regional_route, count=count)

        history = []
        for m_id in match_ids:
            try:
                m_data = client.get_match_details(m_id, regional_route=regional_route)
                info = m_data.get("info", {})
                participants = info.get("participants", [])

                player_p = None
                opp_p = None
                for p in participants:
                    if p.get("puuid") == puuid:
                        player_p = p
                        break

                if player_p:
                    role = player_p.get("teamPosition") or "MIDDLE"
                    for p in participants:
                        if p.get("teamId") != player_p.get("teamId") and p.get("teamPosition") == role:
                            opp_p = p
                            break

                    game_duration_sec = info.get("gameDuration", 0)
                    m = game_duration_sec // 60
                    s = game_duration_sec % 60
                    history.append({
                        "matchId": m_id,
                        "champion": player_p.get("championName", "Unknown"),
                        "opponent": opp_p.get("championName", "Unknown") if opp_p else "Unknown",
                        "role": role,
                        "result": "Victory" if player_p.get("win") else "Defeat",
                        "kda": f"{player_p.get('kills', 0)}/{player_p.get('deaths', 0)}/{player_p.get('assists', 0)}",
                        "duration": f"{m:02d}:{s:02d}"
                    })
            except Exception:
                continue

        return {"history": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/replay/watch")
def watch_replay(
    match_id: str,
    time_seconds: Optional[float] = 0.0,
    lead_seconds: float = 8.0,
    champion_name: Optional[str] = None,
    x: Optional[float] = None,
    y: Optional[float] = None
):
    """Launch the League game client in replay mode, seek 5-10s before error, and lock camera to player."""
    from nexuscoach.lcu.client import LCUClient
    import threading
    import time
    lcu = LCUClient()

    actual_time = float(time_seconds or 0.0)
    # Calculate situational awareness start time (default 8s before the incident)
    seek_time = max(0.0, actual_time - lead_seconds)
    seek_m = int(seek_time // 60)
    seek_s = int(seek_time % 60)
    err_m = int(actual_time // 60)
    err_s = int(actual_time % 60)

    # Automatically resolve champion_name if not provided
    if not champion_name:
        clean_id = match_id.split("_")[-1] if "_" in match_id else match_id
        cached_match = cache.get_match(match_id) or cache.get_match(clean_id)
        if cached_match:
            participants = cached_match.get("info", {}).get("participants", [])
            for p in participants:
                if p.get("riotIdGameName", "").lower() in ["stream", "cls63"]:
                    champion_name = p.get("championName")
                    break
            if not champion_name and participants:
                champion_name = participants[0].get("championName")

    def lock_camera_burst(repeats: int = 6, delay: float = 0.4):
        """Send camera lock commands repeatedly to ensure camera binds firmly during scene loading."""
        for _ in range(repeats):
            time.sleep(delay)
            lcu.set_replay_camera(champion_name=champion_name, x=x, y=y, camera_attached=True)

    cam_desc = f"camera locked on {champion_name}" if champion_name else "camera locked on player"

    # 1. If in-game replay is already running on port 2999, seek directly & lock camera!
    if lcu.seek_replay_time(seek_time):
        lcu.set_replay_camera(champion_name=champion_name, x=x, y=y, camera_attached=True)
        threading.Thread(target=lock_camera_burst, args=(4, 0.3), daemon=True).start()
        return {
            "success": True,
            "message": f"Jumped to [{seek_m:02d}:{seek_s:02d}] (-{int(lead_seconds)}s before error at {err_m:02d}:{err_s:02d}) • {cam_desc}!"
        }

    # 2. Check if desktop client is open; if not, launch it directly!
    if not lcu.is_client_running():
        started = lcu.start_league_client()
        if not started:
            return {
                "success": False,
                "message": "League of Legends client could not be located on your system. Please launch League manually."
            }

        # Spawn background thread to wait for the client to boot, then trigger replay launch and camera lock
        def wait_for_client_and_launch():
            for _ in range(60):
                time.sleep(1.5)
                if lcu.is_client_running():
                    time.sleep(2.0)
                    if lcu.launch_replay(match_id):
                        for _ in range(45):
                            time.sleep(1.5)
                            if lcu.seek_replay_time(seek_time):
                                lock_camera_burst(repeats=8, delay=0.5)
                                break
                    break

        threading.Thread(target=wait_for_client_and_launch, daemon=True).start()

        return {
            "success": True,
            "message": f"Launching League of Legends Client... Replay will automatically open at [{seek_m:02d}:{seek_s:02d}] (-{int(lead_seconds)}s lead) • {cam_desc}!"
        }

    # 3. Request launch via LCU
    launched = lcu.launch_replay(match_id)
    if launched:
        def seek_when_ready():
            for _ in range(45):
                time.sleep(1.5)
                if lcu.seek_replay_time(seek_time):
                    lock_camera_burst(repeats=8, delay=0.5)
                    break
        threading.Thread(target=seek_when_ready, daemon=True).start()

    return {
        "success": launched,
        "message": f"Replay opening at [{seek_m:02d}:{seek_s:02d}] (-{int(lead_seconds)}s lead) • {cam_desc}!" if launched else "Could not trigger replay in League Client."
    }

@app.get("/api/video/status")
def get_video_clip_status(match_id: str, timestamp: str):
    """Check if a rendered video clip exists for this error."""
    from nexuscoach.video.clipper import VideoClipper
    clipper = VideoClipper()
    exists = clipper.clip_exists(match_id, timestamp)
    clip_filename = f"{match_id.replace('/', '_').replace('\\', '_')}_{timestamp.replace(':', '_')}.webm"
    return {
        "exists": exists,
        "video_url": f"/static/videos/{clip_filename}" if exists else None
    }

@app.post("/api/video/capture")
def capture_video_clip(match_id: str, timestamp: str, time_seconds: float):
    """Trigger background capture of a 15-second replay clip using Riot's Replay API."""
    from nexuscoach.video.clipper import VideoClipper
    clipper = VideoClipper()
    result = clipper.capture_clip_async(match_id, timestamp, time_seconds)
    return result

@app.get("/api/demo")
def get_demo_analysis():
    """Return instant coaching analysis on synthetic fixture without network calls."""
    sample_match, sample_timeline, sample_puuid = get_sample_match_data()
    engine = RuleEngine(sample_match, sample_timeline, sample_puuid)
    analysis = engine.run_analysis()
    synthesizer = CoachingSynthesizer()
    review = synthesizer.generate_review(analysis)
    return {
        "analysis": analysis,
        "review": review,
        "is_demo": True
    }

@app.get("/api/analyze")
def analyze_match(
    riot_id: Optional[str] = None,
    region: str = "eun1",
    match_id: Optional[str] = None
):
    """Run full coaching pipeline for given player or match."""
    api_key = os.getenv("RIOT_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(
            status_code=400,
            detail="RIOT_API_KEY is missing. Add it to .env or set the environment variable."
        )

    regional_route = resolve_regional_route(region)
    client = RiotClient(api_key=api_key, cache=cache)
    target_puuid = None

    try:
        if riot_id and isinstance(riot_id, str):
            if "#" not in riot_id:
                raise HTTPException(status_code=400, detail="Riot ID must include '#' (e.g. 'stream#cls63')")
            name, tag = riot_id.split("#", 1)
            target_puuid = client.get_puuid_by_riot_id(name, tag, regional_route=regional_route)

            if not match_id:
                recent = client.get_recent_match_ids(target_puuid, regional_route=regional_route, count=1)
                if not recent:
                    raise HTTPException(status_code=404, detail="No recent matches found for this Riot ID.")
                match_id = recent[0]

        if not match_id:
            raise HTTPException(status_code=400, detail="Must provide either riot_id or match_id.")

        match_dto = client.get_match_details(match_id, regional_route=regional_route)
        timeline_dto = client.get_match_timeline(match_id, regional_route=regional_route)

        if not target_puuid:
            target_puuid = match_dto.get("info", {}).get("participants", [{}])[0].get("puuid", "")

        engine = RuleEngine(match_dto, timeline_dto, target_puuid)
        analysis = engine.run_analysis()

        synthesizer = CoachingSynthesizer()
        review = synthesizer.generate_review(analysis)

        return {
            "analysis": analysis,
            "review": review,
            "is_demo": False
        }

    except RiotAPIError as e:
        raise HTTPException(status_code=e.status_code or 500, detail=e.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
