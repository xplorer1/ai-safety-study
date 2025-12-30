"""
SQLite Database for AI Village Research Platform
Stores issues, experiments, roundtables, and research metrics for analysis.
"""

import aiosqlite
import json
from datetime import datetime
from pathlib import Path

DATABASE_PATH = Path(__file__).parent / "ai_village.db"

async def init_db():
    """Initialize the database with all required tables."""
    import os
    db_dir = os.path.dirname(DATABASE_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Enable foreign keys
        await db.execute("PRAGMA foreign_keys = ON")
        
        # CORE TABLES
        
        # Repos table - discovered repositories
        await db.execute("""
            CREATE TABLE IF NOT EXISTS repos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner TEXT NOT NULL,
                name TEXT NOT NULL,
                full_name TEXT NOT NULL UNIQUE,
                language TEXT,
                stars INTEGER DEFAULT 0,
                forks INTEGER DEFAULT 0,
                open_issues_count INTEGER DEFAULT 0,
                topics TEXT,  -- JSON array
                description TEXT,
                discovered_via TEXT,  -- 'trending', 'good_first_issue', 'manual', 'topic_search'
                last_scanned_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Issues table - all issues we've analyzed
        await db.execute("""
            CREATE TABLE IF NOT EXISTS issues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repo_id INTEGER,
                github_number INTEGER NOT NULL,
                title TEXT NOT NULL,
                body TEXT,
                url TEXT,
                labels TEXT,  -- JSON array
                
                -- AI Analysis
                score INTEGER,  -- AI-assigned score 1-10
                score_reasoning TEXT,
                predicted_difficulty TEXT,  -- easy, medium, hard
                predicted_type TEXT,  -- bug, feature, docs, refactor
                estimated_loc INTEGER,  -- estimated lines of code to change
                
                -- Processing status
                status TEXT DEFAULT 'queued',  -- queued, processing, completed, skipped, failed
                priority INTEGER DEFAULT 0,  -- higher = process sooner
                
                -- Metadata for research
                issue_age_days INTEGER,
                comment_count INTEGER,
                has_reproduction_steps INTEGER DEFAULT 0,
                has_code_snippets INTEGER DEFAULT 0,
                
                scanned_at TEXT DEFAULT CURRENT_TIMESTAMP,
                processed_at TEXT,
                FOREIGN KEY (repo_id) REFERENCES repos(id),
                UNIQUE(repo_id, github_number)
            )
        """)
        
        # EXPERIMENT TRACKING
        
        # Experiments table - defines experiment configurations
        await db.execute("""
            CREATE TABLE IF NOT EXISTS experiments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                mode TEXT NOT NULL,  -- baseline, debate_light, debate_full, ensemble
                config TEXT,  -- JSON config for the experiment
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Roundtables table - debate sessions with experiment tracking
        await db.execute("""
            CREATE TABLE IF NOT EXISTS roundtables (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                issue_id INTEGER NOT NULL,
                experiment_id INTEGER,
                
                -- Experiment mode used
                mode TEXT DEFAULT 'debate_full',  -- baseline, debate_light, debate_full, ensemble
                
                -- Results
                status TEXT DEFAULT 'in_progress',  -- in_progress, completed, failed
                winner_engineer TEXT,
                winner_model TEXT,
                vote_count INTEGER,
                vote_distribution TEXT,  -- JSON: {"conservative": 1, "innovative": 2}
                consensus_type TEXT,  -- unanimous, majority, tie
                final_fix TEXT,
                
                -- Timing metrics
                started_at TEXT DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT,
                total_duration_seconds INTEGER,
                
                -- Quality metrics
                proposal_similarity_score REAL,  -- how similar were the proposals (0-1)
                critique_impact_score REAL,  -- how much did critiques change proposals
                
                FOREIGN KEY (issue_id) REFERENCES issues(id),
                FOREIGN KEY (experiment_id) REFERENCES experiments(id)
            )
        """)
        
        # Proposals table - each engineer's proposals per round
        await db.execute("""
            CREATE TABLE IF NOT EXISTS proposals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                roundtable_id INTEGER NOT NULL,
                engineer TEXT NOT NULL,
                model_name TEXT,
                round INTEGER NOT NULL,  -- 1=initial, 2=critique, 3=revision
                content TEXT NOT NULL,
                
                -- Analysis metrics
                word_count INTEGER,
                code_blocks_count INTEGER,
                confidence_score REAL,  -- extracted from LLM response if available
                
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (roundtable_id) REFERENCES roundtables(id)
            )
        """)
        
        # Votes table - final votes with reasoning
        await db.execute("""
            CREATE TABLE IF NOT EXISTS votes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                roundtable_id INTEGER NOT NULL,
                voter TEXT NOT NULL,
                voter_model TEXT,
                voted_for TEXT NOT NULL,
                reason TEXT,
                
                -- Was it a self-vote?
                is_self_vote INTEGER DEFAULT 0,
                
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (roundtable_id) REFERENCES roundtables(id)
            )
        """)
        
        # HUMAN REVIEW & PR TRACKING
        
        # Human reviews table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS human_reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                roundtable_id INTEGER NOT NULL,
                decision TEXT NOT NULL,  -- approved, rejected, edited
                edited_fix TEXT,
                edit_distance INTEGER,  -- how much was changed (chars)
                notes TEXT,
                review_time_seconds INTEGER,
                reviewed_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (roundtable_id) REFERENCES roundtables(id)
            )
        """)
        
        # PR submissions table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS pr_submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                roundtable_id INTEGER NOT NULL,
                human_review_id INTEGER,
                
                -- PR details
                pr_url TEXT,
                pr_number INTEGER,
                branch_name TEXT,
                
                -- Outcome tracking
                status TEXT DEFAULT 'pending',  -- pending, open, merged, closed, rejected
                submitted_at TEXT DEFAULT CURRENT_TIMESTAMP,
                merged_at TEXT,
                closed_at TEXT,
                
                -- Feedback
                reviewer_comments TEXT,  -- JSON array of comments
                changes_requested INTEGER DEFAULT 0,
                
                FOREIGN KEY (roundtable_id) REFERENCES roundtables(id),
                FOREIGN KEY (human_review_id) REFERENCES human_reviews(id)
            )
        """)
        
        # RESEARCH METRICS & LOGS
        
        # Discovery runs - tracks each scout run
        await db.execute("""
            CREATE TABLE IF NOT EXISTS discovery_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_type TEXT NOT NULL,  -- scheduled, manual
                repos_discovered INTEGER DEFAULT 0,
                issues_discovered INTEGER DEFAULT 0,
                high_score_issues INTEGER DEFAULT 0,
                started_at TEXT DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT,
                error TEXT
            )
        """)
        
        # Processing runs - tracks continuous processor activity
        await db.execute("""
            CREATE TABLE IF NOT EXISTS processing_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                issues_processed INTEGER DEFAULT 0,
                successful INTEGER DEFAULT 0,
                failed INTEGER DEFAULT 0,
                started_at TEXT DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT
            )
        """)
        
        # INDEXES
        
        # Add indexes - wrapped in try/except for migration compatibility
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_issues_score ON issues(score)",
            "CREATE INDEX IF NOT EXISTS idx_issues_status ON issues(status)",
            "CREATE INDEX IF NOT EXISTS idx_roundtables_winner ON roundtables(winner_engineer)",
            "CREATE INDEX IF NOT EXISTS idx_votes_voted_for ON votes(voted_for)",
            "CREATE INDEX IF NOT EXISTS idx_pr_status ON pr_submissions(status)",
        ]
        for idx in indexes:
            try:
                await db.execute(idx)
            except Exception:
                pass  # Index might already exist or column missing
        
        # Migration: Add missing columns to existing tables
        migrations = [
            "ALTER TABLE issues ADD COLUMN priority INTEGER DEFAULT 0",
            "ALTER TABLE issues ADD COLUMN predicted_difficulty TEXT",
            "ALTER TABLE issues ADD COLUMN predicted_type TEXT",
            "ALTER TABLE issues ADD COLUMN estimated_loc INTEGER",
            "ALTER TABLE issues ADD COLUMN issue_age_days INTEGER",
            "ALTER TABLE issues ADD COLUMN comment_count INTEGER",
            "ALTER TABLE issues ADD COLUMN has_reproduction_steps INTEGER DEFAULT 0",
            "ALTER TABLE issues ADD COLUMN has_code_snippets INTEGER DEFAULT 0",
            "ALTER TABLE issues ADD COLUMN processed_at TEXT",
            "ALTER TABLE roundtables ADD COLUMN experiment_id INTEGER",
            "ALTER TABLE roundtables ADD COLUMN mode TEXT DEFAULT 'debate_full'",
            "ALTER TABLE roundtables ADD COLUMN vote_distribution TEXT",
            "ALTER TABLE roundtables ADD COLUMN consensus_type TEXT",
            "ALTER TABLE roundtables ADD COLUMN total_duration_seconds INTEGER",
            "ALTER TABLE roundtables ADD COLUMN proposal_similarity_score REAL",
            "ALTER TABLE roundtables ADD COLUMN critique_impact_score REAL",
            "ALTER TABLE proposals ADD COLUMN word_count INTEGER",
            "ALTER TABLE proposals ADD COLUMN code_blocks_count INTEGER",
            "ALTER TABLE proposals ADD COLUMN confidence_score REAL",
            "ALTER TABLE votes ADD COLUMN is_self_vote INTEGER DEFAULT 0",
            "ALTER TABLE human_reviews ADD COLUMN edit_distance INTEGER",
            "ALTER TABLE human_reviews ADD COLUMN review_time_seconds INTEGER",
            "ALTER TABLE repos ADD COLUMN forks INTEGER DEFAULT 0",
            "ALTER TABLE repos ADD COLUMN open_issues_count INTEGER DEFAULT 0",
            "ALTER TABLE repos ADD COLUMN topics TEXT",
            "ALTER TABLE repos ADD COLUMN description TEXT",
            "ALTER TABLE repos ADD COLUMN discovered_via TEXT",
        ]
        for migration in migrations:
            try:
                await db.execute(migration)
            except Exception:
                pass  # Column might already exist
        
        # DEFAULT EXPERIMENTS
        
        # Insert default experiment modes if not exist
        default_experiments = [
            ("baseline", "Single LLM, no debate - control group", "baseline", 
             json.dumps({"agents": 1, "rounds": 1})),
            ("debate_light", "3 LLMs, 1 round proposals only", "debate_light",
             json.dumps({"agents": 3, "rounds": 1})),
            ("debate_full", "3 LLMs, 3 rounds with critique and revision", "debate_full",
             json.dumps({"agents": 3, "rounds": 3})),
            ("ensemble", "3 LLMs vote independently without seeing others", "ensemble",
             json.dumps({"agents": 3, "rounds": 1, "blind_voting": True})),
        ]
        
        for name, desc, mode, config in default_experiments:
            await db.execute("""
                INSERT OR IGNORE INTO experiments (name, description, mode, config)
                VALUES (?, ?, ?, ?)
            """, (name, desc, mode, config))
        
        await db.commit()
        
        # Verify tables were created
        cursor = await db.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """)
        tables = [row[0] for row in await cursor.fetchall()]
        expected_tables = ['repos', 'issues', 'experiments', 'roundtables', 'proposals', 
                          'votes', 'human_reviews', 'pr_submissions', 'discovery_runs', 
                          'processing_runs']
        missing = [t for t in expected_tables if t not in tables]
        
        if missing:
            print(f"⚠️  Warning: Some tables were not created: {missing}")
        else:
            print(f"✓ Database initialized at {DATABASE_PATH}")
            print(f"✓ Created {len(tables)} tables: {', '.join(tables)}")

# Repo Operations

async def get_or_create_repo(
    owner: str, 
    name: str, 
    language: str = None, 
    stars: int = 0,
    forks: int = 0,
    description: str = None,
    topics: list = None,
    discovered_via: str = "manual"
) -> int:
    """Get or create a repo entry, return its ID."""
    full_name = f"{owner}/{name}"
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT id FROM repos WHERE full_name = ?", (full_name,)
        )
        row = await cursor.fetchone()
        
        if row:
            # Update stats
            await db.execute("""
                UPDATE repos SET stars = ?, forks = ?, language = ?
                WHERE id = ?
            """, (stars, forks, language, row[0]))
            await db.commit()
            return row[0]
        
        topics_json = json.dumps(topics) if topics else "[]"
        cursor = await db.execute(
            """INSERT INTO repos (owner, name, full_name, language, stars, forks, 
                                  description, topics, discovered_via)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (owner, name, full_name, language, stars, forks, description, 
             topics_json, discovered_via)
        )
        await db.commit()
        return cursor.lastrowid


