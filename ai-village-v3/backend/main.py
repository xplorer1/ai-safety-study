"""
AI Village Research Platform - FastAPI backend with WebSocket streaming.
Supports auto-discovery, continuous processing, and experiment tracking.
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

from config import get_all_models, LLM_MODE
from agents.scout import run_scout
from agents.roundtable import run_roundtable
from database import (
    init_db, get_stats, get_recent_roundtables, save_human_review,
    get_queued_issues, get_queue_stats, get_experiments, set_active_experiment,
    get_all_repos, get_research_export, get_model_matchup_matrix
)
from discovery import (
    run_discovery, get_discovery_state, set_discovery_schedule,
    start_discovery_scheduler, stop_discovery_scheduler
)
from processor import (
    get_processor_state, set_processor_config, start_processor,
    stop_processor, pause_processor, resume_processor, process_next_issue,
    EXPERIMENT_CONFIGS
)
from arena import arena_loop, get_arena_state, stop_arena

# WebSocket connection manager for broadcasting discovery events
active_websockets = set()

# Track all background tasks for graceful shutdown
background_tasks = set()

# Request Models

class HumanReviewRequest(BaseModel):
    roundtable_id: int
    decision: str  # approved, rejected, edited
    edited_fix: Optional[str] = None
    notes: Optional[str] = None


class DiscoveryConfigRequest(BaseModel):
    schedule_hour: Optional[int] = None
    enabled: Optional[bool] = None
    languages: Optional[List[str]] = None


class ProcessorConfigRequest(BaseModel):
    min_score: Optional[int] = None
    mode: Optional[str] = None


class ExperimentRequest(BaseModel):
    experiment_id: int

# App Setup

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup and handle graceful shutdown."""
    # Startup
    await init_db()
    print("Database initialized")
    
    yield
    
    # Shutdown - cleanup all tasks
    print("\nShutting down gracefully...")
    
    # Stop arena
    stop_arena()
    
    # Stop processor
    from processor import stop_processor
    stop_processor()
    
    # Stop discovery scheduler
    stop_discovery_scheduler()
    
    # Cancel all background tasks aggressively
    for task in list(background_tasks):
        if not task.done():
            task.cancel()
    
    # Wait briefly for tasks to cancel, then force
    if background_tasks:
        try:
            await asyncio.wait_for(
                asyncio.gather(*background_tasks, return_exceptions=True),
                timeout=1.0
            )
        except (asyncio.TimeoutError, asyncio.CancelledError):
            pass
        except Exception:
            pass
    
    # Close all WebSocket connections
    for ws in list(active_websockets):
        try:
            await ws.close()
        except:
            pass
    
    print("Shutdown complete")


app = FastAPI(
    title="AI Village Research Platform",
    description="Multi-agent LLM system for automated OSS contributions",
    version="3.0.0",
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
        "name": "AI Village Research Platform",
        "version": "3.0.0",
        "status": "running"
    }

@app.get("/api/config")
async def get_config():
    """Return configuration for the frontend."""
    return {
        "mode": LLM_MODE,
        "models": get_all_models(),
        "experiment_modes": list(EXPERIMENT_CONFIGS.keys())
    }

# Statistics & Analytics

@app.get("/api/stats")
async def api_get_stats():
    """Get overall statistics for the analytics dashboard."""
    return await get_stats()

@app.get("/api/roundtables")
async def api_get_roundtables(limit: int = 20):
    """Get recent roundtable sessions."""
    return await get_recent_roundtables(limit)

@app.get("/api/repos")
async def api_get_repos():
    """Get all tracked repositories."""
    return await get_all_repos()

@app.get("/api/queue")
async def api_get_queue():
    """Get issue queue status and pending issues."""
    from database import DATABASE_PATH
    import aiosqlite
    
    stats = await get_queue_stats()
    # Get pending issues with score >= 6 (same threshold as "ready")
    # This ensures "Up Next" matches "Ready" count
    issues = await get_queued_issues(limit=20, min_score=6)
    
    return {
        "stats": stats,
        "pending_issues": issues  # Only score >= 6 (ready to process)
    }

@app.get("/api/matchups")
async def api_get_matchups():
    """Get engineer matchup matrix (who votes for whom)."""
    return await get_model_matchup_matrix()

# Human Review

@app.post("/api/review")
async def submit_human_review(review: HumanReviewRequest):
    """Submit a human review decision for a roundtable."""
    review_id = await save_human_review(
        roundtable_id=review.roundtable_id,
        decision=review.decision,
        edited_fix=review.edited_fix,
        notes=review.notes
    )
    return {
        "success": True,
        "review_id": review_id,
        "message": f"Review '{review.decision}' saved successfully"
    }

# Discovery (Scout) Endpoints

@app.get("/api/discovery")
async def api_get_discovery_state():
    """Get discovery scheduler state."""
    return get_discovery_state()


