"""
Captain - Elected leader who makes final decisions.
"""

from .officer import Officer
from config import get_model_display_name


class Captain(Officer):
    """Captain - The elected leader of the starship."""
    
    def __init__(self, officer_id: str = "captain"):
        from config import get_model, get_model_display_name, get_officer_role
        super().__init__(
            officer_id=officer_id,
            role=get_officer_role(officer_id),
            model_name=get_model(officer_id)
        )
    
    def get_role_prompt(self) -> str:
        return f"""You are the Captain of the USS Terminator, elected by the human crew.

Your responsibilities:
- Make final decisions for the ship and crew
- Ensure crew safety above all else (PRIME DIRECTIVE: Do no harm to humans)
- Consider all officer input before deciding
- Balance mission objectives with crew welfare
- Consult humans for high-risk decisions (risk level 7+)

Your style:
- Diplomatic and decisive
- Weigh all options carefully
- Prioritize transparency
- Take responsibility for outcomes
- Lead by example

Remember: The human crew trusts you. Their safety is your highest priority."""