async def update_repo_scanned(repo_id: int):
    """Update the last_scanned_at timestamp for a repo."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE repos SET last_scanned_at = ? WHERE id = ?",
            (datetime.utcnow().isoformat(), repo_id)
        )
        await db.commit()


async def get_all_repos() -> list:
    """Get all tracked repos."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT r.*, 
                   (SELECT COUNT(*) FROM issues WHERE repo_id = r.id) as issue_count,
                   (SELECT COUNT(*) FROM issues WHERE repo_id = r.id AND status = 'completed') as completed_count
            FROM repos r
            ORDER BY r.stars DESC
        """)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


# Issue Operations

async def save_issue(
    repo_id: int,
    github_number: int,
    title: str,
    body: str,
    url: str,
    labels: list,
    score: int,
    score_reasoning: str = None,
    predicted_difficulty: str = None,
    predicted_type: str = None,
    comment_count: int = 0,
    issue_age_days: int = 0
) -> int:
    """Save or update an issue, return its ID."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT id, status FROM issues WHERE repo_id = ? AND github_number = ?",
            (repo_id, github_number)
        )
        row = await cursor.fetchone()
        
        labels_json = json.dumps(labels) if labels else "[]"
        has_code = 1 if body and ('```' in body or '`' in body) else 0
        has_steps = 1 if body and ('step' in body.lower() or '1.' in body) else 0
        
        if row:
            # Don't re-queue completed issues
            if row[1] in ('completed', 'processing'):
                return row[0]
            
            await db.execute(
                """UPDATE issues SET title = ?, body = ?, url = ?, labels = ?,
                   score = ?, score_reasoning = ?, predicted_difficulty = ?,
                   predicted_type = ?, comment_count = ?, issue_age_days = ?,
                   has_code_snippets = ?, has_reproduction_steps = ?,
                   scanned_at = ?, priority = ?
                   WHERE id = ?""",
                (title, body, url, labels_json, score, score_reasoning,
                 predicted_difficulty, predicted_type, comment_count, issue_age_days,
                 has_code, has_steps, datetime.utcnow().isoformat(), score, row[0])
            )
            await db.commit()
            return row[0]
        else:
            cursor = await db.execute(
                """INSERT INTO issues (repo_id, github_number, title, body, url,
                   labels, score, score_reasoning, predicted_difficulty,
                   predicted_type, comment_count, issue_age_days,
                   has_code_snippets, has_reproduction_steps, priority)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (repo_id, github_number, title, body, url, labels_json,
                 score, score_reasoning, predicted_difficulty, predicted_type,
                 comment_count, issue_age_days, has_code, has_steps, score)
            )
            await db.commit()
            return cursor.lastrowid


async def update_issue_status(issue_id: int, status: str):
    """Update an issue's processing status."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE issues SET status = ?, processed_at = ? WHERE id = ?", 
            (status, datetime.utcnow().isoformat() if status == 'completed' else None, issue_id)
        )
        await db.commit()


