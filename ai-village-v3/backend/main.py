"""
AI Village Backend - FastAPI server with WebSocket streaming.
"""

import asyncio
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from config import get_all_models, LLM_MODE
from agents.scout import run_scout
from agents.roundtable import run_roundtable

app = FastAPI(title="AI Village API", version="1.0.0")

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "AI Village API", "status": "running"}


@app.get("/api/config")
async def get_config():
    """Return configuration for the frontend."""
    return {
        "mode": LLM_MODE,
        "models": get_all_models()
    }


@app.websocket("/ws/pipeline")
async def pipeline_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for running the pipeline with real-time updates.
    
    Client sends: {"action": "start", "repo": "owner/repo"}
    Server streams: Event objects as they happen
    """
    await websocket.accept()
    
    try:
        while True:
            # Wait for client message
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("action") == "start":
                repo = message.get("repo", "pandas-dev/pandas")
                
                # Send pipeline start event
                await websocket.send_json({
                    "type": "pipeline_start",
                    "agent": "system",
                    "message": f"Starting AI Village Pipeline for {repo}",
                    "data": {"repo": repo}
                })
                
                # Run Scout
                issue = None
                async for event in run_scout(repo):
                    await websocket.send_json(event)
                    
                    # Capture the selected issue
                    if event["type"] == "agent_complete" and event["agent"] == "scout":
                        issue = event["data"].get("issue")
                
                # Run Roundtable if we have an issue
                if issue:
                    async for event in run_roundtable(issue):
                        await websocket.send_json(event)
                else:
                    await websocket.send_json({
                        "type": "error",
                        "agent": "system",
                        "message": "No issue selected, skipping roundtable",
                        "data": {}
                    })
                
                # Pipeline complete
                await websocket.send_json({
                    "type": "pipeline_complete",
                    "agent": "system",
                    "message": "Pipeline finished!",
                    "data": {}
                })
            
            elif message.get("action") == "ping":
                await websocket.send_json({"type": "pong"})
                
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "agent": "system",
                "message": str(e),
                "data": {}
            })
        except:
            pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)