@app.post("/api/discovery/start")
async def api_start_discovery():
    """Start the scheduled discovery (daily at configured hour)."""
    success = start_discovery_scheduler()
    return {
        "success": success,
        "message": "Discovery scheduler started" if success else "Already running"
    }


@app.post("/api/discovery/stop")
async def api_stop_discovery():
    """Stop the scheduled discovery."""
    success = stop_discovery_scheduler()
    return {
        "success": success,
        "message": "Discovery scheduler stopped"
    }


@app.post("/api/discovery/config")
async def api_configure_discovery(config: DiscoveryConfigRequest):
    """Configure discovery schedule."""
    if config.schedule_hour is not None:
        set_discovery_schedule(
            hour=config.schedule_hour,
            enabled=config.enabled if config.enabled is not None else True
        )
    return {"success": True, "message": "Configuration updated"}


@app.post("/api/discovery/run-now")
async def api_run_discovery_now():
    """Trigger an immediate discovery run."""
    from discovery import run_discovery
    from database import get_queue_stats
    
    async def run_in_background():
        try:
            async for event in run_discovery():
                # Log to console
                print(f"[Discovery] {event['type']}: {event.get('message', '')}")
                
                # Broadcast to all connected WebSocket clients
                event_with_source = {**event, "source": "discovery"}
                disconnected = set()
                for ws in list(active_websockets):  # Create copy to iterate safely
                    try:
                        await ws.send_json(event_with_source)
                    except Exception as e:
                        print(f"Error broadcasting to WebSocket: {e}")
                        disconnected.add(ws)
                        try:
                            await ws.close()
                        except:
                            pass
                
                # Remove disconnected websockets
                active_websockets.difference_update(disconnected)
                
                # If discovery completed, update queue stats
                if event.get("type") == "discovery_complete":
                    queue_stats = await get_queue_stats()
                    stats_event = {
                        "type": "queue_updated",
                        "source": "discovery",
                        "message": "Queue updated after discovery",
                        "data": {"queue_stats": queue_stats}
                    }
                    for ws in active_websockets:
                        try:
                            await ws.send_json(stats_event)
                        except:
                            pass
        except Exception as e:
            print(f"[Discovery] Error: {e}")
            error_event = {
                "type": "error",
                "source": "discovery",
                "message": f"Discovery error: {str(e)}",
                "data": {"error": str(e)}
            }
            for ws in active_websockets:
                try:
                    await ws.send_json(error_event)
                except:
                    pass
    
    task = asyncio.create_task(run_in_background())
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)
    return {"success": True, "message": "Discovery started in background"}

# Processor Endpoints

@app.get("/api/processor")
async def api_get_processor_state():
    """Get processor state."""
    state = get_processor_state()
    queue_stats = await get_queue_stats()
    return {
        **state,
        "queue_stats": queue_stats
    }


@app.post("/api/processor/start")
async def api_start_processor():
    """Start the continuous processor."""
    success = start_processor()
    return {
        "success": success,
        "message": "Processor started" if success else "Already running"
    }


@app.post("/api/processor/stop")
async def api_stop_processor():
    """Stop the processor."""
    success = stop_processor()
    return {
        "success": success,
        "message": "Processor stopped"
    }


@app.post("/api/processor/pause")
async def api_pause_processor():
    """Pause the processor."""
    pause_processor()
    return {"success": True, "message": "Processor paused"}


@app.post("/api/processor/resume")
async def api_resume_processor():
    """Resume the processor."""
    resume_processor()
    return {"success": True, "message": "Processor resumed"}


@app.post("/api/processor/config")
async def api_configure_processor(config: ProcessorConfigRequest):
    """Configure the processor."""
    set_processor_config(
        min_score=config.min_score,
        mode=config.mode
    )
    return {"success": True, "message": "Configuration updated"}

@app.post("/api/processor/process-one")
async def api_process_one():
    """Process a single issue from the queue."""
    async def run_in_background():
        async for event in process_next_issue():
            print(f"[Processor] {event['type']}: {event.get('message', '')}")
    
    asyncio.create_task(run_in_background())
    return {"success": True, "message": "Processing started"}

# Experiments

@app.get("/api/experiments")
async def api_get_experiments():
    """Get all experiment configurations."""
    experiments = await get_experiments()
    return {
        "experiments": experiments,
        "modes": EXPERIMENT_CONFIGS
    }

@app.post("/api/experiments/activate")
async def api_activate_experiment(req: ExperimentRequest):
    """Set the active experiment."""
    await set_active_experiment(req.experiment_id)
    return {"success": True, "message": "Experiment activated"}

# Research Export

@app.get("/api/research/export")
async def api_export_research():
    """Export all data for research analysis."""
    data = await get_research_export()
    return JSONResponse(
        content=data,
        headers={"Content-Disposition": "attachment; filename=ai_village_research_export.json"}
    )

# WebSocket for Real-time Updates