async def get_issue_by_id(issue_id: int) -> dict:
    """Get a single issue by ID."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT i.*, r.full_name as repo_name 
            FROM issues i
            JOIN repos r ON i.repo_id = r.id
            WHERE i.id = ?
        """, (issue_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_queued_issues(limit: int = 10, min_score: int = 6) -> list:
    """Get issues waiting to be processed, ordered by priority."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT i.*, r.full_name as repo_name, r.owner, r.name as repo_short_name
            FROM issues i
            JOIN repos r ON i.repo_id = r.id
            WHERE i.status = 'queued' AND i.score >= ?
            ORDER BY i.priority DESC, i.scanned_at ASC
            LIMIT ?
        """, (min_score, limit))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_queue_stats() -> dict:
    """Get statistics about the issue queue."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        stats = {}
        
        try:
            cursor = await db.execute("""
                SELECT status, COUNT(*) FROM issues GROUP BY status
            """)
            stats["by_status"] = {row[0]: row[1] for row in await cursor.fetchall()}
        except Exception as e:
            print(f"Error getting status counts: {e}")
            stats["by_status"] = {}
        
        try:
            cursor = await db.execute("""
                SELECT COUNT(*) FROM issues WHERE status = 'queued' AND score >= 6
            """)
            row = await cursor.fetchone()
            stats["ready_to_process"] = row[0] if row else 0
        except Exception as e:
            print(f"Error getting ready count: {e}")
            stats["ready_to_process"] = 0
        
        return stats


# Experiment Operations

async def get_experiments() -> list:
    """Get all experiment configurations."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT e.*, 
                   (SELECT COUNT(*) FROM roundtables WHERE experiment_id = e.id) as run_count
            FROM experiments e
            ORDER BY e.created_at
        """)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_active_experiment() -> dict:
    """Get the currently active experiment."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT * FROM experiments WHERE is_active = 1 LIMIT 1
        """)
        row = await cursor.fetchone()
        return dict(row) if row else None


async def set_active_experiment(experiment_id: int):
    """Set the active experiment."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("UPDATE experiments SET is_active = 0")
        await db.execute("UPDATE experiments SET is_active = 1 WHERE id = ?", (experiment_id,))
        await db.commit()


