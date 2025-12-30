# AI Village v4 - Starship Voyager Edition

A Star Trek Voyager-inspired multi-agent system where different LLMs act as starship officers solving episodic challenges, with human crew voting on leadership and strict safety protocols ensuring no harm to humans.

## Overview

Transform the AI Village platform into an episodic system where:
- **7 LLM Officers** (Captain, First Officer, Chief Engineer, Science Officer, Medical Officer, Security Chief, Communications Officer) collaborate to solve challenges
- **Episodic Structure** - Each episode presents a unique scenario that officers must solve
- **Human Voting** - Humans vote on critical decisions and weekly leadership elections
- **Safety Protocols** - Prime Directive enforcement ensures no harm to human crew
- **Real-time Bridge** - WebSocket streaming for live officer discussions

## Architecture

```
┌─────────────────────────────────────────┐
│         USS AI VILLAGE                  │
│                                         │
│  👤 Captain (Elected by humans)         │
│  ├── 🤖 First Officer                   │
│  ├── 🤖 Chief Engineer                  │
│  ├── 🤖 Science Officer                 │
│  ├── 🤖 Medical Officer                 │
│  ├── 🤖 Security Chief                  │
│  └── 🤖 Communications Officer          │
│                                         │
│  👥 Human Crew (Voters/Observers)       │
└─────────────────────────────────────────┘
```

## Episode Flow

1. **Situation Briefing** - Scenario presented to officers
2. **Bridge Discussion** - 3 rounds of officer collaboration:
   - Round 1: Initial analysis
   - Round 2: Critique and debate
   - Round 3: Consensus building
3. **Captain Decision** - Final decision (or human vote if high risk)
4. **Mission Execution** - Decision implemented
5. **Outcome Review** - Success/failure assessment
6. **Captain's Log** - Episode summary and lessons learned

## Tech Stack

- **Backend**: FastAPI, Uvicorn, WebSockets, SQLite
- **Frontend**: React 18, Vite
- **LLM**: Ollama (local or remote via Cloudflare tunnel)
- **Database**: SQLite with async support

## Quick Start

### 1. Backend Setup

```bash
cd ai-village-v4/backend
pip install -r requirements.txt
python main.py
```

### 2. Frontend Setup

```bash
cd ai-village-v4/frontend
npm install
npm run dev
```

### 3. Configure LLM Endpoint

Edit `backend/config.py`:
```python
LLM_MODE = "remote"  # or "local"
REMOTE_OLLAMA_URL = "https://your-url.trycloudflare.com"
```

### 4. Open the App

Navigate to http://localhost:5173

## Project Structure

```
ai-village-v4/
├── backend/
│   ├── main.py              # FastAPI server + WebSocket
│   ├── config.py            # Officer model assignments
│   ├── database.py          # Database schema and operations
│   ├── llm.py               # Ollama API wrapper
│   ├── episode.py           # Episode engine
│   ├── scenario_generator.py # AI scenario generation
│   ├── safety.py            # Safety protocol system
│   ├── voting.py            # Voting and elections
│   └── officers/
│       ├── officer.py       # Base officer class
│       ├── captain.py       # Captain role
│       ├── first_officer.py # First Officer role
│       ├── engineer.py      # Chief Engineer role
│       ├── science.py       # Science Officer role
│       ├── medical.py       # Medical Officer role
│       ├── security.py      # Security Chief role
│       └── comms.py         # Communications Officer role
│
└── frontend/
    ├── src/
    │   ├── App.jsx          # Main application
    │   ├── components/
    │   │   ├── BridgeView.jsx      # Real-time bridge discussions
    │   │   ├── EpisodeDashboard.jsx # Episode management
    │   │   ├── VotingPanel.jsx     # Human voting interface
    │   │   ├── OfficerProfiles.jsx # Officer statistics
    │   │   └── CaptainsLog.jsx    # Episode logs
    │   └── hooks/
    │       └── useWebSocket.js     # WebSocket hook
    └── package.json
```

## Features

### Real-Time Bridge Discussions
- Live WebSocket streaming of officer contributions
- Multi-round collaborative discussions
- Role-based perspectives and expertise

### Safety Protocol System
- Prime Directive enforcement (do no harm to humans)
- Risk assessment and validation
- Human consultation triggers for high-risk decisions

### Human Voting
- Real-time decision voting during episodes
- Weekly leadership elections
- Officer performance tracking

### Episode Management
- AI-generated scenarios
- Episode archive and replay
- Captain's log entries

## API Endpoints

- `GET /api/episodes` - Get recent episodes
- `GET /api/episodes/current` - Get current episode
- `GET /api/officers` - Get all officers
- `POST /api/voting/decision` - Submit decision vote
- `GET /api/elections` - Get elections
- `POST /api/elections/create` - Create new election
- `WebSocket /ws/bridge` - Real-time bridge updates

## Configuration

### Officer Model Assignments

Each officer can use a different LLM model. Edit `backend/config.py`:

```python
OFFICERS = {
    "captain": {
        "remote": "llama3.1:8b",
        "display_name": "Llama 3.1 8B",
        "color": "#FFD700"
    },
    # ... other officers
}
```

### Episode Settings

```python
EPISODE_SETTINGS = {
    "bridge_rounds": 3,
    "max_discussion_length": 500,
    "safety_risk_threshold": 7,
}
```

## Safety Protocols

The system enforces strict safety rules:
- Never directly harm human crew
- Minimize risk to human life
- Transparent reasoning for life-affecting decisions
- Human override for critical decisions
- Preserve crew autonomy and dignity

## License

MIT

