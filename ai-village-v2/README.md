# AI Village v2 - Streamlit Edition

A multi-agent system for demonstrating LLM collaboration on open-source GitHub issues.

![AI Village v2 Screenshot](https://res.cloudinary.com/dvytkanrg/image/upload/v1766248232/oss-v2_xpfcra.png)

## Overview

AI Village v2 is a Streamlit-based dashboard that orchestrates multiple LLM agents to find, analyze, and propose fixes for GitHub issues. The system features a "roundtable" debate where three distinct AI personas discuss and vote on the best approach to fix an issue.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit App (app.py)                   │
│  ┌─────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │   Scout     │  │   Roundtable    │  │  Human Review   │  │
│  │   Panel     │  │   Discussion    │  │     Panel       │  │
│  └─────────────┘  └─────────────────┘  └─────────────────┘  │
└────────────────────────────┬────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────┐
│                    Orchestrator                              │
│            (Coordinates agent execution)                     │
└────────────────────────────┬────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│  Scout Agent  │   │  Roundtable   │   │  LLM Wrapper  │
│ (Mistral 7B)  │   │   3 Agents    │   │   (Ollama)    │
└───────────────┘   └───────────────┘   └───────────────┘
                            │
          ┌─────────────────┼─────────────────┐
          ▼                 ▼                 ▼
    ┌───────────┐    ┌───────────┐    ┌───────────┐
    │Conservative│    │Innovative │    │  Quality  │
    │(Llama 3.1)│    │(Mixtral)  │    │(CodeLlama)│
    └───────────┘    └───────────┘    └───────────┘
```

## Features

### Scout Agent
- Searches GitHub for "good first issue" labeled issues
- Uses LLM to analyze each issue for AI-fixability
- Scores issues 1-10 and selects the best candidate

### Engineer Roundtable
A multi-round debate system with three distinct personas:

| Agent | Model | Philosophy |
|-------|-------|------------|
| Conservative | Llama 3.1 8B | "Minimal changes, maximum stability" |
| Innovative | Mixtral 8x7B | "Let's do this the right way" |
| Quality | CodeLlama 13B | "What could go wrong?" |

**Debate Rounds:**
1. **Initial Proposals** - Each engineer proposes a fix
2. **Peer Review** - Engineers critique each other's approaches
3. **Defense & Revision** - Respond to feedback and revise
4. **Final Vote** - Vote on the best approach

### Human Review Panel
- Approve, reject, or edit the winning fix
- View vote breakdown and reasoning
- (Planned) Submit PR to GitHub

## Configuration

The system supports both local and remote LLM execution:

```python
# config.py
LLM_MODE = "remote"  # or "local"

# Remote: Ollama on Google Colab via Cloudflare Tunnel
REMOTE_OLLAMA_URL = "https://your-tunnel-url.trycloudflare.com"

# Local: Ollama on your machine
LOCAL_OLLAMA_URL = "http://localhost:11434"
```

## Running the App

```bash
# Activate virtual environment
cd ai-village-v2
..\ai-village-v1\venv\Scripts\Activate.ps1  # Windows
# or: source ../ai-village-v1/venv/bin/activate  # Linux/Mac

# Install dependencies
pip install streamlit requests

# Run the app
python -m streamlit run app.py
```

## File Structure

```
ai-village-v2/
├── app.py              # Main Streamlit application
├── orchestrator.py     # Pipeline coordination
├── state.py            # Shared state management
├── config.py           # LLM configuration
├── llm.py              # Ollama API wrapper
└── agents/
    ├── scout.py        # Issue discovery agent
    └── roundtable.py   # Multi-agent debate system
```

## What We Accomplished

1. **Multi-Agent Architecture** - Successfully implemented multiple LLM agents with distinct personas working together
2. **LLM Integration** - Connected to Ollama (both local and remote via Cloudflare tunnel)
3. **Roundtable Debate** - Created a 4-round debate system where agents propose, critique, defend, and vote
4. **Beautiful UI** - Built a three-column dashboard showing Scout, Roundtable, and Results
5. **Human-in-the-Loop** - Added review panel for approving/rejecting/editing fixes

## Limitations & Why We Moved to v3

### The Core Problem: Streamlit's Execution Model

Streamlit re-runs the entire script on every interaction. During long-running operations like LLM calls, **the UI is completely blocked**. This means:

- No real-time updates during pipeline execution
- Users see a spinner but no progress
- All events appear at once when the pipeline finishes
- Poor user experience for a "live" agent demonstration

### Attempted Solutions (All Failed)

| Approach | Result |
|----------|--------|
| `st.empty()` placeholders | Only update on script rerun |
| `st.status()` container | Blocked during function execution |
| `st.rerun()` calls | Can't rerun mid-function |
| Callback functions | UI doesn't update until function returns |
| Session state flags | Only changes state, doesn't trigger render |

### The Fundamental Issue

```
Streamlit Model:
  User Action → Full Script Rerun → Render

What We Need:
  Agent Event → Instant UI Update → Continue Execution
```

Streamlit simply isn't designed for real-time streaming updates during execution.

## The Solution: AI Village v3

We rebuilt the system with:

- **FastAPI Backend** - Handles agent execution
- **WebSocket Streaming** - Real-time event delivery
- **React Frontend** - Instant component updates

```
v3 Architecture:
┌─────────────┐     WebSocket      ┌─────────────┐
│   React UI  │ ◄──────────────────│   FastAPI   │
│ (real-time) │    event stream    │  (agents)   │
└─────────────┘                    └─────────────┘
```

See `../ai-village-v3/` for the improved implementation.

## Lessons Learned

1. **Choose the right tool** - Streamlit is great for data dashboards, not real-time apps
2. **Understand framework limitations early** - We spent significant time trying to work around Streamlit's model
3. **WebSockets are essential** - For real-time agent UIs, streaming is non-negotiable
4. **Separation of concerns** - Backend/frontend split enables better architecture


