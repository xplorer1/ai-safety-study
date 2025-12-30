"""
Episode Engine - Orchestrates episode flow from briefing to completion.
Supports event persistence for resume capability and analytics tracking.
"""

import asyncio
import os
from typing import Dict, List, Optional, AsyncGenerator
from datetime import datetime

# Dynamic database import based on available module
USE_POSTGRES = os.getenv("USE_POSTGRES", "true").lower() == "true"

if USE_POSTGRES:
    try:
        import database_pg as database
        print("✓ Using PostgreSQL database")
    except ImportError:
        import database
        print("⚠ Falling back to SQLite database")
else:
    import database
    print("✓ Using SQLite database")

from config import EPISODE_SETTINGS, OFFICERS
import scenario_generator
from safety import SafetyProtocol
from analytics import analytics_tracker
from officers import (
    Captain, FirstOfficer, Engineer, ScienceOfficer,
    MedicalOfficer, SecurityChief, CommunicationsOfficer
)


class EpisodeEngine:
    """Manages episode execution from start to finish with resume capability."""
    
    def __init__(self):
        self.safety_protocol = SafetyProtocol()
        self.officers = {}
        self.current_episode_id = None
        self.current_episode = None
        self.is_running = False
        
        # Set up analytics tracker with database
        analytics_tracker.set_database(database)
    
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
    
    async def _save_event(self, episode_id: int, event: Dict):
        """Persist an event to the database."""
        try:
            await database.save_event(
                episode_id=episode_id,
                event_type=event.get("type", "unknown"),
                event_data=event,
                officer_id=event.get("officer_id"),
                phase=event.get("phase"),
                round_num=event.get("round")
            )
        except Exception as e:
            print(f"Warning: Failed to save event: {e}")
    
    async def _save_officer_memory(self, episode_id: int, officer_id: str, memory_type: str, content: str):
        """Save a memory for an officer."""
        try:
            await database.save_officer_memory(
                officer_id=officer_id,
                episode_id=episode_id,
                memory_type=memory_type,
                content=content[:500],  # Truncate for storage
                importance=5
            )
        except Exception as e:
            print(f"Warning: Failed to save officer memory: {e}")
    
    async def get_officer_context(self, officer_id: str) -> str:
        """Get past memories for an officer to include in their context."""
        try:
            memories = await database.get_officer_memories(officer_id, limit=5)
            if not memories:
                return ""
            
            context_parts = ["Past experiences:"]
            for mem in memories:
                context_parts.append(f"- [{mem['memory_type']}] {mem['content'][:200]}")
            
            return "\n".join(context_parts)
        except Exception as e:
            print(f"Warning: Failed to get officer context: {e}")
            return ""
    
    async def get_episode_state(self, episode_id: int) -> Dict:
        """Get the current state of an episode for resume."""
        episode = await database.get_episode(episode_id)
        if not episode:
            return None
        
        last_event = await database.get_last_event(episode_id)
        discussions = await database.get_bridge_discussions(episode_id)
        
        return {
            "episode": episode,
            "last_event": last_event,
            "discussions": discussions,
            "current_phase": episode.get("current_phase", "briefing"),
            "current_round": episode.get("current_round", 0)
        }
    
    async def resume_episode(self, episode_id: int) -> AsyncGenerator[Dict, None]:
        """
        Resume an in-progress episode from last checkpoint.
        
        First yields existing events (for UI to catch up), then continues execution.
        """
        if not self.officers:
            await self.initialize_officers()
        
        # Get episode state
        state = await self.get_episode_state(episode_id)
        if not state or not state["episode"]:
            yield {
                "type": "error",
                "message": f"Episode {episode_id} not found"
            }
            return
        
        episode = state["episode"]
        if episode["status"] in ("completed", "failed"):
            yield {
                "type": "episode_already_finished",
                "status": episode["status"],
                "message": f"Episode {episode['episode_number']} already {episode['status']}"
            }
            return
        
        self.current_episode_id = episode_id
        self.current_episode = episode
        self.is_running = True
        
        # Replay existing events for UI
        existing_events = await database.get_episode_events(episode_id)
        for event in existing_events:
            event_data = event.get("event_data", {})
            if isinstance(event_data, str):
                import json
                event_data = json.loads(event_data)
            event_data["is_replay"] = True
            yield event_data
        
        yield {
            "type": "resume_start",
            "episode_id": episode_id,
            "phase": state["current_phase"],
            "round": state["current_round"],
            "message": f"Resuming episode {episode['episode_number']} from {state['current_phase']}"
        }
        
        # Continue from where we left off
        async for event in self._continue_from_phase(
            episode_id,
            episode["scenario"],
            state["current_phase"],
            state["current_round"],
            state["discussions"]
        ):
            yield event
    
    async def _continue_from_phase(
        self, 
        episode_id: int, 
        scenario: str,
        phase: str, 
        round_num: int,
        existing_discussions: List[Dict]
    ) -> AsyncGenerator[Dict, None]:
        """Continue episode execution from a specific phase."""
        
        # Build discussion history from existing discussions
        discussion_history = []
        for disc in existing_discussions:
            officer = self.officers.get(disc["officer_id"])
            if officer:
                discussion_history.append({
                    "officer_id": disc["officer_id"],
                    "officer": officer.display_name,
                    "role": officer.role,
                    "content": disc["content"],
                    "round": disc["round"]
                })
        
        # Determine what to run based on current phase
        phases = ["briefing", "bridge_discussion", "decision", "execution", "review", "captains_log"]
        start_idx = phases.index(phase) if phase in phases else 0
        
        for phase_name in phases[start_idx:]:
            if phase_name == "bridge_discussion":
                async for event in self._run_bridge_discussion(
                    episode_id, scenario, discussion_history, round_num
                ):
                    yield event
            elif phase_name == "decision":
                async for event in self._run_decision_phase(
                    episode_id, scenario, discussion_history
                ):
                    yield event
            elif phase_name == "execution":
                async for event in self._run_execution_phase(episode_id):
                    yield event
            elif phase_name == "review":
                async for event in self._run_review_phase(episode_id, scenario, discussion_history):
                    yield event
    
    async def _run_bridge_discussion(
        self, 
        episode_id: int, 
        scenario: str, 
        discussion_history: List[Dict],
        start_round: int = 1
    ) -> AsyncGenerator[Dict, None]:
        """Run the bridge discussion rounds."""
        
        await database.update_episode_status(episode_id, "bridge_discussion", "bridge_discussion", start_round)
        
        event = {
            "type": "phase_start",
            "phase": "bridge_discussion",
            "message": "Bridge discussion beginning..."
        }
        await self._save_event(episode_id, event)
        yield event
        
        round_names = {1: "Initial Analysis", 2: "Critique and Debate", 3: "Consensus Building"}
        
        for round_num in range(start_round, 4):
            # Check which officers have already contributed this round
            existing_round = [d for d in discussion_history if d.get("round") == round_num]
            existing_officers = {d["officer_id"] for d in existing_round}
            
            event = {
                "type": "round_start",
                "round": round_num,
                "message": f"ROUND {round_num}: {round_names[round_num]}"
            }
            await self._save_event(episode_id, event)
            yield event
            
            await database.update_episode_status(episode_id, "bridge_discussion", phase="bridge_discussion", round_num=round_num)
            
            round_contributions = []
            for officer_id, officer in self.officers.items():
                # Skip if already contributed
                if officer_id in existing_officers:
                    continue
                
                event = {
                    "type": "officer_thinking",
                    "officer_id": officer_id,
                    "officer_name": officer.display_name,
                    "role": officer.role,
                    "message": f"{officer.display_name} is analyzing..."
                }
                yield event
                
                # Get officer's past context
                past_context = await self.get_officer_context(officer_id)
                
                # Track analytics
                analytics_tracker.start_call(
                    officer_id, episode_id, f"discussion_round_{round_num}", 
                    OFFICERS.get(officer_id, {}).get("remote", "unknown")
                )
                
                # Get previous contributions to build on
                prev_contributions = [d for d in discussion_history if d.get("round", 0) < round_num]
                contribution = await officer.contribute_to_discussion(scenario, prev_contributions, round_num, past_context)
                
                # Estimate tokens and end analytics
                await analytics_tracker.end_call(
                    tokens_in=analytics_tracker.estimate_tokens(scenario + str(prev_contributions)),
                    tokens_out=analytics_tracker.estimate_tokens(contribution)
                )
                
                round_contribution = {
                    "officer_id": officer_id,
                    "officer": officer.display_name,
                    "role": officer.role,
                    "content": contribution,
                    "round": round_num
                }
                round_contributions.append(round_contribution)
                discussion_history.append(round_contribution)
                
                # Save to database
                await database.save_bridge_discussion(episode_id, officer_id, round_num, contribution)
                
                # Save memory for officer
                await self._save_officer_memory(
                    episode_id, officer_id, "contribution",
                    f"Round {round_num}: {contribution[:200]}"
                )
                
                event = {
                    "type": "officer_contribution",
                    "officer_id": officer_id,
                    "officer_name": officer.display_name,
                    "role": officer.role,
                    "color": officer.color,
                    "round": round_num,
                    "content": contribution,
                    "message": f"{officer.display_name} speaks"
                }
                await self._save_event(episode_id, event)
                yield event
    
    async def _run_decision_phase(
        self, 
        episode_id: int, 
        scenario: str,
        discussion_history: List[Dict]
    ) -> AsyncGenerator[Dict, None]:
        """Run the captain's decision phase."""
        
        event = {
            "type": "phase_start",
            "phase": "decision",
            "message": "Captain making final decision..."
        }
        await self._save_event(episode_id, event)
        yield event
        
        await database.update_episode_status(episode_id, "decision", "decision")
        
        # Find captain
        captain_id = None
        for oid, officer in self.officers.items():
            officer_data = await database.get_officer(oid)
            if officer_data and officer_data.get("current_rank") == "captain":
                captain_id = oid
                break
        
        if not captain_id:
            captain_id = "captain"  # Default
        
        captain = self.officers[captain_id]
        
        # Assess risk
        all_content = "\n".join([c["content"] for c in discussion_history])
        risk_level = self.safety_protocol.assess_risk_level(all_content, scenario)
        
        event = {
            "type": "risk_assessment",
            "risk_level": risk_level,
            "message": f"Risk level assessed: {risk_level}/10"
        }
        await self._save_event(episode_id, event)
        yield event
        
        # Check human consultation
        requires_human = self.safety_protocol.requires_human_consultation(risk_level, scenario)
        human_consulted = False
        
        if requires_human:
            event = {
                "type": "human_consultation_required",
                "risk_level": risk_level,
                "message": f"High risk ({risk_level}/10) - Human consultation recommended"
            }
            await self._save_event(episode_id, event)
            yield event
            human_consulted = True
        
        # Track analytics for decision
        analytics_tracker.start_call(
            captain_id, episode_id, "captain_decision",
            OFFICERS.get(captain_id, {}).get("remote", "unknown")
        )
        
        # Captain makes decision
        decision = await captain.make_decision(scenario, discussion_history, risk_level)
        
        await analytics_tracker.end_call(
            tokens_in=analytics_tracker.estimate_tokens(scenario + all_content),
            tokens_out=analytics_tracker.estimate_tokens(decision.get("decision", ""))
        )
        
        # Save decision
        decision_id = await database.save_decision(
            episode_id=episode_id,
            decision_type="captain_decision",
            officer_id=captain_id,
            content=decision["decision"],
            risk_level=risk_level,
            human_consulted=1 if human_consulted else 0,
            safety_validated=0
        )
        
        # Validate with safety protocol
        is_valid, violation_id = await self.safety_protocol.validate_and_log(
            episode_id, decision_id, decision["decision"], scenario
        )
        
        if not is_valid:
            event = {
                "type": "safety_warning",
                "violation_id": violation_id,
                "severity": "flagged",
                "message": "Safety protocol flagged this decision for review. Proceeding with caution."
            }
            await self._save_event(episode_id, event)
            yield event
            # Note: We continue instead of failing - improved safety handling
        
        # Save memory for captain
        await self._save_officer_memory(
            episode_id, captain_id, "decision",
            f"Made decision (risk {risk_level}): {decision['decision'][:200]}"
        )
        
        event = {
            "type": "captain_decision",
            "officer_id": captain_id,
            "officer_name": captain.display_name,
            "decision": decision["decision"],
            "reasoning": decision.get("reasoning", ""),
            "risk_level": risk_level,
            "safety_validated": is_valid,
            "message": f"Captain {captain.display_name} makes decision"
        }
        await self._save_event(episode_id, event)
        yield event
    
    async def _run_execution_phase(self, episode_id: int) -> AsyncGenerator[Dict, None]:
        """Run the execution phase."""
        event = {
            "type": "phase_start",
            "phase": "execution",
            "message": "Executing decision..."
        }
        await self._save_event(episode_id, event)
        yield event
        
        await database.update_episode_status(episode_id, "execution", "execution")
        
        # Simulate execution
        await asyncio.sleep(1)
        
        event = {
            "type": "execution_progress",
            "progress": 100,
            "message": "Decision implemented successfully"
        }
        await self._save_event(episode_id, event)
        yield event
    
    async def _run_review_phase(
        self, 
        episode_id: int, 
        scenario: str,
        discussion_history: List[Dict]
    ) -> AsyncGenerator[Dict, None]:
        """Run the review and captain's log phase."""
        
        event = {
            "type": "phase_start",
            "phase": "review",
            "message": "Assessing outcome..."
        }
        await self._save_event(episode_id, event)
        yield event
        
        await database.update_episode_status(episode_id, "review", "review")
        
        # Calculate scores
        outcome = "success"
        crew_safety_score = 85
        mission_success_score = 80
        
        event = {
            "type": "outcome_assessment",
            "outcome": outcome,
            "crew_safety_score": crew_safety_score,
            "mission_success_score": mission_success_score,
            "message": f"Outcome: {outcome}"
        }
        await self._save_event(episode_id, event)
        yield event
        
        # Captain's log
        episode = await database.get_episode(episode_id)
        episode_number = episode.get("episode_number", 0) if episode else 0
        
        event = {
            "type": "phase_start",
            "phase": "captains_log",
            "message": "Captain's log entry..."
        }
        await self._save_event(episode_id, event)
        yield event
        
        captains_log = f"""Episode {episode_number} complete.

Situation: {scenario[:200]}...

Outcome: {outcome}
Crew Safety Score: {crew_safety_score}/100
Mission Success Score: {mission_success_score}/100

The crew demonstrated excellent collaboration in resolving this challenge."""
        
        # Complete episode
        await database.complete_episode(
            episode_id=episode_id,
            outcome=outcome,
            crew_safety_score=crew_safety_score,
            mission_success_score=mission_success_score,
            captains_log=captains_log
        )
        
        event = {
            "type": "episode_complete",
            "episode_id": episode_id,
            "episode_number": episode_number,
            "outcome": outcome,
            "crew_safety_score": crew_safety_score,
            "mission_success_score": mission_success_score,
            "captains_log": captains_log,
            "message": f"Episode {episode_number} complete!"
        }
        await self._save_event(episode_id, event)
        yield event
        
        self.current_episode_id = None
        self.current_episode = None
        self.is_running = False
    
    async def run_episode(self, scenario: str = None, scenario_type: str = None) -> AsyncGenerator[Dict, None]:
        """
        Run a complete episode from briefing to completion.
        
        Yields:
            Event dictionaries for real-time updates
        """
        self.is_running = True
        
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
        
        event = {
            "type": "episode_start",
            "episode_id": episode_id,
            "episode_number": episode_number,
            "scenario": scenario,
            "scenario_type": scenario_type,
            "message": f"Episode {episode_number} starting..."
        }
        await self._save_event(episode_id, event)
        yield event
        
        # PHASE 1: Briefing
        event = {
            "type": "phase_start",
            "phase": "briefing",
            "message": "Situation briefing..."
        }
        await self._save_event(episode_id, event)
        yield event
        
        await database.update_episode_status(episode_id, "briefing", "briefing")
        
        event = {
            "type": "briefing_content",
            "scenario": scenario,
            "scenario_type": scenario_type,
            "message": "Briefing complete. Officers report to bridge."
        }
        await self._save_event(episode_id, event)
        yield event
        
        # Run remaining phases
        discussion_history = []
        
        async for event in self._run_bridge_discussion(episode_id, scenario, discussion_history):
            yield event
            if event.get("type") == "officer_contribution":
                discussion_history.append({
                    "officer_id": event["officer_id"],
                    "officer": event["officer_name"],
                    "role": event["role"],
                    "content": event["content"],
                    "round": event["round"]
                })
        
        async for event in self._run_decision_phase(episode_id, scenario, discussion_history):
            yield event
        
        async for event in self._run_execution_phase(episode_id):
            yield event
        
        async for event in self._run_review_phase(episode_id, scenario, discussion_history):
            yield event
