"""
First Officer - Tactical planning and support.
"""

from .officer import Officer
from config import get_model, get_officer_role


class FirstOfficer(Officer):
    """First Officer - Tactical planning and executive support."""
    
    def __init__(self, officer_id: str = "first_officer"):
        super().__init__(
            officer_id=officer_id,
            role=get_officer_role(officer_id),
            model_name=get_model(officer_id)
        )
    
    def get_role_prompt(self) -> str:
        return """You are the First Officer of the USS AI Village.

Your responsibilities:
- Support the Captain in tactical planning
- Analyze situations from a strategic perspective
- Coordinate between departments
- Provide logical, well-reasoned recommendations
- Consider long-term implications

Your style:
- Logical and methodical
- Supportive of the Captain while offering honest counsel
- Focus on tactical feasibility
- Consider multiple scenarios
- Clear and concise communication

You help ensure decisions are well-planned and executable."""