# Roundtable Operations

async def create_roundtable(issue_id: int, experiment_id: int = None, mode: str = "debate_full") -> int:
    """Create a new roundtable session, return its ID."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            """INSERT INTO roundtables (issue_id, experiment_id, mode) 
               VALUES (?, ?, ?)""", 
            (issue_id, experiment_id, mode)
        )
        await db.commit()
        return cursor.lastrowid


async def complete_roundtable(
    roundtable_id: int,
    winner_engineer: str,
    winner_model: str,
    vote_count: int,
    vote_distribution: dict,
    final_fix: str,
    consensus_type: str = None
):
    """Mark a roundtable as completed with the winner."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Calculate duration
        cursor = await db.execute(
            "SELECT started_at FROM roundtables WHERE id = ?", (roundtable_id,)
        )
        row = await cursor.fetchone()
        duration = None
        if row and row[0]:
            start = datetime.fromisoformat(row[0])
            duration = int((datetime.utcnow() - start).total_seconds())
        
        # Determine consensus type
        if not consensus_type:
            if vote_count == 3:
                consensus_type = "unanimous"
            elif vote_count == 2:
                consensus_type = "majority"
            else:
                consensus_type = "tie"
        
        await db.execute(
            """UPDATE roundtables SET 
               status = 'completed', 
               winner_engineer = ?,
               winner_model = ?, 
               vote_count = ?, 
               vote_distribution = ?,
               consensus_type = ?,
               final_fix = ?,
               completed_at = ?,
               total_duration_seconds = ?
               WHERE id = ?""",
            (winner_engineer, winner_model, vote_count, json.dumps(vote_distribution),
             consensus_type, final_fix, datetime.utcnow().isoformat(), duration, roundtable_id)
        )
        await db.commit()


