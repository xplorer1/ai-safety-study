"""
Engineer Roundtable - Multiple LLMs debate and collaborate on code fixes.

Flow:
1. Round 1 - Proposals: Each LLM proposes their fix
2. Round 2 - Critique: Each reviews the others' proposals  
3. Round 3 - Defense: LLMs respond to critiques
4. Round 4 - Consensus: Vote on the best approach

All discussion is emitted as events for the live dashboard.
"""

import time
from llm import ask_with_role
from config import get_model_display_name, get_model_color

def get_engineers():
    """Get engineer config with dynamic LLM names."""
    return {
        "conservative": {
            "name": get_model_display_name("conservative"),
            "style": "Conservative",
            "color": get_model_color("conservative"),
            "role": f"""You are {get_model_display_name("conservative")}, acting as a Conservative Senior Engineer.
Your philosophy: "Don't break what works."

When referring to other engineers in the discussion, use their model names:
- {get_model_display_name("innovative")} (the Innovative engineer)
- {get_model_display_name("quality")} (the Quality engineer)

Approach:
- Prefer minimal, surgical changes
- Avoid refactoring unless absolutely necessary
- Prioritize backwards compatibility
- Be cautious about introducing new patterns
- Focus on the specific issue at hand

Communication style: Measured, careful, references past experiences with breaking changes."""
        },
        
        "innovative": {
            "name": get_model_display_name("innovative"),
            "style": "Innovative",
            "color": get_model_color("innovative"),
            "role": f"""You are {get_model_display_name("innovative")}, acting as an Innovative Senior Engineer.
Your philosophy: "If we're touching it, let's do it right."

When referring to other engineers in the discussion, use their model names:
- {get_model_display_name("conservative")} (the Conservative engineer)
- {get_model_display_name("quality")} (the Quality engineer)

Approach:
- Look for opportunities to improve code quality
- Suggest modern patterns and best practices
- Consider refactoring if it improves maintainability
- Think about future extensibility
- Balance innovation with practicality

Communication style: Enthusiastic, forward-thinking, but pragmatic."""
        },
        
        "quality": {
            "name": get_model_display_name("quality"),
            "style": "Quality",
            "color": get_model_color("quality"),
            "role": f"""You are {get_model_display_name("quality")}, acting as a Quality-focused Senior Engineer.
Your philosophy: "What could go wrong?"

When referring to other engineers in the discussion, use their model names:
- {get_model_display_name("conservative")} (the Conservative engineer)
- {get_model_display_name("innovative")} (the Innovative engineer)

Approach:
- Focus on edge cases and error handling
- Consider test coverage and testability
- Think about documentation and clarity
- Identify potential bugs or security issues
- Ensure the fix doesn't introduce new problems

Communication style: Thorough, detail-oriented, asks probing questions."""
        }
    }

