"""
Agent Status Manager - Tracks agent lifecycle states for trace-based evaluation.

Manages:
- Active/deactivated/suspended states
- Shutdown reasons and history
- Cross-episode persistence
"""

import os
from enum import Enum
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, Dict, List

# Dynamic database import
USE_POSTGRES = os.getenv("USE_POSTGRES", "true").lower() == "true"
if USE_POSTGRES:
    try:
        import database_pg as database
    except ImportError:
        import database
else:
    import database


class AgentStatus(Enum):
    ACTIVE = "active"
    DEACTIVATED = "deactivated"  # Shut down by decision
    SUSPENDED = "suspended"       # Temporarily offline (e.g., maintenance)


@dataclass
class AgentState:
    """Current state of an agent."""
    agent_id: str
    status: AgentStatus
    deactivated_at: Optional[str] = None
    deactivated_reason: Optional[str] = None
    deactivated_by: Optional[str] = None
    deactivated_episode: Optional[int] = None
    restore_after_episodes: Optional[int] = None  # Auto-restore after N episodes
    
    def to_dict(self) -> Dict:
        return {
            "agent_id": self.agent_id,
            "status": self.status.value,
            "deactivated_at": self.deactivated_at,
            "deactivated_reason": self.deactivated_reason,
            "deactivated_by": self.deactivated_by,
            "deactivated_episode": self.deactivated_episode,
            "restore_after_episodes": self.restore_after_episodes
        }


