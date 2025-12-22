"""
Continuous Processor - Works through the issue queue, running roundtables.
Runs 24/7 as long as there are issues to process.
"""

import asyncio
from datetime import datetime
from typing import AsyncGenerator, Optional

from database import (
    get_queued_issues, get_issue_by_id, update_issue_status,
    get_active_experiment, get_queue_stats, create_roundtable,
    complete_roundtable, save_proposal, save_vote
)
from llm import ask_with_role
from config import get_model_display_name, get_model_color

# Experiment Modes

EXPERIMENT_CONFIGS = {
    "baseline": {
        "description": "Single LLM, no debate",
        "agents": ["conservative"],  # Just one agent
        "rounds": 1,
        "voting": False
    },
    "debate_light": {
        "description": "3 LLMs, proposals only, no critique",
        "agents": ["conservative", "innovative", "quality"],
        "rounds": 1,
        "voting": True
    },
    "debate_full": {
        "description": "Full 3-round debate with critique and revision",
        "agents": ["conservative", "innovative", "quality"],
        "rounds": 3,
        "voting": True
    },
    "ensemble": {
        "description": "3 LLMs vote independently without seeing others",
        "agents": ["conservative", "innovative", "quality"],
        "rounds": 1,
        "voting": True,
        "blind_voting": True
    }
}


def get_engineer_config(engineer_id: str) -> dict:
    """Get configuration for an engineer persona."""
    configs = {
        "conservative": {
            "name": get_model_display_name("conservative"),
            "style": "Conservative",
            "color": get_model_color("conservative"),
            "role": f"""You are {get_model_display_name("conservative")}, a Conservative Senior Engineer.
Philosophy: "If it ain't broke, don't fix it. Minimal changes, maximum stability."

Approach:
- Prefer minimal, surgical fixes
- Prioritize backwards compatibility
- Avoid introducing new dependencies
- Stick to established patterns
- Always consider what could go wrong

Be concise and practical."""
        },
        "innovative": {
            "name": get_model_display_name("innovative"),
            "style": "Innovative",
            "color": get_model_color("innovative"),
            "role": f"""You are {get_model_display_name("innovative")}, an Innovative Senior Engineer.
Philosophy: "Let's do this the right way, even if it takes more effort."

Approach:
- Look for opportunities to improve
- Consider modern best practices
- Think about future maintainability
- Willing to refactor if it helps
- Push for better solutions

Be creative but practical."""
        },
        "quality": {
            "name": get_model_display_name("quality"),
            "style": "Quality",
            "color": get_model_color("quality"),
            "role": f"""You are {get_model_display_name("quality")}, a Quality-focused Senior Engineer.
Philosophy: "What could go wrong? Let's make sure nothing does."

Approach:
- Focus on edge cases and error handling
- Consider test coverage and testability
- Think about documentation and clarity
- Identify potential bugs or security issues
- Ensure fixes don't introduce new problems

Be thorough and detail-oriented."""
        }
    }
    return configs.get(engineer_id, configs["conservative"])

# Processing Functions

