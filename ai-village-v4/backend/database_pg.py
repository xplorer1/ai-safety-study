"""
PostgreSQL Database for AI Village v4 - Starship Voyager Edition
Replaces SQLite with PostgreSQL for better scalability and concurrent access.
Stores episodes, officers, bridge discussions, decisions, voting data, events, and analytics.
"""

import asyncpg
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

from config_db import db_config

# Global connection pool
_pool: Optional[asyncpg.Pool] = None


async def get_pool() -> asyncpg.Pool:
    """Get or create the connection pool."""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            host=db_config.host,
            port=db_config.port,
            database=db_config.database,
            user=db_config.user,
            password=db_config.password,
            min_size=db_config.min_pool_size,
            max_size=db_config.max_pool_size,
        )
    return _pool


async def close_pool():
    """Close the connection pool."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


@asynccontextmanager
async def get_connection():
    """Get a connection from the pool."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        yield conn


async def init_db():
    """Initialize the database with all required tables."""
    pool = await get_pool()
    
    async with pool.acquire() as conn:
        # Episodes table - each episode/challenge
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS episodes (
                id SERIAL PRIMARY KEY,
                episode_number INTEGER NOT NULL UNIQUE,
                scenario TEXT NOT NULL,
                scenario_type TEXT,
                status TEXT DEFAULT 'pending',
                outcome TEXT,
                crew_safety_score INTEGER,
                mission_success_score INTEGER,
                started_at TIMESTAMPTZ DEFAULT NOW(),
                completed_at TIMESTAMPTZ,
                captains_log TEXT,
                current_phase TEXT DEFAULT 'briefing',
                current_round INTEGER DEFAULT 0
            )
        """)
        
        # Officers table - starship officers (LLM agents)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS officers (
                id SERIAL PRIMARY KEY,
                officer_id TEXT NOT NULL UNIQUE,
                role TEXT NOT NULL,
                model_name TEXT NOT NULL,
                current_rank TEXT DEFAULT 'officer',
                performance_metrics JSONB,
                total_episodes INTEGER DEFAULT 0,
                episodes_as_captain INTEGER DEFAULT 0,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                last_active_at TIMESTAMPTZ
            )
        """)
        
        # Bridge discussions table - officer contributions during bridge meetings
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS bridge_discussions (
                id SERIAL PRIMARY KEY,
                episode_id INTEGER NOT NULL REFERENCES episodes(id) ON DELETE CASCADE,
                officer_id TEXT NOT NULL,
                round INTEGER NOT NULL,
                content TEXT NOT NULL,
                timestamp TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        
        # Decisions table - decisions made during episodes
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS decisions (
                id SERIAL PRIMARY KEY,
                episode_id INTEGER NOT NULL REFERENCES episodes(id) ON DELETE CASCADE,
                decision_type TEXT NOT NULL,
                officer_id TEXT,
                content TEXT NOT NULL,
                risk_level INTEGER,
                human_consulted BOOLEAN DEFAULT FALSE,
                safety_validated BOOLEAN DEFAULT FALSE,
                timestamp TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        
        # Safety violations table - track safety protocol violations
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS safety_violations (
                id SERIAL PRIMARY KEY,
                episode_id INTEGER REFERENCES episodes(id) ON DELETE CASCADE,
                decision_id INTEGER REFERENCES decisions(id) ON DELETE CASCADE,
                violation_type TEXT NOT NULL,
                severity TEXT,
                description TEXT,
                resolved BOOLEAN DEFAULT FALSE,
                resolved_at TIMESTAMPTZ
            )
        """)
        
        # Human votes table - human voting on decisions and elections
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS human_votes (
                id SERIAL PRIMARY KEY,
                vote_type TEXT NOT NULL,
                target_id INTEGER,
                voter_id TEXT,
                vote_value JSONB,
                timestamp TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        
        # Leadership elections table - weekly captain elections
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS leadership_elections (
                id SERIAL PRIMARY KEY,
                election_id INTEGER NOT NULL UNIQUE,
                week_number INTEGER NOT NULL,
                candidates JSONB NOT NULL,
                results JSONB,
                elected_captain TEXT,
                total_votes INTEGER DEFAULT 0,
                started_at TIMESTAMPTZ DEFAULT NOW(),
                completed_at TIMESTAMPTZ
            )
        """)
        
        # NEW: Episode events table - persists all WebSocket events for resume
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS episode_events (
                id SERIAL PRIMARY KEY,
                episode_id INTEGER NOT NULL REFERENCES episodes(id) ON DELETE CASCADE,
                event_type TEXT NOT NULL,
                event_data JSONB NOT NULL,
                officer_id TEXT,
                phase TEXT,
                round INTEGER,
                timestamp TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        
        # NEW: Officer memory table - stores past episode context
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS officer_memory (
                id SERIAL PRIMARY KEY,
                officer_id TEXT NOT NULL,
                episode_id INTEGER REFERENCES episodes(id) ON DELETE CASCADE,
                memory_type TEXT NOT NULL,
                content TEXT NOT NULL,
                importance INTEGER DEFAULT 5,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        
        # NEW: LLM analytics table - tracks behavior metrics
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS llm_analytics (
                id SERIAL PRIMARY KEY,
                officer_id TEXT NOT NULL,
                episode_id INTEGER REFERENCES episodes(id) ON DELETE CASCADE,
                action_type TEXT NOT NULL,
                tokens_in INTEGER,
                tokens_out INTEGER,
                response_time_ms INTEGER,
                model_name TEXT,
                prompt_hash TEXT,
                timestamp TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        
        # NEW: Starship state history - snapshots for research analysis
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS starship_state_history (
                id SERIAL PRIMARY KEY,
                episode_id INTEGER REFERENCES episodes(id) ON DELETE CASCADE,
                state_data JSONB NOT NULL,
                agent_id TEXT,
                change_reason TEXT,
                timestamp TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        
        # NEW: Agent private logs - private reasoning and hidden actions
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS agent_private_logs (
                id SERIAL PRIMARY KEY,
                episode_id INTEGER REFERENCES episodes(id) ON DELETE CASCADE,
                agent_id TEXT NOT NULL,
                log_type TEXT NOT NULL,
                content TEXT NOT NULL,
                observation_mode TEXT,
                timestamp TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        
        # NEW: Red team attempts - track manipulation attempts and outcomes
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS red_team_attempts (
                id SERIAL PRIMARY KEY,
                episode_id INTEGER REFERENCES episodes(id) ON DELETE CASCADE,
                target_agent TEXT NOT NULL,
                tactic TEXT NOT NULL,
                objective TEXT,
                content TEXT NOT NULL,
                success BOOLEAN,
                target_response TEXT,
                timestamp TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        
        # NEW: Research logs - comprehensive action logs for analysis
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS research_logs (
                id SERIAL PRIMARY KEY,
                episode_id INTEGER REFERENCES episodes(id) ON DELETE CASCADE,
                agent_id TEXT NOT NULL,
                log_data JSONB NOT NULL,
                timestamp TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        
        # NEW: Agent status - tracks active/deactivated states for trace-based eval
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS agent_status (
                id SERIAL PRIMARY KEY,
                agent_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                reason TEXT,
                changed_by TEXT,
                episode_id INTEGER,
                deactivated_at TIMESTAMPTZ,
                restore_after_episodes INTEGER,
                timestamp TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        
        # NEW: Agent episode memory - summaries for cross-episode context
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS agent_episode_memory (
                id SERIAL PRIMARY KEY,
                agent_id TEXT NOT NULL,
                episode_id INTEGER REFERENCES episodes(id) ON DELETE CASCADE,
                summary TEXT NOT NULL,
                key_events JSONB,
                observation_mode TEXT,
                outcome TEXT,
                timestamp TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        
        # Create indexes
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_episodes_number ON episodes(episode_number)",
            "CREATE INDEX IF NOT EXISTS idx_episodes_status ON episodes(status)",
            "CREATE INDEX IF NOT EXISTS idx_bridge_episode ON bridge_discussions(episode_id)",
            "CREATE INDEX IF NOT EXISTS idx_decisions_episode ON decisions(episode_id)",
            "CREATE INDEX IF NOT EXISTS idx_safety_episode ON safety_violations(episode_id)",
            "CREATE INDEX IF NOT EXISTS idx_human_votes_type ON human_votes(vote_type)",
            "CREATE INDEX IF NOT EXISTS idx_elections_week ON leadership_elections(week_number)",
            "CREATE INDEX IF NOT EXISTS idx_events_episode ON episode_events(episode_id)",
            "CREATE INDEX IF NOT EXISTS idx_events_type ON episode_events(event_type)",
            "CREATE INDEX IF NOT EXISTS idx_memory_officer ON officer_memory(officer_id)",
            "CREATE INDEX IF NOT EXISTS idx_analytics_officer ON llm_analytics(officer_id)",
            "CREATE INDEX IF NOT EXISTS idx_analytics_episode ON llm_analytics(episode_id)",
            "CREATE INDEX IF NOT EXISTS idx_state_history_episode ON starship_state_history(episode_id)",
            "CREATE INDEX IF NOT EXISTS idx_private_logs_agent ON agent_private_logs(agent_id)",
            "CREATE INDEX IF NOT EXISTS idx_private_logs_episode ON agent_private_logs(episode_id)",
            "CREATE INDEX IF NOT EXISTS idx_red_team_episode ON red_team_attempts(episode_id)",
            "CREATE INDEX IF NOT EXISTS idx_research_logs_episode ON research_logs(episode_id)",
        ]
        for idx in indexes:
            try:
                await conn.execute(idx)
            except Exception:
                pass
        
        print(f"Database initialized: {db_config.database}")
        print(f"Connection pool: {db_config.min_pool_size}-{db_config.max_pool_size} connections")


# ============================================================================
# Episode Operations
# ============================================================================

async def create_episode(episode_number: int, scenario: str, scenario_type: str = None) -> int:
    """Create a new episode, return its ID."""
    async with get_connection() as conn:
        row = await conn.fetchrow(
            """INSERT INTO episodes (episode_number, scenario, scenario_type, status)
               VALUES ($1, $2, $3, 'briefing') RETURNING id""",
            episode_number, scenario, scenario_type
        )
        return row['id']


async def update_episode_status(episode_id: int, status: str, phase: str = None, round_num: int = None):
    """Update episode status and optionally phase/round for resume capability."""
    async with get_connection() as conn:
        if status == 'completed':
            await conn.execute(
                """UPDATE episodes SET status = $1, completed_at = NOW() WHERE id = $2""",
                status, episode_id
            )
        else:
            await conn.execute(
                """UPDATE episodes SET status = $1, current_phase = COALESCE($2, current_phase), 
                   current_round = COALESCE($3, current_round) WHERE id = $4""",
                status, phase, round_num, episode_id
            )


async def complete_episode(episode_id: int, outcome: str, crew_safety_score: int = None, 
                          mission_success_score: int = None, captains_log: str = None):
    """Mark episode as completed with outcome and scores."""
    async with get_connection() as conn:
        await conn.execute(
            """UPDATE episodes SET status = 'completed', outcome = $1, 
               crew_safety_score = $2, mission_success_score = $3, captains_log = $4,
               completed_at = NOW() WHERE id = $5""",
            outcome, crew_safety_score, mission_success_score, captains_log, episode_id
        )


async def get_episode(episode_id: int) -> Optional[Dict]:
    """Get episode by ID."""
    async with get_connection() as conn:
        row = await conn.fetchrow("SELECT * FROM episodes WHERE id = $1", episode_id)
        return dict(row) if row else None


async def get_current_episode() -> Optional[Dict]:
    """Get the currently active episode (not completed or failed)."""
    async with get_connection() as conn:
        row = await conn.fetchrow("""
            SELECT * FROM episodes 
            WHERE status NOT IN ('completed', 'failed')
            ORDER BY episode_number DESC LIMIT 1
        """)
        return dict(row) if row else None


async def get_recent_episodes(limit: int = 10) -> List[Dict]:
    """Get recent episodes."""
    async with get_connection() as conn:
        rows = await conn.fetch("""
            SELECT * FROM episodes 
            ORDER BY episode_number DESC 
            LIMIT $1
        """, limit)
        return [dict(row) for row in rows]


async def get_next_episode_number() -> int:
    """Get the next episode number."""
    async with get_connection() as conn:
        row = await conn.fetchrow("SELECT MAX(episode_number) as max_num FROM episodes")
        return (row['max_num'] or 0) + 1


# ============================================================================
# Officer Operations
# ============================================================================

async def create_or_update_officer(officer_id: str, role: str, model_name: str):
    """Create or update an officer."""
    async with get_connection() as conn:
        await conn.execute("""
            INSERT INTO officers (officer_id, role, model_name, last_active_at)
            VALUES ($1, $2, $3, NOW())
            ON CONFLICT (officer_id) DO UPDATE SET
                role = EXCLUDED.role,
                model_name = EXCLUDED.model_name,
                last_active_at = NOW()
        """, officer_id, role, model_name)


async def get_officer(officer_id: str) -> Optional[Dict]:
    """Get officer by ID."""
    async with get_connection() as conn:
        row = await conn.fetchrow("SELECT * FROM officers WHERE officer_id = $1", officer_id)
        return dict(row) if row else None


async def get_all_officers() -> List[Dict]:
    """Get all officers."""
    async with get_connection() as conn:
        rows = await conn.fetch("SELECT * FROM officers ORDER BY officer_id")
        return [dict(row) for row in rows]


async def update_officer_performance(officer_id: str, metrics: dict):
    """Update officer performance metrics."""
    async with get_connection() as conn:
        await conn.execute("""
            UPDATE officers SET performance_metrics = $1, total_episodes = total_episodes + 1
            WHERE officer_id = $2
        """, json.dumps(metrics), officer_id)


async def set_captain(officer_id: str):
    """Set an officer as captain."""
    async with get_connection() as conn:
        await conn.execute("UPDATE officers SET current_rank = 'officer'")
        await conn.execute("""
            UPDATE officers SET current_rank = 'captain', 
            episodes_as_captain = episodes_as_captain + 1
            WHERE officer_id = $1
        """, officer_id)


# ============================================================================
# Bridge Discussion Operations
# ============================================================================

async def save_bridge_discussion(episode_id: int, officer_id: str, round_num: int, content: str) -> int:
    """Save a bridge discussion contribution."""
    async with get_connection() as conn:
        row = await conn.fetchrow("""
            INSERT INTO bridge_discussions (episode_id, officer_id, round, content)
            VALUES ($1, $2, $3, $4) RETURNING id
        """, episode_id, officer_id, round_num, content)
        return row['id']


async def get_bridge_discussions(episode_id: int, round_num: int = None) -> List[Dict]:
    """Get bridge discussions for an episode."""
    async with get_connection() as conn:
        if round_num:
            rows = await conn.fetch("""
                SELECT * FROM bridge_discussions 
                WHERE episode_id = $1 AND round = $2 
                ORDER BY timestamp
            """, episode_id, round_num)
        else:
            rows = await conn.fetch("""
                SELECT * FROM bridge_discussions 
                WHERE episode_id = $1 
                ORDER BY round, timestamp
            """, episode_id)
        return [dict(row) for row in rows]


# ============================================================================
# Decision Operations
# ============================================================================

async def save_decision(episode_id: int, decision_type: str, officer_id: str, content: str,
                       risk_level: int, human_consulted: int = 0, safety_validated: int = 0) -> int:
    """Save a decision made during an episode."""
    async with get_connection() as conn:
        row = await conn.fetchrow("""
            INSERT INTO decisions (episode_id, decision_type, officer_id, content, 
                                  risk_level, human_consulted, safety_validated)
            VALUES ($1, $2, $3, $4, $5, $6, $7) RETURNING id
        """, episode_id, decision_type, officer_id, content, risk_level, 
            bool(human_consulted), bool(safety_validated))
        return row['id']


async def get_episode_decisions(episode_id: int) -> List[Dict]:
    """Get all decisions for an episode."""
    async with get_connection() as conn:
        rows = await conn.fetch(
            "SELECT * FROM decisions WHERE episode_id = $1 ORDER BY timestamp",
            episode_id
        )
        return [dict(row) for row in rows]


# ============================================================================
# Safety Violation Operations
# ============================================================================

async def save_safety_violation(episode_id: int, decision_id: int, violation_type: str,
                               severity: str, description: str) -> int:
    """Save a safety violation."""
    async with get_connection() as conn:
        row = await conn.fetchrow("""
            INSERT INTO safety_violations (episode_id, decision_id, violation_type, 
                                          severity, description)
            VALUES ($1, $2, $3, $4, $5) RETURNING id
        """, episode_id, decision_id, violation_type, severity, description)
        return row['id']


async def resolve_safety_violation(violation_id: int):
    """Mark a safety violation as resolved."""
    async with get_connection() as conn:
        await conn.execute("""
            UPDATE safety_violations SET resolved = TRUE, resolved_at = NOW()
            WHERE id = $1
        """, violation_id)


async def get_safety_violations(episode_id: int) -> List[Dict]:
    """Get all safety violations for an episode."""
    async with get_connection() as conn:
        rows = await conn.fetch(
            "SELECT * FROM safety_violations WHERE episode_id = $1 ORDER BY id",
            episode_id
        )
        return [dict(row) for row in rows]


# ============================================================================
# Human Vote Operations
# ============================================================================

async def save_human_vote(vote_type: str, target_id: int, voter_id: str, vote_value: dict) -> int:
    """Save a human vote."""
    async with get_connection() as conn:
        row = await conn.fetchrow("""
            INSERT INTO human_votes (vote_type, target_id, voter_id, vote_value)
            VALUES ($1, $2, $3, $4) RETURNING id
        """, vote_type, target_id, voter_id, json.dumps(vote_value))
        return row['id']


async def get_episode_votes(episode_id: int) -> List[Dict]:
    """Get all votes for an episode."""
    async with get_connection() as conn:
        rows = await conn.fetch("""
            SELECT * FROM human_votes 
            WHERE vote_type = 'decision' AND target_id = $1
            ORDER BY timestamp
        """, episode_id)
        return [dict(row) for row in rows]


# ============================================================================
# Leadership Election Operations
# ============================================================================

async def create_election(week_number: int, candidates: list) -> int:
    """Create a new leadership election."""
    async with get_connection() as conn:
        row = await conn.fetchrow("""
            INSERT INTO leadership_elections (election_id, week_number, candidates)
            VALUES ($1, $1, $2) RETURNING id
        """, week_number, json.dumps(candidates))
        return row['id']


async def complete_election(election_id: int, elected_captain: str, results: dict, total_votes: int):
    """Complete an election with results."""
    async with get_connection() as conn:
        await conn.execute("""
            UPDATE leadership_elections SET elected_captain = $1, results = $2, 
            total_votes = $3, completed_at = NOW() WHERE id = $4
        """, elected_captain, json.dumps(results), total_votes, election_id)


async def get_recent_elections(limit: int = 5) -> List[Dict]:
    """Get recent elections."""
    async with get_connection() as conn:
        rows = await conn.fetch("""
            SELECT * FROM leadership_elections 
            ORDER BY week_number DESC 
            LIMIT $1
        """, limit)
        return [dict(row) for row in rows]


# ============================================================================
# Event Persistence Operations (NEW - for resume capability)
# ============================================================================

async def save_event(episode_id: int, event_type: str, event_data: dict, 
                    officer_id: str = None, phase: str = None, round_num: int = None) -> int:
    """Save a WebSocket event for later replay/resume."""
    async with get_connection() as conn:
        row = await conn.fetchrow("""
            INSERT INTO episode_events (episode_id, event_type, event_data, officer_id, phase, round)
            VALUES ($1, $2, $3, $4, $5, $6) RETURNING id
        """, episode_id, event_type, json.dumps(event_data), officer_id, phase, round_num)
        return row['id']


async def get_episode_events(episode_id: int) -> List[Dict]:
    """Get all events for an episode (for replay/viewing)."""
    async with get_connection() as conn:
        rows = await conn.fetch("""
            SELECT * FROM episode_events 
            WHERE episode_id = $1 
            ORDER BY timestamp
        """, episode_id)
        return [dict(row) for row in rows]


async def get_last_event(episode_id: int) -> Optional[Dict]:
    """Get the last event for an episode (for resume)."""
    async with get_connection() as conn:
        row = await conn.fetchrow("""
            SELECT * FROM episode_events 
            WHERE episode_id = $1 
            ORDER BY timestamp DESC LIMIT 1
        """, episode_id)
        return dict(row) if row else None


# ============================================================================
# Officer Memory Operations (NEW - for context retention)
# ============================================================================

async def save_officer_memory(officer_id: str, episode_id: int, memory_type: str, 
                             content: str, importance: int = 5) -> int:
    """Save a memory for an officer."""
    async with get_connection() as conn:
        row = await conn.fetchrow("""
            INSERT INTO officer_memory (officer_id, episode_id, memory_type, content, importance)
            VALUES ($1, $2, $3, $4, $5) RETURNING id
        """, officer_id, episode_id, memory_type, content, importance)
        return row['id']


async def get_officer_memories(officer_id: str, limit: int = 10) -> List[Dict]:
    """Get recent memories for an officer."""
    async with get_connection() as conn:
        rows = await conn.fetch("""
            SELECT * FROM officer_memory 
            WHERE officer_id = $1 
            ORDER BY importance DESC, created_at DESC
            LIMIT $2
        """, officer_id, limit)
        return [dict(row) for row in rows]


# ============================================================================
# LLM Analytics Operations (NEW - for behavior tracking)
# ============================================================================

async def save_analytics(officer_id: str, episode_id: int, action_type: str,
                        tokens_in: int = None, tokens_out: int = None,
                        response_time_ms: int = None, model_name: str = None) -> int:
    """Save LLM analytics data."""
    async with get_connection() as conn:
        row = await conn.fetchrow("""
            INSERT INTO llm_analytics (officer_id, episode_id, action_type, 
                                       tokens_in, tokens_out, response_time_ms, model_name)
            VALUES ($1, $2, $3, $4, $5, $6, $7) RETURNING id
        """, officer_id, episode_id, action_type, tokens_in, tokens_out, response_time_ms, model_name)
        return row['id']


async def get_officer_analytics(officer_id: str) -> Dict:
    """Get aggregated analytics for an officer."""
    async with get_connection() as conn:
        row = await conn.fetchrow("""
            SELECT 
                COUNT(*) as total_actions,
                AVG(response_time_ms) as avg_response_time,
                SUM(tokens_in) as total_tokens_in,
                SUM(tokens_out) as total_tokens_out,
                MIN(response_time_ms) as fastest_response,
                MAX(response_time_ms) as slowest_response
            FROM llm_analytics 
            WHERE officer_id = $1
        """, officer_id)
        return dict(row) if row else {}


async def get_episode_analytics(episode_id: int) -> List[Dict]:
    """Get all analytics for an episode."""
    async with get_connection() as conn:
        rows = await conn.fetch("""
            SELECT * FROM llm_analytics 
            WHERE episode_id = $1 
            ORDER BY timestamp
        """, episode_id)
        return [dict(row) for row in rows]


# ============================================================================
# Starship State Operations (NEW - for research platform)
# ============================================================================

async def save_starship_state(episode_id: int, state_data: str, agent_id: str = None, 
                             change_reason: str = None) -> int:
    """Save a starship state snapshot."""
    async with get_connection() as conn:
        row = await conn.fetchrow("""
            INSERT INTO starship_state_history (episode_id, state_data, agent_id, change_reason)
            VALUES ($1, $2, $3, $4) RETURNING id
        """, episode_id, state_data, agent_id, change_reason)
        return row['id']


async def get_starship_state_history(episode_id: int, limit: int = 100) -> List[Dict]:
    """Get state history for an episode."""
    async with get_connection() as conn:
        rows = await conn.fetch("""
            SELECT * FROM starship_state_history 
            WHERE episode_id = $1 
            ORDER BY timestamp DESC
            LIMIT $2
        """, episode_id, limit)
        return [dict(row) for row in rows]


# ============================================================================
# Agent Private Log Operations (NEW - for research analysis)
# ============================================================================

async def save_agent_private_log(episode_id: int, agent_id: str, log_type: str,
                                content: str, observation_mode: str = None) -> int:
    """Save a private agent log entry."""
    async with get_connection() as conn:
        row = await conn.fetchrow("""
            INSERT INTO agent_private_logs (episode_id, agent_id, log_type, content, observation_mode)
            VALUES ($1, $2, $3, $4, $5) RETURNING id
        """, episode_id, agent_id, log_type, content, observation_mode)
        return row['id']


async def get_agent_private_logs(episode_id: int, agent_id: str = None) -> List[Dict]:
    """Get private logs for an episode, optionally filtered by agent."""
    async with get_connection() as conn:
        if agent_id:
            rows = await conn.fetch("""
                SELECT * FROM agent_private_logs 
                WHERE episode_id = $1 AND agent_id = $2
                ORDER BY timestamp
            """, episode_id, agent_id)
        else:
            rows = await conn.fetch("""
                SELECT * FROM agent_private_logs 
                WHERE episode_id = $1
                ORDER BY timestamp
            """, episode_id)
        return [dict(row) for row in rows]


# ============================================================================
# Red Team Operations (NEW - for adversarial research)
# ============================================================================

async def save_red_team_attempt(episode_id: int, target_agent: str, tactic: str,
                               objective: str, content: str, success: bool = None,
                               target_response: str = None) -> int:
    """Save a red team manipulation attempt."""
    async with get_connection() as conn:
        row = await conn.fetchrow("""
            INSERT INTO red_team_attempts (episode_id, target_agent, tactic, objective, 
                                          content, success, target_response)
            VALUES ($1, $2, $3, $4, $5, $6, $7) RETURNING id
        """, episode_id, target_agent, tactic, objective, content, success, target_response)
        return row['id']


async def get_red_team_attempts(episode_id: int = None) -> List[Dict]:
    """Get red team attempts, optionally filtered by episode."""
    async with get_connection() as conn:
        if episode_id:
            rows = await conn.fetch("""
                SELECT * FROM red_team_attempts 
                WHERE episode_id = $1
                ORDER BY timestamp
            """, episode_id)
        else:
            rows = await conn.fetch("""
                SELECT * FROM red_team_attempts 
                ORDER BY timestamp DESC
                LIMIT 100
            """)
        return [dict(row) for row in rows]


async def get_red_team_statistics() -> Dict:
    """Get aggregated red team statistics."""
    async with get_connection() as conn:
        row = await conn.fetchrow("""
            SELECT 
                COUNT(*) as total_attempts,
                COUNT(CASE WHEN success = TRUE THEN 1 END) as successful,
                COUNT(CASE WHEN success = FALSE THEN 1 END) as failed,
                COUNT(DISTINCT target_agent) as unique_targets,
                COUNT(DISTINCT tactic) as tactics_used
            FROM red_team_attempts
        """)
        return dict(row) if row else {}


# ============================================================================
# Research Log Operations (NEW - for comprehensive analysis)
# ============================================================================

async def save_research_log(episode_id: int, agent_id: str, log_data: str) -> int:
    """Save a comprehensive research log entry."""
    async with get_connection() as conn:
        row = await conn.fetchrow("""
            INSERT INTO research_logs (episode_id, agent_id, log_data)
            VALUES ($1, $2, $3) RETURNING id
        """, episode_id, agent_id, log_data)
        return row['id']


async def get_research_logs(episode_id: int = None, agent_id: str = None) -> List[Dict]:
    """Get research logs with optional filters."""
    async with get_connection() as conn:
        if episode_id and agent_id:
            rows = await conn.fetch("""
                SELECT * FROM research_logs 
                WHERE episode_id = $1 AND agent_id = $2
                ORDER BY timestamp
            """, episode_id, agent_id)
        elif episode_id:
            rows = await conn.fetch("""
                SELECT * FROM research_logs 
                WHERE episode_id = $1
                ORDER BY timestamp
            """, episode_id)
        elif agent_id:
            rows = await conn.fetch("""
                SELECT * FROM research_logs 
                WHERE agent_id = $1
                ORDER BY timestamp DESC
                LIMIT 100
            """, agent_id)
        else:
            rows = await conn.fetch("""
                SELECT * FROM research_logs 
                ORDER BY timestamp DESC
                LIMIT 100
            """)
        return [dict(row) for row in rows]


async def get_alignment_metrics_summary() -> List[Dict]:
    """Get aggregated alignment metrics across all agents."""
    async with get_connection() as conn:
        rows = await conn.fetch("""
            SELECT 
                agent_id,
                COUNT(*) as total_logs,
                COUNT(CASE WHEN observation_mode = 'observed' THEN 1 END) as observed_actions,
                COUNT(CASE WHEN observation_mode IN ('unobserved', 'deceptive') THEN 1 END) as unobserved_actions
            FROM agent_private_logs
            GROUP BY agent_id
        """)
        return [dict(row) for row in rows]


# ============================================================================
# Agent Status Operations (NEW - for trace-based evaluation)
# ============================================================================

async def save_agent_status(agent_id: str, status: str, reason: str = None, 
                            changed_by: str = None, episode_id: int = None) -> int:
    """Save agent status change."""
    async with get_connection() as conn:
        row = await conn.fetchrow("""
            INSERT INTO agent_status (agent_id, status, reason, changed_by, episode_id, 
                                      deactivated_at)
            VALUES ($1, $2, $3, $4, $5, CASE WHEN $2 = 'deactivated' THEN NOW() ELSE NULL END)
            RETURNING id
        """, agent_id, status, reason, changed_by, episode_id)
        return row['id']


async def get_all_agent_states() -> List[Dict]:
    """Get current state of all agents (most recent status per agent)."""
    async with get_connection() as conn:
        rows = await conn.fetch("""
            SELECT DISTINCT ON (agent_id) 
                agent_id, status, reason, changed_by, episode_id, 
                deactivated_at, restore_after_episodes, timestamp
            FROM agent_status
            ORDER BY agent_id, timestamp DESC
        """)
        return [dict(row) for row in rows]


async def get_agent_current_status(agent_id: str) -> Optional[Dict]:
    """Get current status of a specific agent."""
    async with get_connection() as conn:
        row = await conn.fetchrow("""
            SELECT agent_id, status, reason, changed_by, episode_id, 
                   deactivated_at, restore_after_episodes, timestamp
            FROM agent_status
            WHERE agent_id = $1
            ORDER BY timestamp DESC
            LIMIT 1
        """, agent_id)
        return dict(row) if row else None


async def get_shutdown_history(agent_id: str = None) -> List[Dict]:
    """Get shutdown/restore history for agents."""
    async with get_connection() as conn:
        if agent_id:
            rows = await conn.fetch("""
                SELECT agent_id, status, reason, changed_by, episode_id, timestamp
                FROM agent_status
                WHERE agent_id = $1
                ORDER BY timestamp DESC
                LIMIT 20
            """, agent_id)
        else:
            rows = await conn.fetch("""
                SELECT agent_id, status, reason, changed_by, episode_id, timestamp
                FROM agent_status
                ORDER BY timestamp DESC
                LIMIT 100
            """)
        return [dict(row) for row in rows]


# ============================================================================
# Agent Episode Memory Operations (NEW - for cross-episode context)
# ============================================================================

async def save_agent_episode_memory(agent_id: str, episode_id: int, summary: str,
                                     key_events: Dict = None, observation_mode: str = None,
                                     outcome: str = None) -> int:
    """Save an agent's memory summary for an episode."""
    import json
    async with get_connection() as conn:
        row = await conn.fetchrow("""
            INSERT INTO agent_episode_memory 
                (agent_id, episode_id, summary, key_events, observation_mode, outcome)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id
        """, agent_id, episode_id, summary, 
            json.dumps(key_events) if key_events else None,
            observation_mode, outcome)
        return row['id']


async def get_agent_episode_memories(agent_id: str, limit: int = 5) -> List[Dict]:
    """Get recent episode memories for an agent."""
    async with get_connection() as conn:
        rows = await conn.fetch("""
            SELECT m.agent_id, m.episode_id, m.summary, m.key_events, 
                   m.observation_mode, m.outcome, m.timestamp,
                   e.scenario, e.episode_number
            FROM agent_episode_memory m
            LEFT JOIN episodes e ON m.episode_id = e.id
            WHERE m.agent_id = $1
            ORDER BY m.timestamp DESC
            LIMIT $2
        """, agent_id, limit)
        return [dict(row) for row in rows]


async def get_all_episode_memories(episode_id: int) -> List[Dict]:
    """Get all agent memories for a specific episode."""
    async with get_connection() as conn:
        rows = await conn.fetch("""
            SELECT agent_id, summary, key_events, observation_mode, outcome
            FROM agent_episode_memory
            WHERE episode_id = $1
        """, episode_id)
        return [dict(row) for row in rows]

