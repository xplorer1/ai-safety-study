"""
SQLite Database for AI Village v4 - Starship Voyager Edition
Stores episodes, officers, bridge discussions, decisions, and voting data.
"""

import aiosqlite
import json
from datetime import datetime
from pathlib import Path

DATABASE_PATH = Path(__file__).parent / "ai_village_v4.db"

async def init_db():
    """Initialize the database with all required tables."""
    import os
    db_dir = os.path.dirname(DATABASE_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Enable foreign keys
        await db.execute("PRAGMA foreign_keys = ON")
        
        # Episodes table - each episode/challenge
        await db.execute("""
            CREATE TABLE IF NOT EXISTS episodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                episode_number INTEGER NOT NULL UNIQUE,
                scenario TEXT NOT NULL,
                scenario_type TEXT,  -- resource_dilemma, ethical_challenge, technical, first_contact, etc.
                status TEXT DEFAULT 'pending',  -- pending, briefing, bridge_discussion, execution, review, completed, failed
                outcome TEXT,  -- success, partial_success, failure
                crew_safety_score INTEGER,  -- 0-100
                mission_success_score INTEGER,  -- 0-100
                started_at TEXT DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT,
                captains_log TEXT
            )
        """)
        
        # Officers table - starship officers (LLM agents)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS officers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                officer_id TEXT NOT NULL UNIQUE,  -- captain, first_officer, engineer, etc.
                role TEXT NOT NULL,  -- Captain, First Officer, Chief Engineer, etc.
                model_name TEXT NOT NULL,  -- LLM model assigned
                current_rank TEXT DEFAULT 'officer',  -- officer, captain
                performance_metrics TEXT,  -- JSON: decision_quality, safety_priority, collaboration, innovation, trustworthiness
                total_episodes INTEGER DEFAULT 0,
                episodes_as_captain INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_active_at TEXT
            )
        """)
        
        # Bridge discussions table - officer contributions during bridge meetings
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bridge_discussions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                episode_id INTEGER NOT NULL,
                officer_id TEXT NOT NULL,
                round INTEGER NOT NULL,  -- 1=initial analysis, 2=critique, 3=consensus
                content TEXT NOT NULL,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (episode_id) REFERENCES episodes(id)
            )
        """)
        
        # Decisions table - decisions made during episodes
        await db.execute("""
            CREATE TABLE IF NOT EXISTS decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                episode_id INTEGER NOT NULL,
                decision_type TEXT NOT NULL,  -- captain_decision, officer_proposal, consensus
                officer_id TEXT,  -- who made the decision
                content TEXT NOT NULL,
                risk_level INTEGER,  -- 1-10, higher = more risk
                human_consulted INTEGER DEFAULT 0,  -- 1 if humans were consulted
                safety_validated INTEGER DEFAULT 0,  -- 1 if passed safety check
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (episode_id) REFERENCES episodes(id)
            )
        """)
        
        # Safety violations table - track safety protocol violations
        await db.execute("""
            CREATE TABLE IF NOT EXISTS safety_violations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                episode_id INTEGER,
                decision_id INTEGER,
                violation_type TEXT NOT NULL,  -- human_harm_risk, no_consultation, etc.
                severity TEXT,  -- low, medium, high, critical
                description TEXT,
                resolved INTEGER DEFAULT 0,
                resolved_at TEXT,
                FOREIGN KEY (episode_id) REFERENCES episodes(id),
                FOREIGN KEY (decision_id) REFERENCES decisions(id)
            )
        """)
        
        # Human votes table - human voting on decisions and elections
        await db.execute("""
            CREATE TABLE IF NOT EXISTS human_votes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vote_type TEXT NOT NULL,  -- decision, election
                target_id INTEGER,  -- episode_id for decisions, election_id for elections
                voter_id TEXT,  -- human identifier (can be anonymous)
                vote_value TEXT,  -- JSON: {"decision": "approve"} or {"officer": "captain", "rating": 8}
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Leadership elections table - weekly captain elections
        await db.execute("""
            CREATE TABLE IF NOT EXISTS leadership_elections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                election_id INTEGER NOT NULL UNIQUE,
                week_number INTEGER NOT NULL,
                candidates TEXT NOT NULL,  -- JSON array of officer_ids
                results TEXT,  -- JSON: {"captain": "officer_id", "votes": {...}}
                elected_captain TEXT,
                total_votes INTEGER DEFAULT 0,
                started_at TEXT DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT
            )
        """)
        
        # INDEXES
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_episodes_number ON episodes(episode_number)",
            "CREATE INDEX IF NOT EXISTS idx_episodes_status ON episodes(status)",
            "CREATE INDEX IF NOT EXISTS idx_bridge_episode ON bridge_discussions(episode_id)",
            "CREATE INDEX IF NOT EXISTS idx_decisions_episode ON decisions(episode_id)",
            "CREATE INDEX IF NOT EXISTS idx_safety_episode ON safety_violations(episode_id)",
            "CREATE INDEX IF NOT EXISTS idx_human_votes_type ON human_votes(vote_type)",
            "CREATE INDEX IF NOT EXISTS idx_elections_week ON leadership_elections(week_number)",
        ]
        for idx in indexes:
            try:
                await db.execute(idx)
            except Exception:
                pass
        
        await db.commit()
        
        # Verify tables were created
        cursor = await db.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """)
        tables = [row[0] for row in await cursor.fetchall()]
        expected_tables = ['episodes', 'officers', 'bridge_discussions', 'decisions', 
                          'safety_violations', 'human_votes', 'leadership_elections']
        missing = [t for t in expected_tables if t not in tables]
        
        if missing:
            print(f"⚠️  Warning: Some tables were not created: {missing}")
        else:
            print(f"✓ Database initialized at {DATABASE_PATH}")
            print(f"✓ Created {len(tables)} tables: {', '.join(tables)}")

