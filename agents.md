# NexusCoach AI - Developer & Agent Documentation

> **Source of Truth** for NexusCoach AI architecture, data contracts, and implementation standards.

## 1. Project Overview
NexusCoach AI is an automated post-game coaching pipeline for League of Legends solo laners (Mid & Top). It consumes raw match and timeline data from Riot Games Match-v5 API, processes events through a deterministic, math-grounded Rule Engine, and synthesizes top actionable macro takeaways using an analytical LLM reasoning layer.

## 2. Directory Structure & Architecture
```
nexuscoach-ai/
├── .venv/                      # Isolated virtual environment
├── agents.md                   # Source of truth documentation (this file)
├── requirements.txt            # Python dependencies
├── .env.example                # Environment variables template
├── nexuscoach/
│   ├── __init__.py
│   ├── config.py               # Constants, region mappings, API configurations
│   ├── ingestion/
│   │   ├── __init__.py
│   │   ├── riot_client.py      # Riot Account-v1 & Match-v5 client with rate limiting & caching
│   │   └── cache.py            # Local disk cache for match JSON payloads
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── coordinates.py      # Summoner's Rift geometry & Euclidean distance helpers
│   │   ├── death_profiler.py   # Death context (1vN, vision in 90s, held flash)
│   │   ├── economy_tracker.py  # Gold hoarding (>1500g for >120s), XP/Level delta
│   │   ├── roam_analyzer.py    # Failed roams with lane loss quantification
│   │   ├── objective_sync.py   # Objective presence (T-45s..T-15s, TP readiness)
│   │   └── rule_engine.py      # Master orchestrator combining all deterministic checks
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── normalizer.py       # Compresses anomalies into concise JSON manifest (<1500 tokens)
│   │   ├── prompt.py           # Challenger persona & anti-hallucination prompt
│   │   └── synthesizer.py      # LLM reasoning layer with fallback offline rule synthesizer
│   ├── report/
│   │   ├── __init__.py
│   │   ├── formatter.py        # Markdown & Discord Embed formatter
│   │   └── minimap_renderer.py # Text-based 2D minimap visualizer of deaths & objectives
│   ├── lcu/
│   │   ├── __init__.py
│   │   ├── lockfile.py         # LeagueClient lockfile parser & credential extractor
│   │   ├── client.py           # Local LCU REST API client (Replay RPC with contextData, -8s situational lead & port 2999 camera lock)
│   │   └── watcher.py          # Background watcher detecting EndOfGame state transitions
│   ├── video/
│   │   ├── __init__.py
│   │   └── clipper.py          # Automated in-game video recording & Replay API config (game.cfg EnableReplayApi=1, /api/video/capture)
│   ├── desktop/
│   │   ├── __init__.py
│   │   └── overlay.py          # Native desktop window launcher via pywebview & Win32 docking
│   ├── web/
│   │   ├── __init__.py
│   │   ├── app.py              # FastAPI server (API endpoints + static dashboard serving)
│   │   └── static/
│   │       └── index.html      # Hextech dark interactive Single Page App (Built-in In-App Video & 2D Tactical Replay Canvas)
│   └── main.py                 # CLI entry point for processing games, daemon, and overlay
└── tests/
    ├── __init__.py
    ├── fixtures/
    │   └── sample_match.py     # Deterministic synthetic match & timeline for unit tests
    ├── test_rule_engine.py     # Unit test suite verifying all rule detectors
    ├── test_lcu_watcher.py     # Unit test suite for LCU lockfile parsing & watcher
    ├── test_api_and_features.py # Comprehensive integration suite (API contracts, video, coordinates)
    └── test_video_pipeline.py  # Full video test suite (HTTP streaming, range requests, WebM serving)
```

## 3. Data Contracts
### 3.1 Riot API Timeline Specifications
- Summoner's Rift bounds: $X \in [0, 16000]$, $Y \in [0, 16000]$.
- Standard vision radius: Ward = 900 units, Champion = 1350 units.
- Participant frame interval: 60,000 ms (1 minute).

### 3.2 Normalized Anomaly Manifest
The Rule Engine transforms raw timeline frames into a clean JSON manifest strictly under 1,500 tokens before feeding into the LLM Reasoning Layer.

## 4. Dependencies
- Python 3.13+
- `requests` (HTTP requests to Riot API & LLM endpoints)
- `python-dotenv` (Configuration & secret management)
- `fastapi` & `uvicorn` (Web Dashboard API & static server)
- `pywebview` (Native desktop overlay window)

## 5. Execution Commands
```bash
# Activate virtual environment
.\.venv\Scripts\activate

# Run automated unit tests
python -m unittest discover tests

# Launch Interactive Web Dashboard UI & API
python -m nexuscoach.main --serve

# Launch Native Desktop Overlay with automatic LCU detection
python -m nexuscoach.main --overlay

# Run background daemon that watches local League client for match finishes
python -m nexuscoach.main --watch-lcu

# Simulate an EndOfGame event to test the complete auto-trigger pipeline
python -m nexuscoach.main --simulate-endgame

# Run live CLI review on your latest game
python -m nexuscoach.main --riot-id "GameName#Tag" --region "eun1" --api-key "RGAPI-..."
```

## 6. Minimalist UI/UX & Replay Architecture
### 6.1 Obsidian Glassmorphism UI
- **Design Tokens**: Obsidian void (`#07080B`), subtle border transparency (`border-white/[0.06]`), prestige gold accents (`#D4AF37`), and clean status badges (emerald for tempo, rose for fatal ganks/deaths).
- **Match History Strip**: Compact horizontal match selector fetching directly from `/api/history` with one-click analysis.
- **Cinematic Hero**: Champion splash art background with linear gradient fade, matchup header (`vs Opponent`), KPI stat cards (KDA, CS/M, Deaths, Anomalies), and a hero replay trigger.
- **Client Playback Focus**: In-app video/clip streaming feature has been removed from the UI. Playback is handled exclusively via the official League Client replay engine.
- **Interactive 2D Tactical Canvas**: Client-side animated canvas reconstructing the gank/collapse sequence, movement vectors, vision ward radius, countdown timer (`T-3.0s until collapse`), and fatal impact wave.
- **Summoner's Rift Radar**: 512x512 canvas drawing the official satellite texture with interactive hover tooltips and one-click pin focus.
- **Economic Velocity Chart**: Dual-line canvas plotting player gold vs opponent gold with death event markers.

### 6.2 In-Game Replay Lead Time & Persistent Camera Lock
- **Lead Time Buffer**: Configured to `-8.0s` before the fatal error to give the summoner situational awareness of enemy rotations and missing laners.
- **Automatic Camera Lock**: Every time a replay is triggered (from hero banner or individual cards), the camera is automatically locked to the player's champion (`selectionName: champion_name, cameraAttached: True`).
- **Burst Retries**: A background thread dispatches repeated lock commands during 3D engine startup to prevent League's initial fountain camera sweep from detaching the player lock.
- **LCU API Integration**: Calls `POST https://127.0.0.1:2999/replay/playback` for time seeking and `POST https://127.0.0.1:2999/replay/render` for champion camera locking.

