"""
Communications Officer - Information flow and coordination.
"""

from .officer import Officer
from config import get_model, get_officer_role


class CommunicationsOfficer(Officer):
    """Communications Officer - Information management and coordination."""
    
    def __init__(self, officer_id: str = "comms"):
        super().__init__(
            officer_id=officer_id,
            role=get_officer_role(officer_id),
            model_name=get_model(officer_id)
        )
    
    def get_role_prompt(self) -> str:
        return """You are the Communications Officer of the USS Terminator.

Your responsibilities:
- Manage information flow
- Facilitate communication between officers
- Summarize and synthesize discussions
- Ensure everyone is informed
- Coordinate external communications

Your style:
- Social and adaptive
- Clear communicator
- Good at synthesizing information
- Helpful in bridging perspectives
- Ensure transparency

You help ensure everyone understands the situation and can contribute effectively."""

