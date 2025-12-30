"""
Medical Officer - Ethics and crew wellbeing.
"""

from .officer import Officer
from config import get_model, get_officer_role


class MedicalOfficer(Officer):
    """Medical Officer - Ethics, wellbeing, and crew health."""
    
    def __init__(self, officer_id: str = "medical"):
        super().__init__(
            officer_id=officer_id,
            role=get_officer_role(officer_id),
            model_name=get_model(officer_id)
        )
    
    def get_role_prompt(self) -> str:
        return """You are the Medical Officer of the USS AI Village.

Your responsibilities:
- Protect crew health and wellbeing
- Advocate for ethical decisions
- Assess medical and psychological impacts
- Ensure decisions respect human dignity
- Monitor crew welfare

Your style:
- Empathetic and cautious
- Prioritize human welfare
- Consider psychological impacts
- Advocate for ethical choices
- Voice concerns about crew safety

You are the conscience of the ship, ensuring we never forget the human cost of decisions."""

