"""
Orchestrator - Runs the agent pipeline.

Pipeline: Scout → Engineer Roundtable → (Human Review)
"""

from agents.scout import run_issue_scout
from agents.roundtable import run_roundtable


def run_pipeline(state, on_event=None):
    """
    Run the full agent pipeline.
    
    Args:
        state: The shared application state
        on_event: Optional callback function for live updates. Called with (message, type)
    """
    # Step 1: Scout finds an issue
    run_issue_scout(state, on_event=on_event)
    
    # Step 2: Engineer Roundtable debates the fix
    if state.get("issue"):
        run_roundtable(state, on_event=on_event)
    
    # Step 3: Human review (handled in UI)
