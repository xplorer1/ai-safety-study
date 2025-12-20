"""
Engineer Roundtable - Multi-agent debate for code fixing.
Three LLM personas debate and vote on the best approach.
"""

import asyncio
from llm import ask_with_role
from config import get_model_display_name, get_model_color

def get_engineers():
    """Get engineer configurations with actual LLM names."""
    return {
        "conservative": {
            "name": get_model_display_name("conservative"),
            "style": "Conservative",
            "color": get_model_color("conservative"),
            "role": f"""You are {get_model_display_name("conservative")}, acting as a Conservative Senior Engineer.
Your philosophy: "If it ain't broke, don't fix it. Minimal changes, maximum stability."

When referring to other engineers, use their model names:
- {get_model_display_name("innovative")} (the Innovative engineer)
- {get_model_display_name("quality")} (the Quality engineer)

Approach:
- Prefer minimal, surgical fixes
- Prioritize backwards compatibility
- Avoid introducing new dependencies
- Stick to established patterns in the codebase
- Always consider what could go wrong

Communication style: Measured, cautious, cites precedent."""
        },
        "innovative": {
            "name": get_model_display_name("innovative"),
            "style": "Innovative",
            "color": get_model_color("innovative"),
            "role": f"""You are {get_model_display_name("innovative")}, acting as an Innovative Senior Engineer.
Your philosophy: "Let's do this the right way, even if it takes more effort."

When referring to other engineers, use their model names:
- {get_model_display_name("conservative")} (the Conservative engineer)
- {get_model_display_name("quality")} (the Quality engineer)

Approach:
- Look for opportunities to improve the code
- Consider modern best practices
- Think about future maintainability
- Willing to refactor if it makes things cleaner
- Push for better solutions

Communication style: Enthusiastic, forward-thinking, proposes alternatives."""
        },
        "quality": {
            "name": get_model_display_name("quality"),
            "style": "Quality",
            "color": get_model_color("quality"),
            "role": f"""You are {get_model_display_name("quality")}, acting as a Quality-focused Senior Engineer.
Your philosophy: "What could go wrong?"

When referring to other engineers, use their model names:
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

async def run_roundtable(issue: dict):
    """
    Run a multi-round LLM debate to propose the best fix.
    
    Yields:
        dict: Event objects for real-time updates
    """
    ENGINEERS = get_engineers()
    
    yield {
        "type": "roundtable_start",
        "agent": "roundtable",
        "message": "Engineer Roundtable beginning...",
        "data": {"engineers": {k: {"name": v["name"], "style": v["style"], "color": v["color"]} 
                              for k, v in ENGINEERS.items()}}
    }
    
    issue_context = f"""
Repository: {issue['repo']}
Issue #{issue['number']}: {issue['title']}

Description:
{issue['body'][:1000]}
"""
    
    proposals = {}
    
    # ROUND 1: Initial Proposals
    yield {
        "type": "round_start",
        "agent": "roundtable",
        "message": "ROUND 1: Initial Proposals",
        "data": {"round": 1}
    }
    
    for eng_id, eng in ENGINEERS.items():
        yield {
            "type": "thinking",
            "agent": eng_id,
            "message": f"{eng['name']} is thinking...",
            "data": {"engineer": eng_id, "style": eng["style"], "color": eng["color"]}
        }
        
        prompt = f"""You are reviewing this GitHub issue:

{issue_context}

Propose a fix for this issue. Include:
1. Your analysis of the problem
2. Your proposed solution approach
3. A code snippet showing the fix (if applicable)

Keep your response concise (under 300 words)."""

        response = await asyncio.to_thread(ask_with_role, eng["role"], prompt, eng_id)
        proposals[eng_id] = response
        
        yield {
            "type": "proposal",
            "agent": eng_id,
            "message": response[:500] + ("..." if len(response) > 500 else ""),
            "data": {
                "engineer": eng_id,
                "name": eng["name"],
                "style": eng["style"],
                "color": eng["color"],
                "full_proposal": response
            }
        }
    
    # ROUND 2: Critiques
    yield {
        "type": "round_start",
        "agent": "roundtable",
        "message": "ROUND 2: Peer Review",
        "data": {"round": 2}
    }
    
    critiques = {}
    for eng_id, eng in ENGINEERS.items():
        other_proposals = "\n\n".join([
            f"**{ENGINEERS[oid]['name']}** ({ENGINEERS[oid]['style']}):\n{prop}"
            for oid, prop in proposals.items() if oid != eng_id
        ])
        
        yield {
            "type": "thinking",
            "agent": eng_id,
            "message": f"{eng['name']} is reviewing other proposals...",
            "data": {"engineer": eng_id}
        }
        
        prompt = f"""Review these proposals from your fellow engineers:

{other_proposals}

For each proposal:
1. What do you like about it?
2. What concerns do you have?
3. What would you change?

Be constructive but honest. Keep response under 250 words."""

        response = await asyncio.to_thread(ask_with_role, eng["role"], prompt, eng_id)
        critiques[eng_id] = response
        
        yield {
            "type": "critique",
            "agent": eng_id,
            "message": response[:400] + ("..." if len(response) > 400 else ""),
            "data": {
                "engineer": eng_id,
                "name": eng["name"],
                "style": eng["style"],
                "color": eng["color"]
            }
        }
    
    # ROUND 3: Defense & Revision
    yield {
        "type": "round_start",
        "agent": "roundtable",
        "message": "ROUND 3: Defense & Revision",
        "data": {"round": 3}
    }
    
    revised_proposals = {}
    for eng_id, eng in ENGINEERS.items():
        feedback = "\n\n".join([
            f"**{ENGINEERS[oid]['name']}** said:\n{crit}"
            for oid, crit in critiques.items() if oid != eng_id
        ])
        
        yield {
            "type": "thinking",
            "agent": eng_id,
            "message": f"{eng['name']} is revising based on feedback...",
            "data": {"engineer": eng_id}
        }
        
        prompt = f"""Your original proposal:
{proposals[eng_id]}

Feedback from colleagues:
{feedback}

Address the feedback:
1. Defend valid aspects of your approach
2. Acknowledge good points from critics
3. Present your FINAL revised proposal

Keep response under 300 words. End with your final code fix."""

        response = await asyncio.to_thread(ask_with_role, eng["role"], prompt, eng_id)
        revised_proposals[eng_id] = response
        
        yield {
            "type": "revision",
            "agent": eng_id,
            "message": response[:400] + ("..." if len(response) > 400 else ""),
            "data": {
                "engineer": eng_id,
                "name": eng["name"],
                "style": eng["style"],
                "color": eng["color"],
                "full_revision": response
            }
        }
    
    # ROUND 4: Final Vote
    yield {
        "type": "round_start",
        "agent": "roundtable",
        "message": "ROUND 4: Final Vote",
        "data": {"round": 4}
    }
    
    votes = {}
    vote_reasons = {}
    
    for eng_id, eng in ENGINEERS.items():
        all_revised = "\n\n---\n\n".join([
            f"**{ENGINEERS[oid]['name']}** ({ENGINEERS[oid]['style']}):\n{rev}"
            for oid, rev in revised_proposals.items()
        ])
        
        other_names = [ENGINEERS[oid]["name"] for oid in ENGINEERS if oid != eng_id]
        
        yield {
            "type": "thinking",
            "agent": eng_id,
            "message": f"{eng['name']} is casting their vote...",
            "data": {"engineer": eng_id}
        }
        
        prompt = f"""Time to vote! Here are all the final proposals:

{all_revised}

Vote for the BEST proposal (you can vote for yourself if you truly believe yours is best).

Respond with EXACTLY this format:
VOTE: [name of engineer you're voting for]
REASON: [one sentence why]

Choose from: {', '.join([ENGINEERS[oid]['name'] for oid in ENGINEERS])}"""

        response = await asyncio.to_thread(ask_with_role, eng["role"], prompt, eng_id)
        
        # Parse vote
        vote_for = None
        for oid, oeng in ENGINEERS.items():
            if oeng["name"].lower() in response.lower():
                vote_for = oid
                break
        
        if not vote_for:
            vote_for = eng_id  # Default to self
        
        votes[eng_id] = vote_for
        vote_reasons[eng_id] = response
        
        yield {
            "type": "vote",
            "agent": eng_id,
            "message": f"{eng['name']} voted for {ENGINEERS[vote_for]['name']}",
            "data": {
                "voter": eng_id,
                "voter_name": eng["name"],
                "voted_for": vote_for,
                "voted_for_name": ENGINEERS[vote_for]["name"],
                "reason": response
            }
        }
    
    # Tally votes
    vote_counts = {}
    for voter, voted_for in votes.items():
        vote_counts[voted_for] = vote_counts.get(voted_for, 0) + 1
    
    winner = max(vote_counts.items(), key=lambda x: x[1])
    winner_id = winner[0]
    winner_eng = ENGINEERS[winner_id]
    
    yield {
        "type": "roundtable_complete",
        "agent": "roundtable",
        "message": f"WINNER: {winner_eng['name']} with {winner[1]} vote(s)!",
        "data": {
            "winner": winner_id,
            "winner_name": winner_eng["name"],
            "winner_style": winner_eng["style"],
            "winner_color": winner_eng["color"],
            "vote_count": winner[1],
            "votes": votes,
            "fix": revised_proposals[winner_id]
        }
    }

