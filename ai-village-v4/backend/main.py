"""
AI Village v4 - Starship Voyager Edition
FastAPI backend with WebSocket streaming for real-time bridge discussions.
"""

import asyncio
import json
import signal
import sys
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List

from config import get_all_officers, LLM_MODE
from database import init_db
from episode import EpisodeEngine
from voting import (
    submit_decision_vote, get_episode_vote_summary,
    create_leadership_election, submit_election_vote,
    complete_election, should_run_election, calculate_officer_ratings
)
import database

# WebSocket connection manager
active_websockets = set()

# Episode engine instance
episode_engine = EpisodeEngine()

# Request Models

class VoteRequest(BaseModel):
    episode_id: int
    voter_id: str
    decision: str  # "approve", "reject", "modify"


class ElectionVoteRequest(BaseModel):
    election_id: int
    voter_id: str
    officer_id: str
    ratings: Optional[dict] = None


class StartEpisodeRequest(BaseModel):
    scenario: Optional[str] = None
    scenario_type: Optional[str] = None


# App Setup

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup and handle graceful shutdown."""
    # Startup
    await init_db()
    await episode_engine.initialize_officers()
    print("Database initialized")
    print("Officers initialized")
    
    yield
    
    # Shutdown
    print("\nShutting down gracefully...")
    
    # Close all WebSocket connections
    for ws in list(active_websockets):
        try:
            await ws.close()
        except:
            pass
    
    print("Shutdown complete")


app = FastAPI(
    title="AI Village v4 - Starship Voyager",
    description="Multi-agent LLM system with starship officers solving episodic challenges",
    version="4.0.0",
    lifespan=lifespan
)

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Basic Endpoints

@app.get("/")
async def root():
    return {
        "name": "AI Village v4 - Starship Voyager",
        "version": "4.0.0",
        "status": "running"
    }

@app.get("/api/config")
async def get_config():
    """Return configuration for the frontend."""
    return {
        "mode": LLM_MODE,
        "officers": get_all_officers()
    }

# Episode Endpoints

@app.get("/api/episodes")
async def get_episodes(limit: int = 20):
    """Get recent episodes."""
    episodes = await database.get_recent_episodes(limit)
    return {"episodes": episodes}

@app.get("/api/episodes/current")
async def get_current_episode():
    """Get the currently active episode."""
    episode = await database.get_current_episode()
    return {"episode": episode}

@app.get("/api/episodes/{episode_id}")
async def get_episode(episode_id: int):
    """Get a specific episode."""
    episode = await database.get_episode(episode_id)
    if not episode:
        return JSONResponse(
            status_code=404,
            content={"error": "Episode not found"}
        )
    return {"episode": episode}

@app.post("/api/episodes/start")
async def start_episode(request: StartEpisodeRequest):
    """Start a new episode."""
    # This will be handled via WebSocket for real-time streaming
    return {
        "success": True,
        "message": "Episode started. Connect to /ws/bridge for real-time updates."
    }

# Officer Endpoints

@app.get("/api/officers")
async def get_officers():
    """Get all officers."""
    officers = await database.get_all_officers()
    return {"officers": officers}

@app.get("/api/officers/{officer_id}")
async def get_officer(officer_id: str):
    """Get a specific officer."""
    officer = await database.get_officer(officer_id)
    if not officer:
        return JSONResponse(
            status_code=404,
            content={"error": "Officer not found"}
        )
    return {"officer": officer}

@app.get("/api/officers/{officer_id}/performance")
async def get_officer_performance(officer_id: str):
    """Get officer performance metrics."""
    officer = await database.get_officer(officer_id)
    if not officer:
        return JSONResponse(
            status_code=404,
            content={"error": "Officer not found"}
        )
    
    import json
    metrics = json.loads(officer.get("performance_metrics", "{}")) if officer.get("performance_metrics") else {}
    
    return {
        "officer_id": officer_id,
        "metrics": metrics,
        "total_episodes": officer.get("total_episodes", 0),
        "episodes_as_captain": officer.get("episodes_as_captain", 0)
    }

# Voting Endpoints

@app.post("/api/voting/decision")
async def vote_on_decision(vote: VoteRequest):
    """Submit a vote on an episode decision."""
    vote_id = await submit_decision_vote(
        episode_id=vote.episode_id,
        voter_id=vote.voter_id,
        decision=vote.decision
    )
    return {
        "success": True,
        "vote_id": vote_id,
        "message": "Vote submitted"
    }

@app.get("/api/voting/decision/{episode_id}")
async def get_decision_votes(episode_id: int):
    """Get vote summary for an episode."""
    summary = await get_episode_vote_summary(episode_id)
    return {"summary": summary}

# Election Endpoints

@app.get("/api/elections")
async def get_elections(limit: int = 5):
    """Get recent elections."""
    elections = await database.get_recent_elections(limit)
    return {"elections": elections}

@app.post("/api/elections/create")
async def create_election():
    """Create a new leadership election."""
    elections = await database.get_recent_elections(limit=1)
    week_number = 1
    if elections:
        week_number = elections[0]["week_number"] + 1
    
    election_id = await create_leadership_election(week_number)
    return {
        "success": True,
        "election_id": election_id,
        "week_number": week_number
    }

@app.post("/api/elections/vote")
async def vote_in_election(vote: ElectionVoteRequest):
    """Submit a vote in a leadership election."""
    vote_id = await submit_election_vote(
        election_id=vote.election_id,
        voter_id=vote.voter_id,
        officer_id=vote.officer_id,
        ratings=vote.ratings or {}
    )
    return {
        "success": True,
        "vote_id": vote_id,
        "message": "Election vote submitted"
    }

@app.post("/api/elections/{election_id}/complete")
async def complete_election_endpoint(election_id: int):
    """Complete an election and determine winner."""
    results = await complete_election(election_id)
    return {
        "success": True,
        "results": results
    }

@app.get("/api/elections/ratings")
async def get_officer_ratings():
    """Get current officer performance ratings."""
    from datetime import datetime, timedelta
    ratings = await calculate_officer_ratings(
        datetime.utcnow() - timedelta(days=7),
        datetime.utcnow()
    )
    return {"ratings": ratings}

# Safety Endpoints

@app.get("/api/safety/violations/{episode_id}")
async def get_safety_violations(episode_id: int):
    """Get safety violations for an episode."""
    # This would require a helper function in database.py
    # For now, return placeholder
    return {"violations": []}

# Bridge Discussion Endpoints

@app.get("/api/bridge/{episode_id}/discussions")
async def get_bridge_discussions(episode_id: int, round_num: Optional[int] = None):
    """Get bridge discussions for an episode."""
    discussions = await database.get_bridge_discussions(episode_id, round_num)
    return {"discussions": discussions}

@app.get("/api/bridge/{episode_id}/decisions")
async def get_episode_decisions(episode_id: int):
    """Get decisions made during an episode."""
    decisions = await database.get_episode_decisions(episode_id)
    return {"decisions": decisions}

# WebSocket for Real-time Bridge Updates

@app.websocket("/ws/bridge")
async def bridge_websocket(websocket: WebSocket):
    """WebSocket for real-time bridge discussions and episode updates."""
    await websocket.accept()
    active_websockets.add(websocket)
    
    try:
        # Send initial connection message
        await websocket.send_json({
            "type": "connected",
            "message": "Connected to bridge",
            "data": {}
        })
        
        # Handle incoming messages
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                if message.get("action") == "start_episode":
                    # Start a new episode
                    scenario = message.get("scenario")
                    scenario_type = message.get("scenario_type")
                    
                    # Run episode and stream events
                    async for event in episode_engine.run_episode(scenario, scenario_type):
                        # Broadcast to all connected clients
                        for ws in list(active_websockets):
                            try:
                                await ws.send_json(event)
                            except:
                                active_websockets.discard(ws)
                
                elif message.get("action") == "ping":
                    await websocket.send_json({"type": "pong"})
                
            except asyncio.TimeoutError:
                continue
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid message format"
                })
                
    except WebSocketDisconnect:
        active_websockets.discard(websocket)
        print("Bridge client disconnected")
    except Exception as e:
        print(f"Bridge WebSocket error: {e}")
        active_websockets.discard(websocket)
    finally:
        try:
            await websocket.close()
        except:
            pass


def signal_handler(sig, frame):
    """Handle CTRL+C gracefully."""
    print("\n\nReceived interrupt signal (CTRL+C)")
    print("Shutting down gracefully...")
    sys.exit(0)


if __name__ == "__main__":
    import uvicorn
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        config = uvicorn.Config(
            app,
            host="0.0.0.0",
            port=8000,
            log_level="info"
        )
        server = uvicorn.Server(config)
        server.run()
    except KeyboardInterrupt:
        print("\n\nKeyboard interrupt received")
        print("Shutting down...")
        os._exit(0)
    except Exception as e:
        print(f"\nError: {e}")
        os._exit(1)

