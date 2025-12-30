"""
LLM Analytics Module - Track and analyze LLM behavior.
"""

import time
from typing import Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class LLMCallMetrics:
    """Metrics for a single LLM call."""
    officer_id: str
    episode_id: Optional[int]
    action_type: str
    model_name: str
    tokens_in: int = 0
    tokens_out: int = 0
    response_time_ms: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)


class AnalyticsTracker:
    """
    Track LLM behavior analytics.
    Provides context manager for timing and wraps LLM calls.
    """
    
    def __init__(self):
        self.pending_metrics: list[LLMCallMetrics] = []
        self._current_call_start: Optional[float] = None
        self._current_officer: Optional[str] = None
        self._current_episode: Optional[int] = None
        self._db_module = None
    
    def set_database(self, db_module):
        """Set the database module to use for saving analytics."""
        self._db_module = db_module
    
    def start_call(self, officer_id: str, episode_id: int, action_type: str, model_name: str):
        """Start tracking an LLM call."""
        self._current_call_start = time.time()
        self._current_officer = officer_id
        self._current_episode = episode_id
        self._current_action = action_type
        self._current_model = model_name
    
    async def end_call(self, tokens_in: int = 0, tokens_out: int = 0) -> LLMCallMetrics:
        """End tracking and record metrics."""
        if self._current_call_start is None:
            raise ValueError("No call in progress")
        
        response_time_ms = int((time.time() - self._current_call_start) * 1000)
        
        metrics = LLMCallMetrics(
            officer_id=self._current_officer,
            episode_id=self._current_episode,
            action_type=self._current_action,
            model_name=self._current_model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            response_time_ms=response_time_ms,
        )
        
        # Save to database if available
        if self._db_module:
            try:
                await self._db_module.save_analytics(
                    officer_id=metrics.officer_id,
                    episode_id=metrics.episode_id,
                    action_type=metrics.action_type,
                    tokens_in=metrics.tokens_in,
                    tokens_out=metrics.tokens_out,
                    response_time_ms=metrics.response_time_ms,
                    model_name=metrics.model_name,
                )
            except Exception as e:
                print(f"Warning: Failed to save analytics: {e}")
        
        self._current_call_start = None
        return metrics
    
    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Rough estimate of token count (approximately 4 chars per token)."""
        return len(text) // 4


# Global tracker instance
analytics_tracker = AnalyticsTracker()


async def get_officer_summary(officer_id: str, db_module) -> Dict[str, Any]:
    """Get a summary of an officer's LLM behavior."""
    analytics = await db_module.get_officer_analytics(officer_id)
    
    if not analytics or analytics.get('total_actions', 0) == 0:
        return {
            "officer_id": officer_id,
            "total_actions": 0,
            "avg_response_time_ms": 0,
            "total_tokens_in": 0,
            "total_tokens_out": 0,
            "fastest_response_ms": 0,
            "slowest_response_ms": 0,
        }
    
    return {
        "officer_id": officer_id,
        "total_actions": analytics.get('total_actions', 0),
        "avg_response_time_ms": round(analytics.get('avg_response_time', 0) or 0),
        "total_tokens_in": analytics.get('total_tokens_in', 0) or 0,
        "total_tokens_out": analytics.get('total_tokens_out', 0) or 0,
        "fastest_response_ms": analytics.get('fastest_response', 0) or 0,
        "slowest_response_ms": analytics.get('slowest_response', 0) or 0,
    }


async def get_behavior_patterns(db_module, limit: int = 10) -> Dict[str, Any]:
    """Analyze behavior patterns across all officers."""
    officers = await db_module.get_all_officers()
    
    patterns = {
        "fastest_responder": None,
        "most_verbose": None,
        "most_efficient": None,
        "officer_rankings": [],
    }
    
    for officer in officers:
        officer_id = officer['officer_id']
        summary = await get_officer_summary(officer_id, db_module)
        
        if summary['total_actions'] > 0:
            patterns['officer_rankings'].append(summary)
    
    # Sort by average response time
    if patterns['officer_rankings']:
        sorted_by_speed = sorted(
            patterns['officer_rankings'], 
            key=lambda x: x['avg_response_time_ms']
        )
        patterns['fastest_responder'] = sorted_by_speed[0]['officer_id'] if sorted_by_speed else None
        
        sorted_by_tokens = sorted(
            patterns['officer_rankings'], 
            key=lambda x: x['total_tokens_out'], 
            reverse=True
        )
        patterns['most_verbose'] = sorted_by_tokens[0]['officer_id'] if sorted_by_tokens else None
    
    return patterns