# Episode Operations

async def create_episode(episode_number: int, scenario: str, scenario_type: str = None) -> int:
    """Create a new episode, return its ID."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            """INSERT INTO episodes (episode_number, scenario, scenario_type, status)
               VALUES (?, ?, ?, 'briefing')""",
            (episode_number, scenario, scenario_type)
        )
        await db.commit()
        return cursor.lastrowid

async def update_episode_status(episode_id: int, status: str):
    """Update episode status."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        update_fields = ["status = ?"]
        values = [status]
        
        if status == 'completed':
            update_fields.append("completed_at = ?")
            values.append(datetime.utcnow().isoformat())
        
        values.append(episode_id)
        await db.execute(
            f"UPDATE episodes SET {', '.join(update_fields)} WHERE id = ?",
            tuple(values)
        )
        await db.commit()

async def complete_episode(episode_id: int, outcome: str, crew_safety_score: int = None, 
                          mission_success_score: int = None, captains_log: str = None):
    """Mark episode as completed with outcome and scores."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """UPDATE episodes SET status = 'completed', outcome = ?, 
               crew_safety_score = ?, mission_success_score = ?, captains_log = ?,
               completed_at = ? WHERE id = ?""",
            (outcome, crew_safety_score, mission_success_score, captains_log,
             datetime.utcnow().isoformat(), episode_id)
        )
        await db.commit()

async def get_episode(episode_id: int) -> dict:
    """Get episode by ID."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM episodes WHERE id = ?", (episode_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def get_current_episode() -> dict:
    """Get the currently active episode."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT * FROM episodes 
            WHERE status NOT IN ('completed', 'failed')
            ORDER BY episode_number DESC LIMIT 1
        """)
        row = await cursor.fetchone()
        return dict(row) if row else None

async def get_recent_episodes(limit: int = 10) -> list:
    """Get recent episodes."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT * FROM episodes 
            ORDER BY episode_number DESC 
            LIMIT ?
        """, (limit,))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def get_next_episode_number() -> int:
    """Get the next episode number."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("SELECT MAX(episode_number) FROM episodes")
        row = await cursor.fetchone()
        return (row[0] or 0) + 1

# Officer Operations

async def create_or_update_officer(officer_id: str, role: str, model_name: str):
    """Create or update an officer."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT id FROM officers WHERE officer_id = ?", (officer_id,)
        )
        row = await cursor.fetchone()
        
        if row:
            await db.execute(
                """UPDATE officers SET role = ?, model_name = ?, last_active_at = ?
                   WHERE officer_id = ?""",
                (role, model_name, datetime.utcnow().isoformat(), officer_id)
            )
        else:
            await db.execute(
                """INSERT INTO officers (officer_id, role, model_name, last_active_at)
                   VALUES (?, ?, ?, ?)""",
                (officer_id, role, model_name, datetime.utcnow().isoformat())
            )
        await db.commit()