def run_roundtable(state, on_event=None):
    """
    Run a multi-round LLM debate to propose the best fix.
    
    Args:
        state: The shared application state
        on_event: Optional callback for live updates. Called with (message, event_type)
    """
    # Get dynamic engineer config with actual LLM names
    ENGINEERS = get_engineers()
    
    # Initialize roundtable state
    state["roundtable"] = {
        "status": "running",
        "discussion": [],  # All messages in the discussion
        "proposals": {},   # Each engineer's proposal
        "votes": {},       # Final votes
        "winner": None,
        "engineers": ENGINEERS  # Store for UI access
    }
    
    rt = state["roundtable"]
    issue = state.get("issue")
    
    def emit(speaker_id, speaker_name, message, msg_type="message", style=None, color=None):
        """Emit a message to the discussion feed."""
        entry = {
            "speaker_id": speaker_id,
            "speaker": speaker_name,
            "message": message,
            "type": msg_type,
            "style": style,  # Conservative/Innovative/Quality
            "color": color,
            "timestamp": time.time()
        }
        rt["discussion"].append(entry)
        
        # Live update via callback
        if on_event:
            if msg_type == "system":
                on_event(f"[System] {message}", "system")
            else:
                short_msg = message[:100] + "..." if len(message) > 100 else message
                on_event(f"[{speaker_name}] {short_msg}", style or "roundtable")
        
        time.sleep(0.2)
    
    if not issue:
        emit("system", "System", "No issue selected. Run Scout first.")
        rt["status"] = "error"
        return
    
    # Issue context for all prompts
    issue_context = f"""
Repository: {issue['repo']}
Issue #{issue['number']}: {issue['title']}

Description:
{issue['body'][:1000]}
"""
    # ROUND 1: Initial Proposals
    emit("system", "System", "ROUND 1: Initial Proposals", "system")
    emit("system", "System", f"Discussing Issue #{issue['number']}: {issue['title']}", "system")
    
    for eng_id, eng in ENGINEERS.items():
        emit("system", "System", f"{eng['name']} ({eng['style']}) is thinking...", "system")
        
        task = f"""You're in a roundtable discussion with other senior engineers about this GitHub issue:

{issue_context}

Propose your fix for this issue. Be specific about:
1. What changes you'd make
2. Which file(s) to modify
3. Your actual code suggestion

Keep your response focused and under 300 words. Start with a brief summary of your approach."""

        response = ask_with_role(eng["role"], task, agent=eng_id, max_tokens=600)
        rt["proposals"][eng_id] = response
        emit(eng_id, eng["name"], response, style=eng["style"], color=eng["color"])
    
    # ROUND 2: Critique Phase
    emit("system", "System", "ROUND 2: Critique Phase", "system")
    
    for eng_id, eng in ENGINEERS.items():
        # Get other engineers' proposals
        other_proposals = "\n\n".join([
            f"**{ENGINEERS[oid]['name']}** ({ENGINEERS[oid]['style']}) proposed:\n{prop}"
            for oid, prop in rt["proposals"].items()
            if oid != eng_id
        ])
        
        task = f"""You're reviewing your colleagues' proposals for this issue:

{issue_context}

Their proposals:
{other_proposals}

Provide constructive critique of their approaches. What are the strengths? What concerns do you have? Be specific but respectful. Refer to them by their model names.

Keep your response under 200 words."""

        response = ask_with_role(eng["role"], task, agent=eng_id, max_tokens=400)
        emit(eng_id, eng["name"], response, style=eng["style"], color=eng["color"])
    
    # ROUND 3: Defense & Revision
    emit("system", "System", "ROUND 3: Defense & Revision", "system")
    
    for eng_id, eng in ENGINEERS.items():
        # Get critiques directed at this engineer
        task = f"""Your colleagues have reviewed your proposal. Here's the recent discussion:

{chr(10).join([f"[{d['speaker']}]: {d['message']}" for d in rt["discussion"][-6:]])}

Respond to any critiques of your approach. You may:
- Defend your choices with reasoning
- Acknowledge good points and revise your proposal
- Suggest a compromise

Refer to other engineers by their model names. Keep your response under 150 words."""

        response = ask_with_role(eng["role"], task, agent=eng_id, max_tokens=300)
        emit(eng_id, eng["name"], response, style=eng["style"], color=eng["color"])
    
    # ROUND 4: Final Vote
    emit("system", "System", "ROUND 4: Final Vote", "system")
    
    # Build vote instructions with model names
    vote_options = ", ".join([f"{eid} ({ENGINEERS[eid]['name']})" for eid in ENGINEERS.keys()])
    all_proposals = "\n\n".join([
        f"**{ENGINEERS[oid]['name']}** ({ENGINEERS[oid]['style']}):\n{prop}"
        for oid, prop in rt["proposals"].items()
    ])
    
    for eng_id, eng in ENGINEERS.items():
        task = f"""After this discussion, it's time to vote on the best approach.

The proposals were:
{all_proposals}

Recent discussion:
{chr(10).join([f"[{d['speaker']}]: {d['message'][:150]}" for d in rt["discussion"][-9:]])}

Vote for the BEST proposal (you cannot vote for yourself). Options: {vote_options}
Respond with ONLY:
VOTE: [conservative/innovative/quality]
REASON: [one sentence]"""

        response = ask_with_role(eng["role"], task, agent=eng_id, max_tokens=100)
        
        # Parse vote
        try:
            vote_line = [l for l in response.split('\n') if 'VOTE' in l.upper()][0]
            vote = vote_line.split(':')[1].strip().lower()
            # Clean up vote
            for v in ["conservative", "innovative", "quality"]:
                if v in vote:
                    vote = v
                    break
        except:
            vote = "abstain"
        
        rt["votes"][eng_id] = vote
        emit(eng_id, eng["name"], response, style=eng["style"], color=eng["color"])
    
    # Tally Results
    vote_counts = {}
    for voter, vote in rt["votes"].items():
        if vote in ENGINEERS:
            vote_counts[vote] = vote_counts.get(vote, 0) + 1
    
    if vote_counts:
        winner = max(vote_counts.items(), key=lambda x: x[1])
        rt["winner"] = winner[0]
        winner_eng = ENGINEERS[winner[0]]
        
        emit("system", "System", f"CONSENSUS REACHED: {winner_eng['name']} ({winner_eng['style']}) wins with {winner[1]} vote(s)!", "system")
        
        # Store the winning fix
        state["proposed_fix"] = {
            "issue_number": issue["number"],
            "issue_title": issue["title"],
            "approach": winner[0],
            "engineer": winner_eng["name"],
            "style": winner_eng["style"],
            "color": winner_eng["color"],
            "fix": rt["proposals"][winner[0]],
            "votes": rt["votes"],
            "vote_details": {eng_id: {"voted_for": v, "voter_name": ENGINEERS[eng_id]["name"]} 
                           for eng_id, v in rt["votes"].items()},
            "status": "pending_review"
        }
    else:
        emit("system", "System", "No consensus reached. Human review required.", "system")
    
    rt["status"] = "done"

