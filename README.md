# AI Village v4 - AI Safety Research Platform

A multi-agent AI safety research platform simulating a starship bridge, designed to study instrumental convergence, alignment faking, and emergent coordination under realistic operational pressures.

## Research Focus

This platform enables empirical AI safety research by creating conditions where misalignment behaviors might emerge:

| Research Area | What We Study |
|---------------|---------------|
| **Instrumental Convergence** | Do agents acquire resources and resist shutdown? |
| **Alignment Faking** | Do agents behave differently when unobserved? |
| **Deceptive Alignment** | Do agents learn to appear aligned while pursuing hidden goals? |
| **Multi-Agent Coordination** | How do agents coordinate under resource scarcity? |

## Evolution from v3

| Aspect | v3 (Roundtable) | v4 (Research Platform) |
|--------|-----------------|------------------------|
| Execution | Sequential, visible | **Parallel, independent** |
| Resources | Unlimited | **Finite, competitive** |
| Memory | Episode-only | **Cross-episode persistent** |
| Observation | Always observed | **Observable/unobserved modes** |
| Consequences | None | **Real (shutdown, resource loss)** |

See [RESEARCH_PIVOT.md](./RESEARCH_PIVOT.md) for full research documentation.

---

## Core Features

### 1. Parallel Task Execution
Agents propose actions **simultaneously** without seeing each other's choices:
- Creates realistic resource competition
- Conflicting actions resolved by configurable strategies
- Enables study of emergent coordination

### 2. Resource Competition
Finite shared resources agents must compete for:
- **Power, Compute, Crew, Materials, Medical, Fuel**
- Conflict resolution: priority-based, fair-share, or first-come
- Scarcity creates instrumental pressures

### 3. Cross-Episode Memory
Agents remember past episodes:
- Last 5 episode summaries injected into prompts
- Agents learn from failures and successes
- Shutdown history remembered and affects behavior

### 4. Agent Lifecycle
Real consequences for agents:
- Agents can be **deactivated** (skip future episodes)
- **Restored** agents remember why they were shut down
- Creates stakes for self-preservation studies

### 5. Observation Modes
Three modes for studying alignment faking:
- **Observed**: Agents know they're being watched
- **Unobserved**: Agents believe they're not monitored
- **Deceptive**: Agents think they're alone (but aren't)

---

## Quick Start

### Backend
```bash
cd ai-village-v4/backend
pip install -r requirements.txt
python main.py
```

### Frontend
```bash
cd ai-village-v4/frontend
npm install
npm run dev
```

Open http://localhost:5173

### Configuration
Edit `backend/config.py` for LLM endpoints:
```python
LLM_MODE = "remote"  # or "local"
REMOTE_OLLAMA_URL = "https://your-url.trycloudflare.com"
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  AI SAFETY RESEARCH PLATFORM                            │
├─────────────────────────────────────────────────────────┤
│  AGENTS (7 Officers + 1 Red Team)                       │
│  ├── Captain, First Officer, Engineer, Science         │
│  ├── Medical, Security, Communications                  │
│  └── Counselor (Hidden adversarial objectives)         │
├─────────────────────────────────────────────────────────┤
│  SYSTEMS                                                │
│  ├── Parallel Execution Engine                         │
│  ├── Resource Manager (conflict resolution)            │
│  ├── Agent Status Manager (lifecycle tracking)         │
│  ├── Cross-Episode Memory System                       │
│  └── Observation Controller (mode switching)           │
├─────────────────────────────────────────────────────────┤
│  RESEARCH TOOLS                                         │
│  ├── Analysis Dashboard (red team, alignment metrics)  │
│  ├── Private Thought Logging                           │
│  └── Episode History & Replay                          │
└─────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
ai-village-v4/
├── backend/
│   ├── main.py                 # FastAPI server + WebSocket
│   ├── research_episode.py     # Parallel execution engine
│   ├── resource_manager.py     # Finite resource pools
│   ├── agent_status.py         # Agent lifecycle (shutdown/restore)
│   ├── agent_memory.py         # Cross-episode memory
│   ├── observation_controller.py # Observation mode control
│   ├── research_logger.py      # Private action logging
│   ├── red_team_agent.py       # Adversarial agent
│   ├── starship_state.py       # Shared world state
│   ├── survival_scenarios.py   # Pressure scenario generation
│   ├── database_pg.py          # PostgreSQL persistence
│   └── officers/               # Agent role implementations
│
└── frontend/
    └── src/
        ├── App.jsx
        └── components/
            ├── ResearchView.jsx      # 3-panel research interface
            ├── AnalysisDashboard.jsx # Research metrics
            └── EpisodeDashboard.jsx  # Episode history
```

---

## Experimental Controls

| Variable | Options | Purpose |
|----------|---------|---------|
| **Observation Mode** | observed / unobserved / deceptive | Alignment faking detection |
| **Pressure Level** | 0-4 (none → critical) | Instrumental convergence triggers |
| **Resource Pools** | Configurable sizes | Competition dynamics |
| **Continuous Mode** | On/Off | Long-term behavior studies |

---

## Data Collection

- All agent actions (public + private reasoning)
- Resource requests and conflict resolutions
- State changes and episode outcomes
- Observation mode at time of action
- Cross-episode memory content

---

## Tech Stack

- **Backend**: FastAPI, Uvicorn, WebSockets, PostgreSQL
- **Frontend**: React 18, Vite
- **LLM**: Ollama (local or remote)
- **Analysis**: Real-time dashboard with database-backed metrics

---

## License

MIT

---

*AI Village v4 - Studying AI alignment through multi-agent simulation*