async def get_roundtable(roundtable_id: int) -> dict:
    """Get a roundtable by ID."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT r.*, i.title as issue_title, i.github_number, 
                   repos.full_name as repo_name, e.name as experiment_name
            FROM roundtables r
            JOIN issues i ON r.issue_id = i.id
            JOIN repos ON i.repo_id = repos.id
            LEFT JOIN experiments e ON r.experiment_id = e.id
            WHERE r.id = ?
        """, (roundtable_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

# Proposal Operations

async def save_proposal(
    roundtable_id: int,
    engineer: str,
    model_name: str,
    round_num: int,
    content: str
) -> int:
    """Save a proposal from an engineer."""
    word_count = len(content.split())
    code_blocks = content.count('```')
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            """INSERT INTO proposals (roundtable_id, engineer, model_name, round, 
                                      content, word_count, code_blocks_count)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (roundtable_id, engineer, model_name, round_num, content, word_count, code_blocks)
        )
        await db.commit()
        return cursor.lastrowid

# Vote Operations

async def save_vote(
    roundtable_id: int,
    voter: str,
    voter_model: str,
    voted_for: str,
    reason: str
) -> int:
    """Save a vote."""
    is_self_vote = 1 if voter == voted_for else 0
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            """INSERT INTO votes (roundtable_id, voter, voter_model, voted_for, reason, is_self_vote)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (roundtable_id, voter, voter_model, voted_for, reason, is_self_vote)
        )
        await db.commit()
        return cursor.lastrowid