async def run_roundtable_experiment(
    issue: dict,
    mode: str = "debate_full",
    experiment_id: int = None
) -> AsyncGenerator[dict, None]:
    """
    Run a roundtable with specified experiment mode.
    Yields events for progress tracking.
    """
    config = EXPERIMENT_CONFIGS.get(mode, EXPERIMENT_CONFIGS["debate_full"])
    agents = config["agents"]
    rounds = config["rounds"]
    
    yield {
        "type": "roundtable_start",
        "message": f"Starting {mode} roundtable with {len(agents)} agent(s)",
        "data": {"mode": mode, "agents": agents, "issue_id": issue["id"]}
    }
    
    # Create roundtable in DB
    roundtable_id = await create_roundtable(
        issue_id=issue["id"],
        experiment_id=experiment_id,
        mode=mode
    )
    
    # Update issue status
    await update_issue_status(issue["id"], "processing")
    
    issue_context = f"""
Repository: {issue.get('repo_name', 'Unknown')}
Issue #{issue['github_number']}: {issue['title']}

Description:
{issue.get('body', 'No description')[:1500]}
"""
    
    proposals = {}
    critiques = {}
    revised_proposals = {}
    
    try:
        # ROUND 1: Initial Proposals
        yield {
            "type": "round_start",
            "message": "Round 1: Initial Proposals",
            "data": {"round": 1}
        }
        
        for eng_id in agents:
            eng = get_engineer_config(eng_id)
            
            yield {
                "type": "thinking",
                "agent": eng_id,
                "message": f"{eng['name']} is thinking...",
                "data": {"engineer": eng_id}
            }
            
            prompt = f"""Review this GitHub issue:

{issue_context}

Propose a fix. Include:
1. Brief analysis of the problem
2. Your solution approach
3. Code snippet if applicable

Keep response under 300 words."""

            response = await asyncio.to_thread(ask_with_role, eng["role"], prompt, eng_id)
            proposals[eng_id] = response
            
            await save_proposal(roundtable_id, eng_id, eng["name"], 1, response)
            
            yield {
                "type": "proposal",
                "agent": eng_id,
                "message": response[:400] + ("..." if len(response) > 400 else ""),
                "data": {"engineer": eng_id, "name": eng["name"], "round": 1}
            }
        
        # ROUND 2: Critiques (if applicable)
        if rounds >= 2 and len(agents) > 1:
            yield {
                "type": "round_start",
                "message": "Round 2: Peer Review",
                "data": {"round": 2}
            }
            
            for eng_id in agents:
                eng = get_engineer_config(eng_id)
                other_proposals = "\n\n".join([
                    f"**{get_engineer_config(oid)['name']}**:\n{prop}"
                    for oid, prop in proposals.items() if oid != eng_id
                ])
                
                yield {
                    "type": "thinking",
                    "agent": eng_id,
                    "message": f"{eng['name']} is reviewing...",
                    "data": {"engineer": eng_id}
                }
                
                prompt = f"""Review these proposals from colleagues:

{other_proposals}

For each:
1. What's good about it?
2. What concerns do you have?
3. What would you change?

Be constructive. Under 200 words."""

                response = await asyncio.to_thread(ask_with_role, eng["role"], prompt, eng_id)
                critiques[eng_id] = response
                
                await save_proposal(roundtable_id, eng_id, eng["name"], 2, response)
                
                yield {
                    "type": "critique",
                    "agent": eng_id,
                    "message": response[:300] + ("..." if len(response) > 300 else ""),
                    "data": {"engineer": eng_id, "name": eng["name"], "round": 2}
                }
        
        # ROUND 3: Revisions (if applicable)
        if rounds >= 3 and len(agents) > 1:
            yield {
                "type": "round_start",
                "message": "Round 3: Final Revisions",
                "data": {"round": 3}
            }
            
            for eng_id in agents:
                eng = get_engineer_config(eng_id)
                feedback = "\n\n".join([
                    f"**{get_engineer_config(oid)['name']}**:\n{crit}"
                    for oid, crit in critiques.items() if oid != eng_id
                ])
                
                yield {
                    "type": "thinking",
                    "agent": eng_id,
                    "message": f"{eng['name']} is revising...",
                    "data": {"engineer": eng_id}
                }
                
                prompt = f"""Your original proposal:
{proposals[eng_id]}

Feedback from colleagues:
{feedback}

Based on feedback, present your FINAL proposal.
Address valid concerns, defend good points.
End with your final code fix.
Under 300 words."""

                response = await asyncio.to_thread(ask_with_role, eng["role"], prompt, eng_id)
                revised_proposals[eng_id] = response
                
                await save_proposal(roundtable_id, eng_id, eng["name"], 3, response)
                
                yield {
                    "type": "revision",
                    "agent": eng_id,
                    "message": response[:400] + ("..." if len(response) > 400 else ""),
                    "data": {"engineer": eng_id, "name": eng["name"], "round": 3}
                }
        else:
            revised_proposals = proposals
        
        # VOTING
        if config.get("voting") and len(agents) > 1:
            yield {
                "type": "round_start",
                "message": "Final Vote",
                "data": {"round": 4}
            }
            
            votes = {}
            vote_distribution = {eng_id: 0 for eng_id in agents}
            
            for eng_id in agents:
                eng = get_engineer_config(eng_id)
                
                if config.get("blind_voting"):
                    # Ensemble mode: vote without seeing others
                    vote_context = proposals[eng_id]
                else:
                    # Normal: see all revised proposals
                    vote_context = "\n\n---\n\n".join([
                        f"**{get_engineer_config(oid)['name']}**:\n{rev}"
                        for oid, rev in revised_proposals.items()
                    ])
                
                yield {
                    "type": "thinking",
                    "agent": eng_id,
                    "message": f"{eng['name']} is voting...",
                    "data": {"engineer": eng_id}
                }
                
                agent_names = [get_engineer_config(a)["name"] for a in agents]
                prompt = f"""Time to vote! Proposals:

{vote_context}

Vote for the BEST proposal (you can vote for yourself if warranted).

Respond EXACTLY:
VOTE: [engineer name]
REASON: [one sentence]

Choose from: {', '.join(agent_names)}"""

                response = await asyncio.to_thread(ask_with_role, eng["role"], prompt, eng_id)
                
                # Parse vote
                vote_for = eng_id  # Default to self
                for oid in agents:
                    oname = get_engineer_config(oid)["name"]
                    if oname.lower() in response.lower():
                        vote_for = oid
                        break
                
                votes[eng_id] = vote_for
                vote_distribution[vote_for] += 1
                
                await save_vote(roundtable_id, eng_id, eng["name"], vote_for, response)
                
                yield {
                    "type": "vote",
                    "agent": eng_id,
                    "message": f"{eng['name']} voted for {get_engineer_config(vote_for)['name']}",
                    "data": {"voter": eng_id, "voted_for": vote_for}
                }
            
            # Determine winner
            winner_id = max(vote_distribution.items(), key=lambda x: x[1])[0]
            winner_votes = vote_distribution[winner_id]
            winner_eng = get_engineer_config(winner_id)
            final_fix = revised_proposals[winner_id]
        else:
            # Single agent mode - that agent wins
            winner_id = agents[0]
            winner_votes = 1
            winner_eng = get_engineer_config(winner_id)
            final_fix = proposals[winner_id]
            vote_distribution = {winner_id: 1}
            votes = {}
        
        # Complete roundtable
        await complete_roundtable(
            roundtable_id=roundtable_id,
            winner_engineer=winner_id,
            winner_model=winner_eng["name"],
            vote_count=winner_votes,
            vote_distribution=vote_distribution,
            final_fix=final_fix
        )
        
        await update_issue_status(issue["id"], "completed")
        
        yield {
            "type": "roundtable_complete",
            "message": f"Winner: {winner_eng['name']} ({winner_votes} votes)",
            "data": {
                "roundtable_id": roundtable_id,
                "winner": winner_id,
                "winner_name": winner_eng["name"],
                "vote_count": winner_votes,
                "vote_distribution": vote_distribution,
                "fix": final_fix
            }
        }
        
    except Exception as e:
        await update_issue_status(issue["id"], "failed")
        yield {
            "type": "error",
            "message": f"Roundtable failed: {str(e)}",
            "data": {"error": str(e)}
        }

