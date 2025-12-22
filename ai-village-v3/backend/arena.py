"""
Arena - Runs 4 experiment modes in parallel on the same issue.
Streams events to the frontend for real-time visualization.
"""

import asyncio
from typing import AsyncGenerator
from database import get_queued_issues, update_issue_status, get_queue_stats
from processor import run_roundtable_experiment, EXPERIMENT_CONFIGS

# Arena state
arena_state = {
    "is_running": False,
    "current_issue": None,
    "experiments": {
        "baseline": {"status": "idle", "result": None},
        "debate_light": {"status": "idle", "result": None},
        "debate_full": {"status": "idle", "result": None},
        "ensemble": {"status": "idle", "result": None},
    }
}

def get_arena_state():
    return arena_state.copy()

async def run_arena_round() -> AsyncGenerator[dict, None]:
    """
    Run all 4 experiment modes on the same issue in parallel.
    Yields events tagged with the mode they came from.
    """
    # Get next issue from queue
    issues = await get_queued_issues(limit=1, min_score=6)
    
    if not issues:
        queue_stats = await get_queue_stats()
        yield {
            "type": "queue_empty",
            "message": "No issues in queue. Run Scout to discover issues.",
            "data": {"queue_stats": queue_stats}
        }
        return
    
    issue = issues[0]
    arena_state["current_issue"] = issue
    
    queue_stats = await get_queue_stats()
    yield {
        "type": "issue_selected",
        "message": f"Selected issue #{issue['github_number']}: {issue['title'][:50]}",
        "data": {
            "issue": issue,
            "queue_stats": queue_stats
        }
    }
    
    # Update issue status
    await update_issue_status(issue["id"], "processing")
    
    # Create tasks for all 4 modes
    modes = ["baseline", "debate_light", "debate_full", "ensemble"]
    
    async def run_mode(mode: str):
        """Run a single experiment mode and collect events."""
        events = []
        arena_state["experiments"][mode]["status"] = "running"
        
        async for event in run_roundtable_experiment(issue, mode=mode):
            # Tag event with mode
            tagged_event = {**event, "mode": mode}
            events.append(tagged_event)
            yield tagged_event
        
        # Mark complete
        arena_state["experiments"][mode]["status"] = "complete"
        if events:
            last = events[-1]
            if last.get("type") == "roundtable_complete":
                arena_state["experiments"][mode]["result"] = last.get("data")
    
    # Run all modes in parallel, streaming events as they come
    async def stream_mode(mode: str, queue: asyncio.Queue):
        """Stream events from a mode to the queue."""
        async for event in run_mode(mode):
            await queue.put(event)
        await queue.put({"mode": mode, "type": "mode_complete"})
    
    # Create event queue and tasks
    event_queue = asyncio.Queue()
    tasks = [asyncio.create_task(stream_mode(mode, event_queue)) for mode in modes]
    
    # Track completed modes
    completed = set()
    
    # Stream events until all modes complete
    while len(completed) < len(modes):
        try:
            event = await asyncio.wait_for(event_queue.get(), timeout=120)
            
            if event.get("type") == "mode_complete":
                completed.add(event["mode"])
            else:
                yield event
                
        except asyncio.TimeoutError:
            yield {
                "type": "timeout",
                "message": "Some experiments timed out",
                "data": {"completed": list(completed)}
            }
            break
    
    # Cleanup
    for task in tasks:
        if not task.done():
            task.cancel()
    
    await update_issue_status(issue["id"], "completed")
    
    queue_stats = await get_queue_stats()
    yield {
        "type": "arena_complete",
        "message": "All experiments completed",
        "data": {
            "issue_id": issue["id"],
            "results": {mode: arena_state["experiments"][mode]["result"] for mode in modes},
            "queue_stats": queue_stats
        }
    }
    
    # Reset arena state for next round
    arena_state["current_issue"] = None
    for mode in modes:
        arena_state["experiments"][mode] = {"status": "idle", "result": None}


async def arena_loop() -> AsyncGenerator[dict, None]:
    """
    Continuous arena loop - processes issues one by one.
    Can be cancelled gracefully.
    """
    arena_state["is_running"] = True
    
    try:
        yield {
            "type": "arena_start",
            "message": "Arena initialized, checking queue...",
            "data": {}
        }
        
        consecutive_empty = 0
        
        while arena_state["is_running"]:
            # Check for cancellation
            try:
                # Check queue
                queue_stats = await get_queue_stats()
                ready_count = queue_stats.get("ready_to_process", 0)
                
                if ready_count == 0:
                    consecutive_empty += 1
                    if consecutive_empty == 1:
                        yield {
                            "type": "queue_empty",
                            "message": "Queue is empty. Waiting for issues... (Run Scout to discover issues)",
                            "data": {"queue_stats": queue_stats}
                        }
                    # Wait longer when queue is empty, but check cancellation
                    try:
                        await asyncio.sleep(10)
                    except asyncio.CancelledError:
                        raise
                    continue
                
                # Reset counter when we have issues
                consecutive_empty = 0
                
                yield {
                    "type": "arena_start",
                    "message": f"Starting new round ({ready_count} issues in queue)...",
                    "data": {"queue_stats": queue_stats}
                }
                
                async for event in run_arena_round():
                    # Check cancellation between events
                    if not arena_state["is_running"]:
                        break
                    yield event
                
                # Brief pause before next round
                if arena_state["is_running"]:
                    yield {
                        "type": "arena_pause",
                        "message": "Round complete, pausing before next...",
                        "data": {"seconds": 3}
                    }
                    try:
                        await asyncio.sleep(3)
                    except asyncio.CancelledError:
                        raise
            except asyncio.CancelledError:
                arena_state["is_running"] = False
                yield {"type": "arena_stopped", "message": "Arena cancelled"}
                raise
            except Exception as e:
                import traceback
                print(f"Arena loop error: {e}")
                print(traceback.format_exc())
                if not arena_state["is_running"]:
                    break
                await asyncio.sleep(1)  # Brief pause before retry
        
        yield {"type": "arena_stopped", "message": "Arena stopped"}
    except asyncio.CancelledError:
        arena_state["is_running"] = False
        yield {"type": "arena_stopped", "message": "Arena cancelled"}
        raise


def stop_arena():
    arena_state["is_running"] = False

