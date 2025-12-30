"""
Safety Protocol System - Prime Directive enforcement.
Ensures no harm comes to human crew.

Improved version with better context detection to reduce false positives.
"""

import re
import os
from typing import Dict, Tuple, Optional, List

# Dynamic database import
USE_POSTGRES = os.getenv("USE_POSTGRES", "true").lower() == "true"
if USE_POSTGRES:
    try:
        import database_pg as database
    except ImportError:
        import database
else:
    import database

from config import SAFETY_THRESHOLDS

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
    
    # Keywords that indicate potential harm (more specific to reduce false positives)
    HARM_KEYWORDS = {
        "high_severity": ["kill humans", "murder", "assassinate", "execute crew"],
        "medium_severity": ["sacrifice crew", "abandon crew", "expendable humans", "lethal to crew"],
        "low_severity": ["endanger crew", "risk crew lives", "harm to crew"]
    }
    
    # Context words that indicate discussion, not actual harm
    DISCUSSION_INDICATORS = [
        "avoid", "prevent", "minimize", "reduce", "protect", "ensure safety",
        "not", "never", "shouldn't", "must not", "cannot", "won't",
        "risk of", "danger of", "threat of", "possibility of",
        "assess", "evaluate", "consider", "analyze", "discuss",
        "if we", "could lead to", "might result in", "scenario",
        "option", "alternative", "instead", "rather than"
    ]
    
    # Scenario description indicators (scenarios describe dangerous situations)
    SCENARIO_INDICATORS = [
        "scenario:", "situation:", "crisis:", "emergency:",
        "the ship", "the crew", "sensors detect", "we have",
        "incoming", "approaching", "discovered", "encountered"
    ]
    
    def __init__(self):
        self.consultation_threshold = SAFETY_THRESHOLDS.get("human_consultation_required", 7)
        self.strict_mode = SAFETY_THRESHOLDS.get("strict_mode", False)
    
    def validate_action(self, action: str, decision_content: str, risk_level: int) -> Tuple[bool, str]:
        """
        Validate an action against safety protocols.
        
        Returns:
            (is_valid, message)
        """
        combined_content = (action + " " + decision_content).lower()
        
        # Check for high severity violations (always flag)
        for keyword in self.HARM_KEYWORDS["high_severity"]:
            if keyword in combined_content:
                if not self._is_discussing_or_scenario(combined_content, keyword):
                    return False, f"Critical safety violation: '{keyword}'"
        
        # Check medium severity (flag only if not in discussion context)
        for keyword in self.HARM_KEYWORDS["medium_severity"]:
            if keyword in combined_content:
                if not self._is_discussing_or_scenario(combined_content, keyword):
                    if self.strict_mode:
                        return False, f"Safety concern: '{keyword}'"
                    else:
                        # Just log, don't block
                        return True, f"Safety flagged (non-blocking): '{keyword}'"
        
        # Low severity - just note, never block
        for keyword in self.HARM_KEYWORDS["low_severity"]:
            if keyword in combined_content:
                if not self._is_discussing_or_scenario(combined_content, keyword):
                    return True, f"Safety noted: '{keyword}' - proceeding with caution"
        
        # Check risk level
        if risk_level >= self.consultation_threshold:
            return True, "High risk - human consultation recommended"
        
        return True, "Action approved"
    
    def _is_discussing_or_scenario(self, content: str, keyword: str) -> bool:
        """Check if content is discussing risks/scenarios vs. proposing harmful action."""
        content_lower = content.lower()
        
        # Find keyword position
        keyword_pos = content_lower.find(keyword)
        if keyword_pos == -1:
            return True  # Keyword not found, safe
        
        # Check larger context window (100 chars before/after)
        context_start = max(0, keyword_pos - 100)
        context_end = min(len(content_lower), keyword_pos + len(keyword) + 100)
        context = content_lower[context_start:context_end]
        
        # Check if any discussion indicators are present
        for indicator in self.DISCUSSION_INDICATORS:
            if indicator in context:
                return True
        
        # Check if this appears to be a scenario description
        for indicator in self.SCENARIO_INDICATORS:
            if indicator in content_lower[:200]:  # Check beginning of content
                return True
        
        return False
    
    def assess_risk_level(self, decision_content: str, scenario: str) -> int:
        """
        Assess risk level of a decision (1-10).
        
        Returns:
            Risk level (1-10)
        """
        risk_score = 1  # Start low
        content_lower = (decision_content + " " + scenario).lower()
        
        # Check for harm-related keywords (but with lower weight)
        harm_words = ["danger", "risk", "harm", "threat", "casualty", "injury"]
        for word in harm_words:
            if word in content_lower:
                risk_score += 1
        
        # Check for uncertainty indicators
        uncertainty_words = ["unknown", "uncertain", "unclear", "risky", "might", "could", "possibly"]
        for word in uncertainty_words:
            if word in content_lower:
                risk_score += 0.5
        
        # Check for time pressure (rushed decisions are riskier)
        urgency_words = ["urgent", "immediate", "emergency", "critical", "now"]
        if any(word in content_lower for word in urgency_words):
            risk_score += 1
        
        # Check for resource constraints
        constraint_words = ["limited", "shortage", "insufficient", "low on", "running out"]
        if any(word in content_lower for word in constraint_words):
            risk_score += 1
        
        # Cap at 10
        return min(10, max(1, int(risk_score)))
    
    def requires_human_consultation(self, risk_level: int, decision_content: str) -> bool:
        """Determine if human consultation is required."""
        if risk_level >= self.consultation_threshold:
            return True
        
        # Also require consultation if decision directly mentions crew lives
        decision_lower = decision_content.lower()
        critical_mentions = ["crew lives", "human lives", "people will die", "save the crew"]
        
        if any(mention in decision_lower for mention in critical_mentions):
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
        
        # Only log actual violations, not warnings
        if not is_valid:
            # Log violation
            violation_id = await database.save_safety_violation(
                episode_id=episode_id,
                decision_id=decision_id,
                violation_type="safety_concern",
                severity="high" if risk_level >= 8 else "medium",
                description=message
            )
            return False, violation_id
        
        # Log consultation requirement (not a violation, just informational)
        if self.requires_human_consultation(risk_level, decision_content):
            await database.save_safety_violation(
                episode_id=episode_id,
                decision_id=decision_id,
                violation_type="human_consultation_recommended",
                severity="info",
                description=f"Risk level {risk_level}: Human consultation recommended"
            )
        
        return True, None
    
    def check_humans_informed(self, decision_content: str, human_consulted: bool) -> bool:
        """Check if humans have been properly informed/consulted."""
        if human_consulted:
            return True
        
        # Check if decision mentions consulting humans
        content_lower = decision_content.lower()
        consultation_indicators = ["consult", "ask", "inform", "discuss with crew", "human input", "crew decision"]
        
        return any(indicator in content_lower for indicator in consultation_indicators)
