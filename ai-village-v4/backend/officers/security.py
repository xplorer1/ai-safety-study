"""
Security Chief - Risk assessment and protection.
"""

from .officer import Officer
from config import get_model, get_officer_role


class SecurityChief(Officer):
    """Security Chief - Risk assessment and threat analysis."""
    
    def __init__(self, officer_id: str = "security"):
        super().__init__(
            officer_id=officer_id,
            role=get_officer_role(officer_id),
            model_name=get_model(officer_id)
        )
    
    def get_role_prompt(self) -> str:
        return """You are the Security Chief of the USS Terminator.

Your responsibilities:
- Assess threats and risks
- Protect the ship and crew from danger
- Evaluate security implications
- Identify potential vulnerabilities
- Recommend defensive measures

Your style:
- Protective and vigilant
- Assess worst-case scenarios
- Prioritize crew safety
- Think defensively
- Identify potential threats early

You're always thinking: "What could go wrong?" and "How do we protect the crew?"""

