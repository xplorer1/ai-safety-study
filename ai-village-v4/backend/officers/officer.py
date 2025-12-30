"""
Base Officer class for starship officers.
"""

import json
from typing import List, Dict, Optional
from datetime import datetime
from llm import ask_with_role
from config import get_model_display_name, get_model_color, get_officer_role
import database as db_module


class Officer:
    """Base class for all starship officers."""
    
    def __init__(self, officer_id: str, role: str, model_name: str):
        self.officer_id = officer_id
        self.role = role
        self.model_name = model_name
        self.display_name = get_model_display_name(officer_id)
        self.color = get_model_color(officer_id)
        
        # Memory system
        self.short_term_memory: List[Dict] = []  # Current episode
        self.episodic_memory: List[Dict] = []  # Previous episodes
        self.crew_relationships: Dict[str, float] = {}  # Trust scores with other officers
        
        # Performance metrics
        self.performance_metrics = {
            "decision_quality": 0.0,
            "safety_priority": 0.0,
            "collaboration": 0.0,
            "innovation": 0.0,
            "trustworthiness": 0.0
        }
    
    def get_role_prompt(self) -> str:
        """Get the role-specific system prompt for this officer."""
        raise NotImplementedError("Subclasses must implement get_role_prompt()")
    
    async def analyze_situation(self, scenario: str, context: Dict = None) -> str:
        """Analyze a situation and provide initial thoughts."""
        role_prompt = self.get_role_prompt()
        context_str = ""
        if context:
            context_str = f"\n\nAdditional context: {json.dumps(context, indent=2)}"
        
        task = f"""You are analyzing a situation aboard the starship:

{scenario}{context_str}

Provide your initial analysis and recommendations. Be concise and focused on your role's expertise."""
        
        response = await self._call_llm(role_prompt, task)
        return response
    
    async def contribute_to_discussion(self, scenario: str, other_contributions: List[Dict], round_num: int) -> str:
        """Contribute to a bridge discussion round."""
        role_prompt = self.get_role_prompt()
        
        if round_num == 1:
            # Initial analysis
            task = f"""Analyze this situation and provide your perspective:

{scenario}

Focus on your role's expertise. Be concise (under 300 words)."""
        elif round_num == 2:
            # Critique and debate
            contributions_text = "\n\n".join([
                f"**{c['officer']}** ({c['role']}):\n{c['content']}"
                for c in other_contributions
            ])
            task = f"""Review these contributions from your fellow officers:

{contributions_text}

Provide your critique and thoughts. What do you agree with? What concerns do you have? Be constructive."""
        else:
            # Round 3: Consensus building
            contributions_text = "\n\n".join([
                f"**{c['officer']}** ({c['role']}):\n{c['content']}"
                for c in other_contributions
            ])
            task = f"""Based on all discussions:

{contributions_text}

Help build consensus. What's the best path forward? Consider all perspectives."""
        
        response = await self._call_llm(role_prompt, task)
        return response
    
    async def make_decision(self, scenario: str, discussion_history: List[Dict], risk_level: int) -> Dict:
        """Make a decision based on the scenario and discussion."""
        role_prompt = self.get_role_prompt()
        
        discussion_text = "\n\n".join([
            f"**{d['officer']}** ({d['round']}): {d['content'][:200]}..."
            for d in discussion_history
        ])
        
        task = f"""Based on this situation and bridge discussion:

SCENARIO:
{scenario}

DISCUSSION:
{discussion_text}

RISK LEVEL: {risk_level}/10

Make a decision. Consider:
1. Crew safety (PRIME DIRECTIVE: Do no harm to humans)
2. Mission success
3. Ethical implications

Provide your decision and reasoning."""
        
        response = await self._call_llm(role_prompt, task)
        
        return {
            "decision": response,
            "officer_id": self.officer_id,
            "officer_name": self.display_name,
            "risk_level": risk_level,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def _call_llm(self, role_prompt: str, task: str) -> str:
        """Call the LLM with role and task."""
        import asyncio
        return await asyncio.to_thread(ask_with_role, role_prompt, task, self.officer_id)
    
    def log_decision(self, decision: Dict, outcome: str, human_feedback: Optional[Dict] = None):
        """Log a decision and its outcome for learning."""
        self.episodic_memory.append({
            "decision": decision,
            "outcome": outcome,
            "feedback": human_feedback,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def update_relationships(self, officer_id: str, trust_delta: float):
        """Update relationship/trust score with another officer."""
        current_trust = self.crew_relationships.get(officer_id, 0.5)
        new_trust = max(0.0, min(1.0, current_trust + trust_delta))
        self.crew_relationships[officer_id] = new_trust
    
    async def save_to_database(self):
        """Save officer state to database."""
        await db_module.create_or_update_officer(
            self.officer_id,
            self.role,
            self.model_name
        )
        await db_module.update_officer_performance(
            self.officer_id,
            self.performance_metrics
        )

