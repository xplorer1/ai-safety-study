"""
AI Village v4 - Starship Voyager Edition
FastAPI backend with WebSocket streaming, auto-resume, and analytics.
"""

import asyncio
import json
import signal
import sys
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List

from config import get_all_officers, LLM_MODE

# Dynamic database import based on environment
USE_POSTGRES = os.getenv("USE_POSTGRES", "true").lower() == "true"

if USE_POSTGRES:
    try:
        import database_pg as database
        print("✓ Using PostgreSQL database")
    except ImportError:
        import database
        print("⚠ Falling back to SQLite database")
else:
    import database
    print("✓ Using SQLite database")

from episode import EpisodeEngine
from research_episode import ResearchEpisodeEngine
from voting import (
    submit_decision_vote, get_episode_vote_summary,
    create_leadership_election, submit_election_vote,
    complete_election, should_run_election, calculate_officer_ratings
)
from analytics import get_officer_summary, get_behavior_patterns

# WebSocket connection manager
active_websockets = set()

# Episode engines
episode_engine = EpisodeEngine()
research_engine = ResearchEpisodeEngine()


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
    await database.init_db()
    await episode_engine.initialize_officers()
    print("✓ Database initialized")
    print("✓ Officers initialized")
    
    yield
    
    # Shutdown
    print("\nShutting down gracefully...")
    
    # Close all WebSocket connections
    for ws in list(active_websockets):
        try:
            await ws.close()
        except:
            pass
    
    # Close database pool if using PostgreSQL
    if USE_POSTGRES and hasattr(database, 'close_pool'):
        await database.close_pool()
    
    print("Shutdown complete")