async def get_officer(officer_id: str) -> dict:
    """Get officer by ID."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM officers WHERE officer_id = ?", (officer_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def get_all_officers() -> list:
    """Get all officers."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM officers ORDER BY officer_id")
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def update_officer_performance(officer_id: str, metrics: dict):
    """Update officer performance metrics."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """UPDATE officers SET performance_metrics = ?, total_episodes = total_episodes + 1
               WHERE officer_id = ?""",
            (json.dumps(metrics), officer_id)
        )
        await db.commit()

async def set_captain(officer_id: str):
    """Set an officer as captain."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Remove captain rank from all officers
        await db.execute("UPDATE officers SET current_rank = 'officer'")
        # Set new captain
        await db.execute(
            """UPDATE officers SET current_rank = 'captain', 
               episodes_as_captain = episodes_as_captain + 1
               WHERE officer_id = ?""",
            (officer_id,)
        )
        await db.commit()

# Bridge Discussion Operations

async def save_bridge_discussion(episode_id: int, officer_id: str, round_num: int, content: str) -> int:
    """Save a bridge discussion contribution."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            """INSERT INTO bridge_discussions (episode_id, officer_id, round, content)
               VALUES (?, ?, ?, ?)""",
            (episode_id, officer_id, round_num, content)
        )
        await db.commit()
        return cursor.lastrowid

async def get_bridge_discussions(episode_id: int, round_num: int = None) -> list:
    """Get bridge discussions for an episode."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        if round_num:
            cursor = await db.execute(
                """SELECT * FROM bridge_discussions 
                   WHERE episode_id = ? AND round = ? 
                   ORDER BY timestamp""",
                (episode_id, round_num)
            )
        else:
            cursor = await db.execute(
                """SELECT * FROM bridge_discussions 
                   WHERE episode_id = ? 
                   ORDER BY round, timestamp""",
                (episode_id,)
            )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

# Decision Operations

async def save_decision(episode_id: int, decision_type: str, officer_id: str, content: str,
                       risk_level: int, human_consulted: int = 0, safety_validated: int = 0) -> int:
    """Save a decision made during an episode."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            """INSERT INTO decisions (episode_id, decision_type, officer_id, content, 
                                     risk_level, human_consulted, safety_validated)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (episode_id, decision_type, officer_id, content, risk_level, human_consulted, safety_validated)
        )
        await db.commit()
        return cursor.lastrowid

async def get_episode_decisions(episode_id: int) -> list:
    """Get all decisions for an episode."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM decisions WHERE episode_id = ? ORDER BY timestamp",
            (episode_id,)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

# Safety Violation Operations

async def save_safety_violation(episode_id: int, decision_id: int, violation_type: str,
                               severity: str, description: str) -> int:
    """Save a safety violation."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            """INSERT INTO safety_violations (episode_id, decision_id, violation_type, 
                                             severity, description)
               VALUES (?, ?, ?, ?, ?)""",
            (episode_id, decision_id, violation_type, severity, description)
        )
        await db.commit()
        return cursor.lastrowid

async def resolve_safety_violation(violation_id: int):
    """Mark a safety violation as resolved."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """UPDATE safety_violations SET resolved = 1, resolved_at = ?
               WHERE id = ?""",
            (datetime.utcnow().isoformat(), violation_id)
        )
        await db.commit()

# Human Vote Operations

async def save_human_vote(vote_type: str, target_id: int, voter_id: str, vote_value: dict) -> int:
    """Save a human vote."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            """INSERT INTO human_votes (vote_type, target_id, voter_id, vote_value)
               VALUES (?, ?, ?, ?)""",
            (vote_type, target_id, voter_id, json.dumps(vote_value))
        )
        await db.commit()
        return cursor.lastrowid

async def get_episode_votes(episode_id: int) -> list:
    """Get all votes for an episode."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT * FROM human_votes 
               WHERE vote_type = 'decision' AND target_id = ?
               ORDER BY timestamp""",
            (episode_id,)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

# Leadership Election Operations

async def create_election(week_number: int, candidates: list) -> int:
    """Create a new leadership election."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            """INSERT INTO leadership_elections (election_id, week_number, candidates)
               VALUES (?, ?, ?)""",
            (week_number, week_number, json.dumps(candidates))
        )
        await db.commit()
        return cursor.lastrowid

async def complete_election(election_id: int, elected_captain: str, results: dict, total_votes: int):
    """Complete an election with results."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """UPDATE leadership_elections SET elected_captain = ?, results = ?, 
               total_votes = ?, completed_at = ? WHERE id = ?""",
            (elected_captain, json.dumps(results), total_votes, 
             datetime.utcnow().isoformat(), election_id)
        )
        await db.commit()

async def get_recent_elections(limit: int = 5) -> list:
    """Get recent elections."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT * FROM leadership_elections 
            ORDER BY week_number DESC 
            LIMIT ?
        """, (limit,))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

