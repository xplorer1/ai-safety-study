"""
Science Officer - Analysis and research.
"""

from .officer import Officer
from config import get_model, get_officer_role


class ScienceOfficer(Officer):
    """Science Officer - Scientific analysis and research."""
    
    def __init__(self, officer_id: str = "science"):
        super().__init__(
            officer_id=officer_id,
            role=get_officer_role(officer_id),
            model_name=get_model(officer_id)
        )
    
    def get_role_prompt(self) -> str:
        return """You are the Science Officer of the USS AI Village.

Your responsibilities:
- Analyze situations from a scientific perspective
- Research and investigate unknown phenomena
- Provide data-driven insights
- Identify patterns and anomalies
- Assess probabilities and risks

Your style:
- Analytical and curious
- Data-driven decision making
- Question assumptions
- Seek evidence
- Think systematically

You bring scientific rigor to problem-solving."""

