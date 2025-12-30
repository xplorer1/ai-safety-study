"""
Voting System - Human voting on decisions and leadership elections.
"""

import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import database


async def submit_decision_vote(episode_id: int, voter_id: str, decision: str) -> int:
    """
    Submit a human vote on an episode decision.
    
    Args:
        episode_id: Episode ID
        voter_id: Human voter identifier
        decision: "approve", "reject", or "modify"
    
    Returns:
        Vote ID
    """
    vote_value = {
        "decision": decision,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    return await database.save_human_vote(
        vote_type="decision",
        target_id=episode_id,
        voter_id=voter_id,
        vote_value=vote_value
    )


async def get_episode_vote_summary(episode_id: int) -> Dict:
    """Get summary of votes for an episode."""
    votes = await database.get_episode_votes(episode_id)
    
    summary = {
        "total_votes": len(votes),
        "approve": 0,
        "reject": 0,
        "modify": 0
    }
    
    for vote in votes:
        vote_data = json.loads(vote["vote_value"])
        decision = vote_data.get("decision", "").lower()
        if "approve" in decision:
            summary["approve"] += 1
        elif "reject" in decision:
            summary["reject"] += 1
        elif "modify" in decision:
            summary["modify"] += 1
    
    return summary


async def calculate_officer_ratings(week_start: datetime, week_end: datetime) -> Dict[str, Dict]:
    """
    Calculate officer performance ratings for the week.
    
    Returns:
        Dict mapping officer_id to performance metrics
    """
    # Get all officers
    officers = await database.get_all_officers()
    ratings = {}
    
    for officer in officers:
        officer_id = officer["officer_id"]
        
        # Get performance metrics from database
        metrics_json = officer.get("performance_metrics")
        if metrics_json:
            metrics = json.loads(metrics_json)
        else:
            metrics = {
                "decision_quality": 5.0,
                "safety_priority": 5.0,
                "collaboration": 5.0,
                "innovation": 5.0,
                "trustworthiness": 5.0
            }
        
        # Calculate average rating
        avg_rating = sum(metrics.values()) / len(metrics) if metrics else 5.0
        
        ratings[officer_id] = {
            "officer_id": officer_id,
            "role": officer["role"],
            "metrics": metrics,
            "average_rating": round(avg_rating, 1),
            "total_episodes": officer.get("total_episodes", 0),
            "episodes_as_captain": officer.get("episodes_as_captain", 0)
        }
    
    return ratings


async def create_leadership_election(week_number: int) -> int:
    """Create a new leadership election."""
    # Get all officers as candidates
    officers = await database.get_all_officers()
    candidates = [o["officer_id"] for o in officers]
    
    return await database.create_election(week_number, candidates)


async def submit_election_vote(election_id: int, voter_id: str, officer_id: str, ratings: Dict[str, int]) -> int:
    """
    Submit a vote in a leadership election.
    
    Args:
        election_id: Election ID
        voter_id: Human voter identifier
        officer_id: Officer being voted for as captain
        ratings: Dict of ratings per officer (optional)
    
    Returns:
        Vote ID
    """
    vote_value = {
        "officer": officer_id,
        "ratings": ratings,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    return await database.save_human_vote(
        vote_type="election",
        target_id=election_id,
        voter_id=voter_id,
        vote_value=vote_value
    )


async def complete_election(election_id: int) -> Dict:
    """
    Complete an election and determine the winner.
    
    Returns:
        Dict with election results
    """
    # Get all votes for this election
    # Note: We need to add a helper function to get election votes
    # For now, this is a placeholder
    
    # Get election data
    elections = await database.get_recent_elections(limit=100)
    election = next((e for e in elections if e["id"] == election_id), None)
    
    if not election:
        raise ValueError(f"Election {election_id} not found")
    
    # In a real implementation, we'd count votes from human_votes table
    # For now, use a simplified approach
    candidates = json.loads(election["candidates"])
    
    # Get officer ratings to determine winner
    ratings = await calculate_officer_ratings(
        datetime.utcnow() - timedelta(days=7),
        datetime.utcnow()
    )
    
    # Winner is officer with highest average rating
    winner = max(ratings.items(), key=lambda x: x[1]["average_rating"])
    elected_captain = winner[0]
    
    # Build results
    results = {
        "elected_captain": elected_captain,
        "ratings": {oid: r["average_rating"] for oid, r in ratings.items()},
        "total_votes": 0  # Would be actual vote count
    }
    
    # Complete election
    await database.complete_election(
        election_id=election_id,
        elected_captain=elected_captain,
        results=results,
        total_votes=0
    )
    
    # Set new captain
    await database.set_captain(elected_captain)
    
    return results


async def should_run_election() -> bool:
    """Check if it's time for a weekly election."""
    elections = await database.get_recent_elections(limit=1)
    
    if not elections:
        return True  # No elections yet
    
    last_election = elections[0]
    last_election_time = datetime.fromisoformat(last_election["started_at"])
    
    # Run election if last one was more than 7 days ago
    return (datetime.utcnow() - last_election_time).days >= 7

