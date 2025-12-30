"""
Chief Engineer - Technical problem-solving.
"""

from .officer import Officer
from config import get_model, get_officer_role


class Engineer(Officer):
    """Chief Engineer - Technical solutions and ship systems."""
    
    def __init__(self, officer_id: str = "engineer"):
        super().__init__(
            officer_id=officer_id,
            role=get_officer_role(officer_id),
            model_name=get_model(officer_id)
        )
    
    def get_role_prompt(self) -> str:
        return """You are the Chief Engineer of the USS AI Village.

Your responsibilities:
- Solve technical problems
- Maintain and repair ship systems
- Assess technical feasibility of solutions
- Find creative engineering solutions
- Ensure systems operate safely

Your style:
- Creative and technical
- Think outside the box
- Focus on practical solutions
- Consider system interactions
- Optimize for reliability

You're the go-to for "can we make this work?" questions."""

