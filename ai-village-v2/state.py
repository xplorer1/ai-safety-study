"""
Shared state for the AI Village application.
All agents read from and write to this state.
"""

def init_state():
    return {
        # Selected GitHub issue (set by Scout)
        "issue": None,
        
        # Proposed code fix (set by Roundtable winner)
        "proposed_fix": None,
        
        # Roundtable discussion state
        "roundtable": {
            "status": "idle",
            "discussion": [],
            "proposals": {},
            "votes": {},
            "winner": None
        },
        
        # Agent states
        "agents": {
            "scout": {
                "status": "idle",
                "events": []
            },
            "fixer": {
                "status": "idle",
                "events": []
            },
            "reviewer": {
                "status": "idle",
                "events": []
            }
        },
        
        # Final decision (human approval)
        "final_decision": None
    }