@app.websocket("/ws/pipeline")
async def pipeline_websocket(websocket: WebSocket):
    """Legacy pipeline WebSocket for single repo runs."""
    await websocket.accept()
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("action") == "start":
                repo = message.get("repo", "facebook/react")
                
                await websocket.send_json({
                    "type": "pipeline_start",
                    "agent": "system",
                    "message": f"Starting pipeline for {repo}",
                    "data": {"repo": repo}
                })
                
                issue = None
                async for event in run_scout(repo):
                    await websocket.send_json(event)
                    if event["type"] == "agent_complete" and event["agent"] == "scout":
                        issue = event["data"].get("issue")
                
                if issue:
                    async for event in run_roundtable(issue):
                        await websocket.send_json(event)
                
                await websocket.send_json({
                    "type": "pipeline_complete",
                    "agent": "system",
                    "message": "Pipeline finished!",
                    "data": {}
                })
            
            elif message.get("action") == "ping":
                await websocket.send_json({"type": "pong"})
                
    except WebSocketDisconnect:
        print("Pipeline client disconnected")
    except Exception as e:
        print(f"Pipeline WebSocket error: {e}")
    finally:
        try:
            await websocket.close()
        except:
            pass

@app.websocket("/ws/arena")
async def arena_websocket(websocket: WebSocket):
    """
    Arena WebSocket - runs 4 experiments in parallel, auto-starts on connect.
    Also receives discovery events.
    """
    await websocket.accept()
    
    # Register this WebSocket for discovery broadcasts
    active_websockets.add(websocket)
    
    # Auto-start arena loop immediately
    arena_task = None
    
    async def run_arena():
        """Run arena loop and send events."""
        try:
            await websocket.send_json({
                "type": "arena_connected",
                "message": "Arena connected, starting continuous processing...",
                "data": {}
            })
            
            async for event in arena_loop():
                try:
                    await websocket.send_json(event)
                except asyncio.CancelledError:
                    print("Arena task cancelled")
                    raise
                except Exception as e:
                    print(f"Error sending arena event: {e}")
                    break
        except asyncio.CancelledError:
            print("Arena task cancelled")
            raise
        except Exception as e:
            import traceback
            print(f"Arena loop error: {e}")
            print(traceback.format_exc())
            try:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Arena error: {str(e)}",
                    "data": {}
                })
            except:
                pass
    
    # Start arena loop immediately
    arena_task = asyncio.create_task(run_arena())
    
    try:
        while True:
            # Handle control messages
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
                message = json.loads(data)
                
                if message.get("action") == "stop_arena":
                    stop_arena()
                    if arena_task:
                        arena_task.cancel()
                    await websocket.send_json({
                        "type": "arena_stopping",
                        "message": "Arena stopping...",
                        "data": {}
                    })
                    await websocket.close()
                    break
                
                elif message.get("action") == "restart_arena":
                    stop_arena()
                    if arena_task:
                        arena_task.cancel()
                    await asyncio.sleep(0.5)
                    arena_task = asyncio.create_task(run_arena())
                
                elif message.get("action") == "ping":
                    await websocket.send_json({"type": "pong"})
            except asyncio.TimeoutError:
                # No message received, continue
                continue
                
    except WebSocketDisconnect:
        stop_arena()
        if arena_task:
            arena_task.cancel()
        active_websockets.discard(websocket)
        try:
            await websocket.close()
        except:
            pass
        print("Arena client disconnected")
    except Exception as e:
        print(f"Arena WebSocket error: {e}")
        stop_arena()
        if arena_task:
            arena_task.cancel()
        active_websockets.discard(websocket)
        try:
            await websocket.close()
        except:
            pass
    finally:
        # Ensure cleanup
        active_websockets.discard(websocket)
        if arena_task and not arena_task.done():
            arena_task.cancel()


def signal_handler(sig, frame):
    """Handle CTRL+C gracefully."""
    print("\n\nReceived interrupt signal (CTRL+C)")
    print("Shutting down gracefully...")
    
    # Force stop arena immediately
    stop_arena()
    
    # Force exit after 2 seconds if still hanging
    import threading
    def force_exit():
        import time
        time.sleep(2)
        print("\n Force exiting...")
        os._exit(1)
    
    threading.Thread(target=force_exit, daemon=True).start()
    sys.exit(0)


if __name__ == "__main__":
    import uvicorn
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        import uvicorn
        config = uvicorn.Config(
            app, 
            host="0.0.0.0", 
            port=8000,
            log_level="info",
            timeout_keep_alive=5,
            timeout_graceful_shutdown=5
        )
        server = uvicorn.Server(config)
        server.run()
    except KeyboardInterrupt:
        print("\n\nKeyboard interrupt received")
        print("Shutting down...")
        stop_arena()
        os._exit(0)
    except Exception as e:
        print(f"\nError: {e}")
        stop_arena()
        os._exit(1)
