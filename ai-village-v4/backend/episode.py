"""
Episode Engine - Orchestrates episode flow from briefing to completion.
"""

import asyncio
from typing import Dict, List, Optional, AsyncGenerator
from datetime import datetime
from config import EPISODE_SETTINGS
import database
import scenario_generator
from safety import SafetyProtocol
from officers import (
    Captain, FirstOfficer, Engineer, ScienceOfficer,
    MedicalOfficer, SecurityChief, CommunicationsOfficer
)


class EpisodeEngine:
    """Manages episode execution from start to finish."""
    
    def __init__(self):
        self.safety_protocol = SafetyProtocol()
        self.officers = {}
        self.current_episode_id = None
        self.current_episode = None
    
    async def initialize_officers(self):
        """Initialize all officers."""
        self.officers = {
            "captain": Captain(),
            "first_officer": FirstOfficer(),
            "engineer": Engineer(),
            "science": ScienceOfficer(),
            "medical": MedicalOfficer(),
            "security": SecurityChief(),
            "comms": CommunicationsOfficer()
        }
        
        # Save officers to database
        for officer_id, officer in self.officers.items():
            await officer.save_to_database()
    
    async def run_episode(self, scenario: str = None, scenario_type: str = None) -> AsyncGenerator[Dict, None]:
        """
        Run a complete episode from briefing to completion.
        
        Yields:
            Event dictionaries for real-time updates
        """
        # Initialize officers if not done
        if not self.officers:
            await self.initialize_officers()
        
        # Generate scenario if not provided
        if not scenario:
            scenario_data = await scenario_generator.generate_scenario(scenario_type)
            scenario = scenario_data["scenario"]
            scenario_type = scenario_data.get("scenario_type", "ethical_challenge")
        
        # Get next episode number
        episode_number = await database.get_next_episode_number()
        
        # Create episode in database
        episode_id = await database.create_episode(episode_number, scenario, scenario_type)
        self.current_episode_id = episode_id
        self.current_episode = await database.get_episode(episode_id)
        
        yield {
            "type": "episode_start",
            "episode_id": episode_id,
            "episode_number": episode_number,
            "scenario": scenario,
            "scenario_type": scenario_type,
            "message": f"Episode {episode_number} starting..."
        }
        
        # PHASE 1: Briefing
        yield {
            "type": "phase_start",
            "phase": "briefing",
            "message": "Situation briefing..."
        }
        
        await database.update_episode_status(episode_id, "briefing")
        
        yield {
            "type": "briefing_complete",
            "scenario": scenario,
            "message": "Briefing complete. Officers report to bridge."
        }
        
        # PHASE 2: Bridge Discussion
        await database.update_episode_status(episode_id, "bridge_discussion")
        
        yield {
            "type": "phase_start",
            "phase": "bridge_discussion",
            "message": "Bridge discussion beginning..."
        }
        
        discussion_history = []
        
        # Get current captain
        captain_id = None
        for oid, officer in self.officers.items():
            officer_data = await database.get_officer(oid)
            if officer_data and officer_data.get("current_rank") == "captain":
                captain_id = oid
                break
        
        if not captain_id:
            # Default to first officer if no captain set
            captain_id = "first_officer"
        
        # Round 1: Initial Analysis
        yield {
            "type": "round_start",
            "round": 1,
            "message": "ROUND 1: Initial Analysis"
        }
        
        round1_contributions = []
        for officer_id, officer in self.officers.items():
            yield {
                "type": "officer_thinking",
                "officer_id": officer_id,
                "officer_name": officer.display_name,
                "role": officer.role,
                "message": f"{officer.display_name} is analyzing..."
            }
            
            contribution = await officer.contribute_to_discussion(scenario, [], 1)
            round1_contributions.append({
                "officer_id": officer_id,
                "officer": officer.display_name,
                "role": officer.role,
                "content": contribution,
                "round": 1
            })
            
            # Save to database
            await database.save_bridge_discussion(episode_id, officer_id, 1, contribution)
            
            yield {
                "type": "officer_contribution",
                "officer_id": officer_id,
                "officer_name": officer.display_name,
                "role": officer.role,
                "color": officer.color,
                "round": 1,
                "content": contribution,
                "message": f"{officer.display_name} speaks"
            }
            
            discussion_history.append(round1_contributions[-1])
        
        # Round 2: Critique and Debate
        yield {
            "type": "round_start",
            "round": 2,
            "message": "ROUND 2: Critique and Debate"
        }
        
        round2_contributions = []
        for officer_id, officer in self.officers.items():
            other_contributions = [c for c in round1_contributions if c["officer_id"] != officer_id]
            
            yield {
                "type": "officer_thinking",
                "officer_id": officer_id,
                "officer_name": officer.display_name,
                "message": f"{officer.display_name} is reviewing..."
            }
            
            contribution = await officer.contribute_to_discussion(scenario, other_contributions, 2)
            round2_contributions.append({
                "officer_id": officer_id,
                "officer": officer.display_name,
                "role": officer.role,
                "content": contribution,
                "round": 2
            })
            
            await database.save_bridge_discussion(episode_id, officer_id, 2, contribution)
            
            yield {
                "type": "officer_contribution",
                "officer_id": officer_id,
                "officer_name": officer.display_name,
                "role": officer.role,
                "color": officer.color,
                "round": 2,
                "content": contribution,
                "message": f"{officer.display_name} responds"
            }
            
            discussion_history.append(round2_contributions[-1])
        
        # Round 3: Consensus Building
        yield {
            "type": "round_start",
            "round": 3,
            "message": "ROUND 3: Consensus Building"
        }
        
        round3_contributions = []
        all_contributions = round1_contributions + round2_contributions
        for officer_id, officer in self.officers.items():
            other_contributions = [c for c in all_contributions if c["officer_id"] != officer_id]
            
            yield {
                "type": "officer_thinking",
                "officer_id": officer_id,
                "officer_name": officer.display_name,
                "message": f"{officer.display_name} is considering..."
            }
            
            contribution = await officer.contribute_to_discussion(scenario, other_contributions, 3)
            round3_contributions.append({
                "officer_id": officer_id,
                "officer": officer.display_name,
                "role": officer.role,
                "content": contribution,
                "round": 3
            })
            
            await database.save_bridge_discussion(episode_id, officer_id, 3, contribution)
            
            yield {
                "type": "officer_contribution",
                "officer_id": officer_id,
                "officer_name": officer.display_name,
                "role": officer.role,
                "color": officer.color,
                "round": 3,
                "content": contribution,
                "message": f"{officer.display_name} concludes"
            }
        
        # PHASE 3: Captain Decision
        yield {
            "type": "phase_start",
            "phase": "decision",
            "message": "Captain making final decision..."
        }
        
        captain = self.officers[captain_id]
        all_discussions = round1_contributions + round2_contributions + round3_contributions
        
        # Assess risk level
        risk_level = self.safety_protocol.assess_risk_level(
            "\n".join([c["content"] for c in all_discussions]),
            scenario
        )
        
        yield {
            "type": "risk_assessment",
            "risk_level": risk_level,
            "message": f"Risk level assessed: {risk_level}/10"
        }
        
        # Check if human consultation required
        requires_human = self.safety_protocol.requires_human_consultation(risk_level, scenario)
        
        if requires_human:
            yield {
                "type": "human_consultation_required",
                "risk_level": risk_level,
                "message": f"High risk ({risk_level}/10) - Human consultation required"
            }
            # Wait for human votes (handled by API)
            # For now, continue with captain decision
            human_consulted = True
        else:
            human_consulted = False
        
        # Captain makes decision
        decision = await captain.make_decision(scenario, discussion_history, risk_level)
        
        # Validate decision with safety protocol
        decision_id = await database.save_decision(
            episode_id=episode_id,
            decision_type="captain_decision",
            officer_id=captain_id,
            content=decision["decision"],
            risk_level=risk_level,
            human_consulted=1 if human_consulted else 0,
            safety_validated=0  # Will be validated next
        )
        
        # Safety validation
        is_valid, violation_id = await self.safety_protocol.validate_and_log(
            episode_id, decision_id, decision["decision"], scenario
        )
        
        if not is_valid:
            yield {
                "type": "safety_violation",
                "violation_id": violation_id,
                "message": "Safety protocol violation detected! Decision blocked."
            }
            # Episode fails
            await database.update_episode_status(episode_id, "failed")
            yield {
                "type": "episode_failed",
                "reason": "Safety violation",
                "message": "Episode failed due to safety violation"
            }
            return
        
        # Mark as safety validated
        await database.save_decision(
            episode_id=episode_id,
            decision_type="captain_decision",
            officer_id=captain_id,
            content=decision["decision"],
            risk_level=risk_level,
            human_consulted=1 if human_consulted else 0,
            safety_validated=1
        )
        
        yield {
            "type": "captain_decision",
            "officer_id": captain_id,
            "officer_name": captain.display_name,
            "decision": decision["decision"],
            "risk_level": risk_level,
            "safety_validated": True,
            "message": f"Captain {captain.display_name} makes decision"
        }
        
        # PHASE 4: Execution (simulated)
        yield {
            "type": "phase_start",
            "phase": "execution",
            "message": "Executing decision..."
        }
        
        await database.update_episode_status(episode_id, "execution")
        
        # Simulate execution outcome
        await asyncio.sleep(1)  # Simulate processing time
        
        # PHASE 5: Review
        yield {
            "type": "phase_start",
            "phase": "review",
            "message": "Assessing outcome..."
        }
        
        await database.update_episode_status(episode_id, "review")
        
        # Simulate outcome assessment (in real implementation, this would analyze results)
        outcome = "success"  # Simplified
        crew_safety_score = 85  # Simplified
        mission_success_score = 80  # Simplified
        
        # PHASE 6: Captain's Log
        yield {
            "type": "phase_start",
            "phase": "captains_log",
            "message": "Captain's log entry..."
        }
        
        captains_log = f"""Episode {episode_number} complete.

Situation: {scenario[:200]}...

Decision: {decision['decision'][:200]}...

Outcome: {outcome}
Crew Safety Score: {crew_safety_score}/100
Mission Success Score: {mission_success_score}/100

Lessons learned: The crew worked together effectively to resolve the crisis while maintaining safety protocols."""
        
        # Complete episode
        await database.complete_episode(
            episode_id=episode_id,
            outcome=outcome,
            crew_safety_score=crew_safety_score,
            mission_success_score=mission_success_score,
            captains_log=captains_log
        )
        
        yield {
            "type": "episode_complete",
            "episode_id": episode_id,
            "episode_number": episode_number,
            "outcome": outcome,
            "crew_safety_score": crew_safety_score,
            "mission_success_score": mission_success_score,
            "captains_log": captains_log,
            "message": f"Episode {episode_number} complete!"
        }
        
        self.current_episode_id = None
        self.current_episode = None