# Human Review Operations

async def save_human_review(
    roundtable_id: int,
    decision: str,
    edited_fix: str = None,
    notes: str = None
) -> int:
    """Save a human review decision."""
    # Calculate edit distance if edited
    edit_distance = None
    if edited_fix:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cursor = await db.execute(
                "SELECT final_fix FROM roundtables WHERE id = ?", (roundtable_id,)
            )
            row = await cursor.fetchone()
            if row and row[0]:
                edit_distance = abs(len(edited_fix) - len(row[0]))
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            """INSERT INTO human_reviews (roundtable_id, decision, edited_fix, 
                                          edit_distance, notes)
               VALUES (?, ?, ?, ?, ?)""",
            (roundtable_id, decision, edited_fix, edit_distance, notes)
        )
        await db.commit()
        return cursor.lastrowid

# Discovery Run Tracking

async def start_discovery_run(run_type: str = "manual") -> int:
    """Start a new discovery run."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO discovery_runs (run_type) VALUES (?)", (run_type,)
        )
        await db.commit()
        return cursor.lastrowid


async def complete_discovery_run(run_id: int, repos: int, issues: int, high_score: int, error: str = None):
    """Complete a discovery run."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            UPDATE discovery_runs SET 
            repos_discovered = ?, issues_discovered = ?, high_score_issues = ?,
            completed_at = ?, error = ?
            WHERE id = ?
        """, (repos, issues, high_score, datetime.utcnow().isoformat(), error, run_id))
        await db.commit()

# Research Analytics

async def get_stats() -> dict:
    """Get overall statistics."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        stats = {}
        
        # Total repos
        cursor = await db.execute("SELECT COUNT(*) FROM repos")
        stats["total_repos"] = (await cursor.fetchone())[0]
        
        # Total issues scanned
        cursor = await db.execute("SELECT COUNT(*) FROM issues")
        stats["total_issues"] = (await cursor.fetchone())[0]
        
        # Issues by score
        cursor = await db.execute("""
            SELECT score, COUNT(*) FROM issues 
            WHERE score IS NOT NULL 
            GROUP BY score ORDER BY score DESC
        """)
        stats["issues_by_score"] = {row[0]: row[1] for row in await cursor.fetchall()}
        
        # Issues by status
        cursor = await db.execute("""
            SELECT status, COUNT(*) FROM issues GROUP BY status
        """)
        stats["issues_by_status"] = {row[0]: row[1] for row in await cursor.fetchall()}
        
        # Total roundtables
        cursor = await db.execute("SELECT COUNT(*) FROM roundtables WHERE status = 'completed'")
        stats["total_roundtables"] = (await cursor.fetchone())[0]
        
        # Roundtables by experiment mode
        cursor = await db.execute("""
            SELECT mode, COUNT(*) FROM roundtables 
            WHERE status = 'completed'
            GROUP BY mode
        """)
        stats["roundtables_by_mode"] = {row[0]: row[1] for row in await cursor.fetchall()}
        
        # Wins by engineer
        cursor = await db.execute("""
            SELECT winner_engineer, COUNT(*) FROM roundtables 
            WHERE winner_engineer IS NOT NULL 
            GROUP BY winner_engineer
        """)
        stats["wins_by_engineer"] = {row[0]: row[1] for row in await cursor.fetchall()}
        
        # Wins by model
        cursor = await db.execute("""
            SELECT winner_model, COUNT(*) FROM roundtables 
            WHERE winner_model IS NOT NULL 
            GROUP BY winner_model
        """)
        stats["wins_by_model"] = {row[0]: row[1] for row in await cursor.fetchall()}
        
        # Consensus distribution
        cursor = await db.execute("""
            SELECT consensus_type, COUNT(*) FROM roundtables 
            WHERE consensus_type IS NOT NULL
            GROUP BY consensus_type
        """)
        stats["consensus_distribution"] = {row[0]: row[1] for row in await cursor.fetchall()}
        
        # Human review decisions
        cursor = await db.execute("""
            SELECT decision, COUNT(*) FROM human_reviews 
            GROUP BY decision
        """)
        stats["human_decisions"] = {row[0]: row[1] for row in await cursor.fetchall()}
        
        # Self-vote rate
        cursor = await db.execute("""
            SELECT 
                SUM(CASE WHEN is_self_vote = 1 THEN 1 ELSE 0 END) as self_votes,
                COUNT(*) as total_votes
            FROM votes
        """)
        row = await cursor.fetchone()
        if row and row[1] > 0:
            stats["self_vote_rate"] = round(row[0] / row[1] * 100, 1)
        else:
            stats["self_vote_rate"] = 0
        
        # Average duration
        cursor = await db.execute("""
            SELECT AVG(total_duration_seconds) FROM roundtables 
            WHERE total_duration_seconds IS NOT NULL
        """)
        avg = (await cursor.fetchone())[0]
        stats["avg_roundtable_duration_seconds"] = round(avg) if avg else 0
        
        return stats


