# AI Village v3 - React + FastAPI Edition

A real-time multi-agent system demonstrating LLM collaboration on open-source GitHub issues, featuring WebSocket streaming for instant UI updates.

![AI Village v3](https://res.cloudinary.com/dvytkanrg/image/upload/v1766248232/oss-v3_placeholder.png)

## Why v3?

v2 was built with Streamlit, which blocks the UI during long-running operations. This made it impossible to show real-time agent activity. v3 solves this with:

- **WebSocket streaming** - Events flow instantly from backend to frontend
- **React frontend** - Component-level updates without full page reruns
- **FastAPI backend** - Async support for concurrent agent execution

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     React Frontend (Vite)                        │
│  ┌─────────────┐  ┌─────────────────┐  ┌─────────────────────┐  │
│  │ ScoutPanel  │  │ RoundtablePanel │  │   ResultsPanel      │  │
│  │             │  │                 │  │   + Human Review    │  │
│  └─────────────┘  └─────────────────┘  └─────────────────────┘  │
│                            │                                     │
│                    useWebSocket Hook                             │
└────────────────────────────┼────────────────────────────────────┘
                             │ WebSocket
                             │ (real-time events)
┌────────────────────────────▼────────────────────────────────────┐
│                    FastAPI Backend                               │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                  /ws/pipeline endpoint                    │   │
│  │         (streams events as async generators)              │   │
│  └──────────────────────────────────────────────────────────┘   │
│                             │                                    │
│         ┌───────────────────┼───────────────────┐               │
│         ▼                   ▼                   ▼               │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │   Scout     │    │ Roundtable  │    │    LLM      │         │
│  │   Agent     │    │   Debate    │    │   Wrapper   │         │
│  │ (Mistral)   │    │  (3 LLMs)   │    │  (Ollama)   │         │
│  └─────────────┘    └─────────────┘    └─────────────┘         │
└─────────────────────────────────────────────────────────────────┘
                             │
                             ▼
              ┌─────────────────────────────┐
              │   Ollama (Local or Remote)  │
              │   via Cloudflare Tunnel     │
              └─────────────────────────────┘
```

## Features

### Real-Time Streaming
Every agent action streams to the UI instantly:
- Scout searching GitHub
- Each LLM "thinking"
- Proposals, critiques, revisions
- Votes as they're cast

### Multi-LLM Roundtable
Three distinct AI personas debate code fixes:

| Agent | Model | Philosophy |
|-------|-------|------------|
| **Conservative** | Llama 3.1 8B | "Minimal changes, maximum stability" |
| **Innovative** | Mixtral 8x7B | "Let's do this the right way" |
| **Quality** | CodeLlama 13B | "What could go wrong?" |

### Human Review Panel
- Approve fixes for PR submission
- Reject and restart
- Edit code before submitting

## Tech Stack

- **Frontend**: React 18, Vite, CSS-in-JS
- **Backend**: FastAPI, Uvicorn, WebSockets
- **LLM**: Ollama (local or remote via Cloudflare tunnel)
- **Styling**: Custom dark theme with JetBrains Mono + Space Grotesk fonts

## Quick Start

### 1. Start the Backend
```bash
cd ai-village-v3/backend
pip install -r requirements.txt
python -m uvicorn main:app --port 8000 --reload
```

### 2. Start the Frontend
```bash
cd ai-village-v3/frontend
npm install
npm run dev
```

### 3. Configure LLM Endpoint
Edit `backend/config.py`:
```python
LLM_MODE = "remote"  # or "local"
REMOTE_OLLAMA_URL = "https://your-tunnel.trycloudflare.com"
```

### 4. Open the App
Navigate to http://localhost:5173

## Project Structure

```
ai-village-v3/
├── backend/
│   ├── main.py              # FastAPI server + WebSocket endpoint
│   ├── config.py            # LLM configuration
│   ├── llm.py               # Ollama API wrapper
│   └── agents/
│       ├── scout.py         # Issue discovery (async generator)
│       └── roundtable.py    # Multi-agent debate (async generator)
│
└── frontend/
    ├── index.html
    ├── package.json
    ├── vite.config.js
    └── src/
        ├── App.jsx          # Main application
        ├── index.css        # Global styles + CSS variables
        ├── hooks/
        │   └── useWebSocket.js   # WebSocket connection hook
        └── components/
            ├── ScoutPanel.jsx      # Issue discovery UI
            ├── RoundtablePanel.jsx # Debate discussion UI
            └── ResultsPanel.jsx    # Winner + human review UI
```

## Configuration Options

### Model Assignments
Each agent can use a different LLM model. Edit `backend/config.py`:

```python
MODELS = {
    "scout": {
        "local": "qwen2.5:3b",
        "remote": "mistral:7b",
        "display_name": "Mistral 7B",
        "color": "#FFD700"
    },
    # ... other agents
}
```

### Running on Google Colab
For access to larger models (Mixtral 8x7B, CodeLlama 13B), run Ollama on Colab with a Cloudflare tunnel. See `../ai-village-v2/colab_llm_server.ipynb` for setup instructions.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/api/config` | GET | Returns model configuration |
| `/ws/pipeline` | WebSocket | Streams pipeline events |

### WebSocket Protocol

**Client → Server:**
```json
{"action": "start", "repo": "owner/repo"}
```

**Server → Client (event stream):**
```json
{"type": "step", "agent": "scout", "message": "...", "data": {...}}
{"type": "proposal", "agent": "conservative", "message": "...", "data": {...}}
{"type": "vote", "agent": "quality", "message": "...", "data": {...}}
{"type": "roundtable_complete", "agent": "roundtable", "message": "...", "data": {...}}
```

## Comparison: v2 vs v3

| Feature | v2 (Streamlit) | v3 (React + FastAPI) |
|---------|----------------|---------------------|
| Real-time updates | Blocked during execution | Instant streaming |
| UI responsiveness | Full page reruns | Component updates |
| Architecture | Monolithic | Clean separation |
| Scalability | Limited | Async-ready |
| Code complexity | Simpler | More setup required |

## Next Steps

- [ ] GitHub PR submission integration
- [ ] SQLite database for tracking fixes
- [ ] Multi-repo continuous scanning
- [ ] Analytics dashboard
- [ ] Additional LLM agents (Reviewer, Tester)

