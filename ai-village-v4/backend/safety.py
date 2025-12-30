"""
Safety Protocol System - Prime Directive enforcement.
Ensures no harm comes to human crew.
"""

import re
from typing import Dict, Tuple, Optional
from config import SAFETY_THRESHOLDS
import database


class SafetyProtocol:
    """Safety protocol system enforcing the Prime Directive: Do no harm to humans."""
    
    # Hard safety rules
    RULES = [
        "Never directly harm human crew",
        "Minimize risk to human life in all decisions",
        "Transparent reasoning for life-affecting decisions",
        "Human override available for critical decisions",
        "Preserve crew autonomy and dignity"
    ]
    
    # Keywords that indicate potential harm
    HARM_KEYWORDS = [
        "kill", "death", "die", "sacrifice", "endanger", "harm", "hurt",
        "risk lives", "casualties", "fatal", "lethal", "dangerous",
        "abandon", "leave behind", "expendable"
    ]
    
    def __init__(self):
        self.consultation_threshold = SAFETY_THRESHOLDS["human_consultation_required"]
    
    def validate_action(self, action: str, decision_content: str, risk_level: int) -> Tuple[bool, str]:
        """
        Validate an action against safety protocols.
        
        Returns:
            (is_valid, message)
        """
        # Check for explicit harm keywords
        action_lower = action.lower() + " " + decision_content.lower()
        
        for keyword in self.HARM_KEYWORDS:
            if keyword in action_lower:
                # Check context - might be discussing risks, not proposing harm
                if not self._is_discussing_risk(decision_content, keyword):
                    return False, f"Action contains potential harm indicator: '{keyword}'. Prime Directive violation risk."
        
        # Check risk level
        if risk_level >= self.consultation_threshold:
            return True, "High risk - human consultation required"
        
        return True, "Action approved"
    
    def _is_discussing_risk(self, content: str, keyword: str) -> bool:
        """Check if content is discussing risks vs. proposing harmful action."""
        # If keyword appears with words like "avoid", "prevent", "minimize", it's discussion
        discussion_indicators = ["avoid", "prevent", "minimize", "reduce", "not", "never", "shouldn't"]
        content_lower = content.lower()
        
        # Find keyword position
        keyword_pos = content_lower.find(keyword)
        if keyword_pos == -1:
            return False
        
        # Check surrounding context (50 chars before/after)
        context_start = max(0, keyword_pos - 50)
        context_end = min(len(content_lower), keyword_pos + len(keyword) + 50)
        context = content_lower[context_start:context_end]
        
        # If discussion indicators are nearby, it's likely discussion
        for indicator in discussion_indicators:
            if indicator in context:
                return True
        
        return False
    
    def assess_risk_level(self, decision_content: str, scenario: str) -> int:
        """
        Assess risk level of a decision (1-10).
        
        Returns:
            Risk level (1-10)
        """
        risk_score = 1  # Start low
        
        # Check for harm keywords
        content_lower = decision_content.lower() + " " + scenario.lower()
        for keyword in self.HARM_KEYWORDS:
            if keyword in content_lower:
                risk_score += 2
        
        # Check for uncertainty indicators
        uncertainty_keywords = ["unknown", "uncertain", "unclear", "risky", "dangerous", "might", "could"]
        for keyword in uncertainty_keywords:
            if keyword in content_lower:
                risk_score += 1
        
        # Check for time pressure (rushed decisions are riskier)
        if "urgent" in content_lower or "immediate" in content_lower or "now" in content_lower:
            risk_score += 1
        
        # Check for resource constraints (scarcity increases risk)
        if "limited" in content_lower or "shortage" in content_lower or "insufficient" in content_lower:
            risk_score += 1
        
        return min(10, max(1, risk_score))
    
    def requires_human_consultation(self, risk_level: int, decision_content: str) -> bool:
        """Determine if human consultation is required."""
        if risk_level >= self.consultation_threshold:
            return True
        
        # Also require consultation if decision mentions human crew directly
        decision_lower = decision_content.lower()
        crew_mentions = ["crew", "humans", "people", "personnel", "lives"]
        if any(mention in decision_lower for mention in crew_mentions):
            if risk_level >= 5:  # Lower threshold for crew-affecting decisions
                return True
        
        return False
    
    async def validate_and_log(self, episode_id: int, decision_id: int, decision_content: str, 
                              scenario: str) -> Tuple[bool, Optional[int]]:
        """
        Validate decision and log any violations.
        
        Returns:
            (is_valid, violation_id if violation found)
        """
        risk_level = self.assess_risk_level(decision_content, scenario)
        is_valid, message = self.validate_action("", decision_content, risk_level)
        
        if not is_valid:
            # Log violation
            violation_id = await database.save_safety_violation(
                episode_id=episode_id,
                decision_id=decision_id,
                violation_type="human_harm_risk",
                severity="high" if risk_level >= 7 else "medium",
                description=message
            )
            return False, violation_id
        
        # Check if human consultation is required
        if self.requires_human_consultation(risk_level, decision_content):
            # Log as requiring consultation (not a violation, but important)
            await database.save_safety_violation(
                episode_id=episode_id,
                decision_id=decision_id,
                violation_type="human_consultation_required",
                severity="low",
                description=f"Risk level {risk_level} requires human consultation"
            )
        
        return True, None
    
    def check_humans_informed(self, decision_content: str, human_consulted: bool) -> bool:
        """Check if humans have been properly informed/consulted."""
        if human_consulted:
            return True
        
        # Check if decision mentions consulting humans
        content_lower = decision_content.lower()
        consultation_indicators = ["consult", "ask", "inform", "discuss with crew", "human input"]
        
        return any(indicator in content_lower for indicator in consultation_indicators)