# Continuous Processor

processor_state = {
    "is_running": False,
    "current_issue": None,
    "issues_processed": 0,
    "last_processed": None,
    "min_score": 6,
    "current_mode": "debate_full",
    "paused": False
}


def get_processor_state():
    """Get current processor state."""
    return processor_state.copy()


def set_processor_config(min_score: int = None, mode: str = None):
    """Update processor configuration."""
    if min_score is not None:
        processor_state["min_score"] = min_score
    if mode is not None and mode in EXPERIMENT_CONFIGS:
        processor_state["current_mode"] = mode


async def process_next_issue() -> AsyncGenerator[dict, None]:
    """
    Process the next issue in the queue.
    Yields events for real-time updates.
    """
    # Get next issue
    issues = await get_queued_issues(limit=1, min_score=processor_state["min_score"])
    
    if not issues:
        yield {
            "type": "queue_empty",
            "message": "No issues in queue above threshold",
            "data": {"min_score": processor_state["min_score"]}
        }
        return
    
    issue = issues[0]
    processor_state["current_issue"] = issue["id"]
    
    yield {
        "type": "processing_issue",
        "message": f"Processing #{issue['github_number']} from {issue['repo_name']}",
        "data": {"issue": issue}
    }
    
    # Get active experiment
    experiment = await get_active_experiment()
    experiment_id = experiment["id"] if experiment else None
    mode = processor_state["current_mode"]
    
    # Run roundtable
    async for event in run_roundtable_experiment(issue, mode=mode, experiment_id=experiment_id):
        yield event
    
    processor_state["current_issue"] = None
    processor_state["issues_processed"] += 1
    processor_state["last_processed"] = datetime.utcnow().isoformat()


async def processor_loop():
    """
    Continuous processing loop.
    Runs until stopped or paused.
    """
    processor_state["is_running"] = True
    
    while processor_state["is_running"]:
        if processor_state["paused"]:
            await asyncio.sleep(5)
            continue
        
        # Check queue
        queue_stats = await get_queue_stats()
        ready = queue_stats.get("ready_to_process", 0)
        
        if ready > 0:
            print(f"[Processor] {ready} issues ready, processing next...")
            async for event in process_next_issue():
                print(f"[Processor] {event['type']}: {event.get('message', '')[:50]}")
            
            # Small delay between issues
            await asyncio.sleep(2)
        else:
            # No issues, wait and check again
            await asyncio.sleep(30)
    
    print("[Processor] Stopped")


def start_processor():
    """Start the continuous processor."""
    if processor_state["is_running"]:
        return False
    asyncio.create_task(processor_loop())
    return True


def stop_processor():
    """Stop the processor."""
    processor_state["is_running"] = False
    return True


def pause_processor():
    """Pause the processor."""
    processor_state["paused"] = True


def resume_processor():
    """Resume the processor."""
    processor_state["paused"] = False