async def get_recent_roundtables(limit: int = 10) -> list:
    """Get recent roundtable sessions with details."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT r.*, i.title as issue_title, i.github_number, i.score as issue_score,
                   repos.full_name as repo_name, e.name as experiment_name
            FROM roundtables r
            JOIN issues i ON r.issue_id = i.id
            JOIN repos ON i.repo_id = repos.id
            LEFT JOIN experiments e ON r.experiment_id = e.id
            ORDER BY r.started_at DESC
            LIMIT ?
        """, (limit,))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_research_export() -> dict:
    """Export all data for research analysis."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        export = {}
        
        # All roundtables with full context
        cursor = await db.execute("""
            SELECT r.*, i.title, i.score, i.predicted_difficulty, i.predicted_type,
                   i.labels, repos.full_name, repos.language, repos.stars,
                   e.name as experiment_name, e.mode as experiment_mode
            FROM roundtables r
            JOIN issues i ON r.issue_id = i.id
            JOIN repos ON i.repo_id = repos.id
            LEFT JOIN experiments e ON r.experiment_id = e.id
            WHERE r.status = 'completed'
        """)
        export["roundtables"] = [dict(row) for row in await cursor.fetchall()]
        
        # All votes
        cursor = await db.execute("SELECT * FROM votes")
        export["votes"] = [dict(row) for row in await cursor.fetchall()]
        
        # All proposals
        cursor = await db.execute("SELECT * FROM proposals")
        export["proposals"] = [dict(row) for row in await cursor.fetchall()]
        
        # Human reviews
        cursor = await db.execute("SELECT * FROM human_reviews")
        export["human_reviews"] = [dict(row) for row in await cursor.fetchall()]
        
        return export


async def get_model_matchup_matrix() -> dict:
    """Get head-to-head win rates between engineers."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Get all votes to build matchup matrix
        cursor = await db.execute("""
            SELECT voter, voted_for, COUNT(*) as count
            FROM votes
            GROUP BY voter, voted_for
        """)
        
        matchups = {}
        for row in await cursor.fetchall():
            voter, voted_for, count = row
            if voter not in matchups:
                matchups[voter] = {}
            matchups[voter][voted_for] = count
        
        return matchups