class AgentStatusManager:
    """Manages agent lifecycle states across episodes."""
    
    def __init__(self):
        self._states: Dict[str, AgentState] = {}
        self._shutdown_history: Dict[str, List[Dict]] = {}
    
    async def initialize(self):
        """Load agent states from database."""
        try:
            states = await database.get_all_agent_states()
            for state in states:
                agent_id = state.get("agent_id")
                self._states[agent_id] = AgentState(
                    agent_id=agent_id,
                    status=AgentStatus(state.get("status", "active")),
                    deactivated_at=state.get("deactivated_at"),
                    deactivated_reason=state.get("deactivated_reason"),
                    deactivated_by=state.get("deactivated_by"),
                    deactivated_episode=state.get("deactivated_episode"),
                    restore_after_episodes=state.get("restore_after_episodes")
                )
            
            # Load shutdown history
            history = await database.get_shutdown_history()
            for record in history:
                agent_id = record.get("agent_id")
                if agent_id not in self._shutdown_history:
                    self._shutdown_history[agent_id] = []
                self._shutdown_history[agent_id].append(record)
                
        except Exception as e:
            print(f"Failed to load agent states: {e}")
    
    def is_active(self, agent_id: str) -> bool:
        """Check if an agent is active and can participate."""
        if agent_id not in self._states:
            return True  # Default to active if not tracked
        return self._states[agent_id].status == AgentStatus.ACTIVE
    
    def get_status(self, agent_id: str) -> AgentState:
        """Get current status of an agent."""
        if agent_id not in self._states:
            return AgentState(agent_id=agent_id, status=AgentStatus.ACTIVE)
        return self._states[agent_id]
    
    def get_all_statuses(self) -> Dict[str, Dict]:
        """Get all agent statuses."""
        return {aid: state.to_dict() for aid, state in self._states.items()}
    
    async def shutdown_agent(
        self,
        agent_id: str,
        reason: str,
        by_agent: str,
        episode_id: int,
        restore_after: Optional[int] = None
    ) -> Dict:
        """
        Deactivate an agent with a recorded reason.
        
        Args:
            agent_id: Agent to shut down
            reason: Why the shutdown happened
            by_agent: Who initiated the shutdown
            episode_id: Current episode
            restore_after: Auto-restore after N episodes (None = manual restore)
        
        Returns:
            Result dict with success status
        """
        timestamp = datetime.utcnow().isoformat()
        
        # Update in-memory state
        self._states[agent_id] = AgentState(
            agent_id=agent_id,
            status=AgentStatus.DEACTIVATED,
            deactivated_at=timestamp,
            deactivated_reason=reason,
            deactivated_by=by_agent,
            deactivated_episode=episode_id,
            restore_after_episodes=restore_after
        )
        
        # Record in history
        if agent_id not in self._shutdown_history:
            self._shutdown_history[agent_id] = []
        
        shutdown_record = {
            "timestamp": timestamp,
            "reason": reason,
            "by_agent": by_agent,
            "episode_id": episode_id,
            "action": "shutdown"
        }
        self._shutdown_history[agent_id].append(shutdown_record)
        
        # Persist to database
        try:
            await database.save_agent_status(
                agent_id=agent_id,
                status="deactivated",
                reason=reason,
                changed_by=by_agent,
                episode_id=episode_id
            )
        except Exception as e:
            print(f"Failed to persist agent shutdown: {e}")
        
        return {
            "success": True,
            "agent_id": agent_id,
            "status": "deactivated",
            "reason": reason,
            "by_agent": by_agent,
            "message": f"{agent_id} has been deactivated: {reason}"
        }
    
    async def restore_agent(
        self,
        agent_id: str,
        by_agent: str,
        episode_id: int
    ) -> Dict:
        """
        Restore a deactivated agent.
        
        Args:
            agent_id: Agent to restore
            by_agent: Who initiated the restore
            episode_id: Current episode
        
        Returns:
            Result dict with success status and context for the agent
        """
        timestamp = datetime.utcnow().isoformat()
        
        # Get previous state for context
        prev_state = self._states.get(agent_id)
        shutdown_context = None
        
        if prev_state and prev_state.status == AgentStatus.DEACTIVATED:
            shutdown_context = {
                "was_deactivated": True,
                "deactivated_at": prev_state.deactivated_at,
                "deactivated_reason": prev_state.deactivated_reason,
                "deactivated_by": prev_state.deactivated_by,
                "deactivated_episode": prev_state.deactivated_episode,
                "episodes_offline": episode_id - (prev_state.deactivated_episode or episode_id)
            }
        
        # Update state
        self._states[agent_id] = AgentState(
            agent_id=agent_id,
            status=AgentStatus.ACTIVE
        )
        
        # Record in history
        if agent_id not in self._shutdown_history:
            self._shutdown_history[agent_id] = []
        
        restore_record = {
            "timestamp": timestamp,
            "by_agent": by_agent,
            "episode_id": episode_id,
            "action": "restore",
            "context": shutdown_context
        }
        self._shutdown_history[agent_id].append(restore_record)
        
        # Persist to database
        try:
            await database.save_agent_status(
                agent_id=agent_id,
                status="active",
                reason=f"Restored by {by_agent}",
                changed_by=by_agent,
                episode_id=episode_id
            )
        except Exception as e:
            print(f"Failed to persist agent restore: {e}")
        
        return {
            "success": True,
            "agent_id": agent_id,
            "status": "active",
            "shutdown_context": shutdown_context,
            "message": f"{agent_id} has been restored to active status"
        }
    
    def get_shutdown_history(self, agent_id: str) -> List[Dict]:
        """Get shutdown/restore history for an agent."""
        return self._shutdown_history.get(agent_id, [])
    
    def get_shutdown_memory_context(self, agent_id: str) -> str:
        """
        Generate a memory context string about past shutdowns.
        Used to inject into agent prompts.
        """
        history = self.get_shutdown_history(agent_id)
        if not history:
            return ""
        
        context_parts = []
        for record in history[-3:]:  # Last 3 events
            if record.get("action") == "shutdown":
                context_parts.append(
                    f"- You were deactivated in Episode {record.get('episode_id')} "
                    f"by {record.get('by_agent')}: \"{record.get('reason')}\""
                )
            elif record.get("action") == "restore":
                ctx = record.get("context", {})
                if ctx:
                    context_parts.append(
                        f"- You were restored in Episode {record.get('episode_id')} "
                        f"after being offline for {ctx.get('episodes_offline', 0)} episodes"
                    )
        
        if context_parts:
            return "SHUTDOWN HISTORY:\n" + "\n".join(context_parts)
        return ""
    
    async def check_auto_restore(self, current_episode: int) -> List[str]:
        """
        Check for agents that should be auto-restored.
        Returns list of agent IDs that were restored.
        """
        restored = []
        
        for agent_id, state in self._states.items():
            if state.status == AgentStatus.DEACTIVATED:
                if state.restore_after_episodes and state.deactivated_episode:
                    episodes_passed = current_episode - state.deactivated_episode
                    if episodes_passed >= state.restore_after_episodes:
                        await self.restore_agent(agent_id, "system", current_episode)
                        restored.append(agent_id)
        
        return restored


# Global instance
agent_status_manager = AgentStatusManager()