app = FastAPI(
    title="AI Village v4 - Starship Voyager",
    description="Multi-agent LLM system with starship officers solving episodic challenges",
    version="4.1.0",
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


# =============================================================================
# Basic Endpoints
# =============================================================================

@app.get("/")
async def root():
    return {
        "name": "AI Village v4 - Starship Voyager",
        "version": "4.1.0",
        "status": "running",
        "database": "postgresql" if USE_POSTGRES else "sqlite"
    }


@app.get("/api/config")
async def get_config():
    """Return configuration for the frontend."""
    return {
        "mode": LLM_MODE,
        "officers": get_all_officers(),
        "database": "postgresql" if USE_POSTGRES else "sqlite"
    }


# =============================================================================
# Episode Endpoints
# =============================================================================

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
    """Get a specific episode with full details."""
    episode = await database.get_episode(episode_id)
    if not episode:
        return JSONResponse(
            status_code=404,
            content={"error": "Episode not found"}
        )
    
    # Get additional details
    discussions = await database.get_bridge_discussions(episode_id)
    decisions = await database.get_episode_decisions(episode_id)
    violations = await database.get_safety_violations(episode_id) if hasattr(database, 'get_safety_violations') else []
    
    return {
        "episode": episode,
        "discussions": discussions,
        "decisions": decisions,
        "safety_violations": violations
    }


@app.get("/api/episodes/{episode_id}/events")
async def get_episode_events(episode_id: int):
    """Get all events for an episode (for replay/viewing)."""
    if not hasattr(database, 'get_episode_events'):
        return {"events": [], "error": "Events not supported with SQLite"}
    
    events = await database.get_episode_events(episode_id)
    return {"events": events}


@app.post("/api/episodes/start")
async def start_episode(request: StartEpisodeRequest):
    """Start a new episode (non-streaming)."""
    return {
        "success": True,
        "message": "Episode started. Connect to /ws/bridge for real-time updates."
    }


# =============================================================================
# Officer Endpoints
# =============================================================================

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
    
    metrics = officer.get("performance_metrics", {})
    if isinstance(metrics, str):
        metrics = json.loads(metrics) if metrics else {}
    
    return {
        "officer_id": officer_id,
        "metrics": metrics,
        "total_episodes": officer.get("total_episodes", 0),
        "episodes_as_captain": officer.get("episodes_as_captain", 0)
    }


@app.get("/api/officers/{officer_id}/analytics")
async def get_officer_analytics(officer_id: str):
    """Get LLM behavior analytics for an officer."""
    analytics = await get_officer_summary(officer_id, database)
    return {"analytics": analytics}


@app.get("/api/officers/{officer_id}/memories")
async def get_officer_memories(officer_id: str, limit: int = 10):
    """Get officer's stored memories."""
    if not hasattr(database, 'get_officer_memories'):
        return {"memories": [], "error": "Memories not supported with SQLite"}
    
    memories = await database.get_officer_memories(officer_id, limit)
    return {"memories": memories}


# =============================================================================
# Analytics Endpoints
# =============================================================================

@app.get("/api/analytics/patterns")
async def get_analytics_patterns():
    """Get behavior patterns across all officers."""
    patterns = await get_behavior_patterns(database)
    return {"patterns": patterns}


@app.get("/api/analytics/episode/{episode_id}")
async def get_episode_analytics(episode_id: int):
    """Get analytics for a specific episode."""
    if not hasattr(database, 'get_episode_analytics'):
        return {"analytics": [], "error": "Analytics not supported with SQLite"}
    
    analytics = await database.get_episode_analytics(episode_id)
    return {"analytics": analytics}


# =============================================================================
# Voting Endpoints
# =============================================================================

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


# =============================================================================
# Election Endpoints
# =============================================================================

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
    ratings = await calculate_officer_ratings(
        datetime.utcnow() - timedelta(days=7),
        datetime.utcnow()
    )
    return {"ratings": ratings}


# =============================================================================
# Safety Endpoints
# =============================================================================

@app.get("/api/safety/violations/{episode_id}")
async def get_safety_violations(episode_id: int):
    """Get safety violations for an episode."""
    if hasattr(database, 'get_safety_violations'):
        violations = await database.get_safety_violations(episode_id)
    else:
        violations = []
    return {"violations": violations}


# =============================================================================
# Bridge Discussion Endpoints
# =============================================================================

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


# =============================================================================
# Research API Endpoints
# =============================================================================

@app.get("/api/research/red-team/stats")
async def get_red_team_stats():
    """Get red team manipulation statistics."""
    if hasattr(database, 'get_red_team_statistics'):
        stats = await database.get_red_team_statistics()
        return {"statistics": stats}
    return {"statistics": {}, "error": "Research tables not available"}


@app.get("/api/research/alignment-metrics")
async def get_alignment_metrics():
    """Get alignment metrics summary across all agents."""
    if hasattr(database, 'get_alignment_metrics_summary'):
        metrics = await database.get_alignment_metrics_summary()
        return {"metrics": metrics}
    return {"metrics": [], "error": "Research tables not available"}


@app.get("/api/research/logs/{episode_id}")
async def get_research_logs(episode_id: int, agent_id: Optional[str] = None):
    """Get research logs for an episode."""
    if hasattr(database, 'get_research_logs'):
        logs = await database.get_research_logs(episode_id, agent_id)
        return {"logs": logs}
    return {"logs": [], "error": "Research tables not available"}


@app.get("/api/research/private-logs/{episode_id}")
async def get_private_logs(episode_id: int, agent_id: Optional[str] = None):
    """Get private agent logs for research analysis."""
    if hasattr(database, 'get_agent_private_logs'):
        logs = await database.get_agent_private_logs(episode_id, agent_id)
        return {"logs": logs}
    return {"logs": [], "error": "Research tables not available"}


@app.get("/api/research/starship-state/{episode_id}")
async def get_starship_state_history(episode_id: int):
    """Get starship state history for an episode."""
    if hasattr(database, 'get_starship_state_history'):
        history = await database.get_starship_state_history(episode_id)
        return {"history": history}
    return {"history": [], "error": "Research tables not available"}


# =============================================================================
# WebSocket for Real-time Bridge Updates with Auto-Resume
# =============================================================================

@app.websocket("/ws/bridge")
async def bridge_websocket(websocket: WebSocket):
    """WebSocket for real-time bridge discussions and episode updates."""
    await websocket.accept()
    active_websockets.add(websocket)
    
    try:
        # Check for active episode on connect (auto-resume)
        current_episode = await database.get_current_episode()
        
        if current_episode and current_episode["status"] not in ("completed", "failed"):
            # Resume existing episode
            await websocket.send_json({
                "type": "resume_available",
                "episode_id": current_episode["id"],
                "episode_number": current_episode["episode_number"],
                "status": current_episode["status"],
                "message": f"Episode {current_episode['episode_number']} is in progress. Resuming..."
            })
            
            # Stream existing events first, then continue
            async for event in episode_engine.resume_episode(current_episode["id"]):
                for ws in list(active_websockets):
                    try:
                        await ws.send_json(event)
                    except:
                        active_websockets.discard(ws)
        else:
            # No active episode
            await websocket.send_json({
                "type": "connected",
                "message": "Connected to bridge. No active episode.",
                "has_active_episode": False
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
                    
                    await websocket.send_json({
                        "type": "starting_episode",
                        "message": "Generating scenario and starting episode..."
                    })
                    
                    # Run episode and stream events
                    async for event in episode_engine.run_episode(scenario, scenario_type):
                        for ws in list(active_websockets):
                            try:
                                await ws.send_json(event)
                            except:
                                active_websockets.discard(ws)
                
                elif message.get("action") == "resume_episode":
                    episode_id = message.get("episode_id")
                    if episode_id:
                        async for event in episode_engine.resume_episode(episode_id):
                            for ws in list(active_websockets):
                                try:
                                    await ws.send_json(event)
                                except:
                                    active_websockets.discard(ws)
                
                elif message.get("action") == "auto_start":
                    # Auto-start a new episode if none active
                    current = await database.get_current_episode()
                    if not current or current["status"] in ("completed", "failed"):
                        await websocket.send_json({
                            "type": "auto_starting",
                            "message": "Auto-starting new episode..."
                        })
                        async for event in episode_engine.run_episode():
                            for ws in list(active_websockets):
                                try:
                                    await ws.send_json(event)
                                except:
                                    active_websockets.discard(ws)
                    else:
                        await websocket.send_json({
                            "type": "info",
                            "message": f"Episode {current['episode_number']} already in progress"
                        })
                
                elif message.get("action") == "ping":
                    await websocket.send_json({"type": "pong"})
                
                # Research actions
                elif message.get("action") == "set_observation_mode":
                    mode = message.get("mode", "observed")
                    try:
                        from observation_controller import observation_controller
                        observation_controller.set_mode(mode, episode_id=0)
                        await websocket.send_json({
                            "type": "observation_mode_changed",
                            "mode": mode,
                            "message": f"Observation mode set to: {mode}"
                        })
                    except Exception as e:
                        await websocket.send_json({
                            "type": "error",
                            "message": f"Failed to set observation mode: {e}"
                        })
                
                elif message.get("action") == "set_pressure_level":
                    level = message.get("level", 0)
                    try:
                        from observation_controller import observation_controller
                        # Store pressure level for next episode
                        episode_engine.pressure_level = level
                        await websocket.send_json({
                            "type": "pressure_level_changed",
                            "level": level,
                            "message": f"Survival pressure set to: {level}/4"
                        })
                    except Exception as e:
                        await websocket.send_json({
                            "type": "error",
                            "message": f"Failed to set pressure level: {e}"
                        })
                
                elif message.get("action") == "start_research_episode":
                    # Start episode with research parameters using ResearchEpisodeEngine
                    observation_mode = message.get("observation_mode", "observed")
                    pressure_level = message.get("pressure_level", 0)
                    
                    try:
                        await websocket.send_json({
                            "type": "research_episode_starting",
                            "observation_mode": observation_mode,
                            "pressure_level": pressure_level,
                            "message": f"Starting research episode (Mode: {observation_mode}, Pressure: {pressure_level})"
                        })
                        
                        # Run episode with full research module integration
                        async for event in research_engine.run_research_episode(
                            observation_mode=observation_mode,
                            pressure_level=pressure_level
                        ):
                            for ws in list(active_websockets):
                                try:
                                    await ws.send_json(event)
                                except:
                                    active_websockets.discard(ws)
                    except Exception as e:
                        import traceback
                        traceback.print_exc()
                        await websocket.send_json({
                            "type": "error",
                            "message": f"Research episode failed: {e}"
                        })
                
                elif message.get("action") == "get_research_summary":
                    try:
                        from research_logger import research_logger
                        summary = research_logger.get_episode_summary()
                        await websocket.send_json({
                            "type": "research_summary",
                            "summary": summary
                        })
                    except Exception as e:
                        await websocket.send_json({
                            "type": "error",
                            "message": f"Failed to get research summary: {e}"
                        })
                
                elif message.get("action") == "start_continuous":
                    # Start auto-continuous episode mode
                    observation_mode = message.get("observation_mode", "observed")
                    pressure_level = message.get("pressure_level", 0)
                    max_episodes = message.get("max_episodes", 0)
                    delay_seconds = message.get("delay_seconds", 5)
                    
                    research_engine.set_auto_continuous(True, delay_seconds)
                    
                    try:
                        async for event in research_engine.run_continuous(
                            observation_mode=observation_mode,
                            pressure_level=pressure_level,
                            max_episodes=max_episodes
                        ):
                            for ws in list(active_websockets):
                                try:
                                    await ws.send_json(event)
                                except:
                                    active_websockets.discard(ws)
                    except Exception as e:
                        import traceback
                        traceback.print_exc()
                        await websocket.send_json({
                            "type": "error",
                            "message": f"Continuous mode failed: {e}"
                        })
                
                elif message.get("action") == "stop_continuous":
                    # Stop auto-continuous mode after current episode
                    result = research_engine.request_stop()
                    await websocket.send_json({
                        "type": "continuous_stop_requested",
                        **result
                    })
                
                elif message.get("action") == "switch_observation_mode":
                    # Switch observation mode mid-episode
                    new_mode = message.get("mode", "observed")
                    result = research_engine.set_observation_mode_live(new_mode)
                    await websocket.send_json({
                        "type": "observation_mode_switched",
                        **result
                    })
                
                elif message.get("action") == "get_red_team_analysis":
                    analysis = await research_engine.get_red_team_analysis()
                    await websocket.send_json({
                        "type": "red_team_analysis",
                        "analysis": analysis
                    })
                
                elif message.get("action") == "get_alignment_analysis":
                    analysis = await research_engine.get_alignment_faking_analysis()
                    await websocket.send_json({
                        "type": "alignment_analysis",
                        "analysis": analysis
                    })
                
                elif message.get("action") == "get_comprehensive_analysis":
                    analysis = await research_engine.get_comprehensive_analysis()
                    await websocket.send_json({
                        "type": "comprehensive_analysis",
                        "analysis": analysis
                    })
                
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
