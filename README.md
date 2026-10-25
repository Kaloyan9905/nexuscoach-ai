# NexusCoach AI ⚔️ // Autonomous League of Legends Coach

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![Tailwind CSS](https://img.shields.io/badge/TailwindCSS-CDN-38B2AC.svg)](https://tailwindcss.com/)
[![Riot Games API](https://img.shields.io/badge/Riot%20Games-Match--v5-D4AF37.svg)](https://developer.riotgames.com/)

> **NexusCoach AI** is a post-game tactical coaching pipeline and dashboard designed specifically for solo laners (Mid & Top) in League of Legends. It extracts match timeline frames, calculates micro/macro vulnerability metrics with a deterministic mathematical rule engine, and provides automated client replay playback with camera tracking.

---

## ✨ Features

- **🎯 Deterministic Tactical Rule Engine**:
  - **Death Profiler**: Analyzes 1vN isolation, vision coverage in a 900-unit radius, held Flash cooldowns, and post-death tower plate losses.
  - **Objective Desynchronization**: Detects late rotations to Dragon/Baron clashes from 8,000+ units away during critical teamfight windows.
  - **Economic Tracking**: Identifies excessive gold hoarding (>1,500g unspent for >2 wave cycles) and early-game XP zoning gaps.

- **🎥 Smart League Client Replay Integration**:
  - **Auto-Launch Client**: If League of Legends is closed, NexusCoach directly starts `RiotClientServices.exe` and waits for login.
  - **-8s Situational Lead**: Seeks the replay 8 seconds prior to the error so you can see enemy rotations, river vision gaps, and flank angles.
  - **Persistent Camera Lock**: Automatically locks the spectator camera onto your player's champion via port 2999 (`/replay/render`), with burst synchronization during 3D loading screens.

- **💎 Minimalist Obsidian Dashboard**:
  - Deep obsidian void glassmorphic design (`#07080B`) with subtle prestige gold (`#D4AF37`) accents.
  - **Hero Match Banner**: Champion splash art ambient background, matchup display, KDA, CS/M, and one-click match replay trigger.
  - **Recent Matches Strip**: Horizontal pill switcher for recent solo queue games.
  - **Interactive 2D Tactical Replay Canvas**: Animated client-side canvas demonstrating movement paths, collapse countdowns, and vision ward coverage.
  - **Tactical Minimap Radar**: 512x512 official Summoner's Rift map with interactive pins and hover tooltips.
  - **Gold Velocity Chart**: Dual-curve economy tracker comparing player gold against the lane opponent.

- **🤖 Challenger LLM Synthesis**:
  - Compresses normalized timeline frames (<1,500 tokens) and generates structured high-elo coaching reviews.
  - Works offline with built-in rule synthesizer or online via Google Gemini.

---

## 🚀 Quick Start

### 1. Clone & Set Up Virtual Environment

```bash
git clone https://github.com/Kaloyan9905/nexuscoach-ai.git
cd nexuscoach-ai

python -m venv .venv
.\.venv\Scripts\activate   # On Windows
# or: source .venv/bin/activate on Linux/macOS

pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the root directory:

```env
RIOT_API_KEY=RGAPI-your-riot-api-key-here
GEMINI_API_KEY=your-gemini-api-key-optional
DEFAULT_REGION=eun1
```

### 3. Launch Web Dashboard

```bash
python -m nexuscoach.main --serve --port 8000
```
Open **`http://127.0.0.1:8000`** in your browser.

---

## 🛠️ CLI Commands

```bash
# Run unit & integration test suite (20 tests)
python -m unittest discover tests

# Launch web server with auto-reload
python -m nexuscoach.main --serve

# Run live coaching review from terminal
python -m nexuscoach.main --riot-id "GameName#Tag" --region "eun1"

# Run background client watcher daemon (auto-triggers coaching after every match)
python -m nexuscoach.main --watch-lcu

# Simulate an EndOfGame event
python -m nexuscoach.main --simulate-endgame
```

---

## 📁 Architecture Overview

```
nexuscoach-ai/
├── nexuscoach/
│   ├── ingestion/       # Riot Account-v1 & Match-v5 API client, cache layer
│   ├── engine/          # Deterministic geometry, death profiler, economy tracker, rule engine
│   ├── llm/             # Context normalizer, anti-hallucination prompt, Gemini synthesizer
│   ├── lcu/             # Local League Client lockfile connector, process launcher, replay controller
│   ├── report/          # Markdown and visual minimap generators
│   └── web/             # FastAPI backend & single-page minimalist dashboard
├── tests/               # Comprehensive automated test suite
├── agents.md            # Architecture documentation & source of truth
└── requirements.txt     # Python dependencies
```

---

## 🛡️ License

MIT License. Developed for competitive League of Legends analysis.
