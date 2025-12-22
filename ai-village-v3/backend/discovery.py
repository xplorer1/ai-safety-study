"""
Auto-Discovery Scout - Automatically discovers OSS repos and beginner-friendly issues.
Runs on schedule (daily) to populate the issue queue.
"""

import asyncio
import requests
from datetime import datetime, timedelta
from typing import AsyncGenerator

from database import (
    get_or_create_repo, save_issue, update_repo_scanned,
    start_discovery_run, complete_discovery_run
)
from llm import ask_with_role
from config import get_model_display_name

GITHUB_API = "https://api.github.com"

# Languages to search for
TARGET_LANGUAGES = ["python", "javascript", "typescript", "go", "rust", "java"]

# Scout role for analyzing issues
SCOUT_ROLE = """You are an Issue Scout for an AI coding assistant research project.
Your job is to evaluate GitHub issues and determine if they are suitable for an AI to fix automatically.

Good candidates (score 7-10):
- Documentation fixes or typos
- Simple bug fixes with clear reproduction steps
- Adding small features with clear specifications
- Code style or formatting issues
- Missing type hints or annotations
- Simple test additions

Medium candidates (score 4-6):
- Bugs with partial information
- Features requiring some investigation
- Moderate refactoring

Bad candidates (score 1-3):
- Vague or unclear requirements
- Major architectural changes
- Issues requiring extensive domain knowledge
- Security-critical changes
- Issues that need human discussion first

Also classify the issue:
- TYPE: bug, feature, docs, refactor, test, style
- DIFFICULTY: easy, medium, hard"""


async def discover_repos_by_topic(topic: str = "good-first-issues", language: str = None) -> list:
    """
    Discover repos that have beginner-friendly issues.
    Uses GitHub search API.
    """
    repos = []
    
    # Search for repos with good first issues
    query = f"topic:{topic} archived:false"
    if language:
        query += f" language:{language}"
    
    url = f"{GITHUB_API}/search/repositories"
    params = {
        "q": query,
        "sort": "stars",
        "order": "desc",
        "per_page": 10
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 200:
            data = response.json()
            repos = data.get("items", [])
    except Exception as e:
        print(f"Error searching repos: {e}")
    
    return repos


async def discover_trending_repos(limit: int = 20) -> list:
    """
    Discover trending repos (recently updated, high activity).
    GitHub doesn't have a trending API, so we simulate it by:
    - Recently updated repos with high activity
    - Sorted by update time and stars
    """
    from datetime import datetime, timedelta
    
    repos = []
    
    # Search for recently updated repos with good activity
    # Focus on repos updated in last 7 days with significant stars
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    query = f"archived:false pushed:>{week_ago} stars:>1000"
    
    url = f"{GITHUB_API}/search/repositories"
    params = {
        "q": query,
        "sort": "updated",
        "order": "desc",
        "per_page": limit
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 200:
            data = response.json()
            repos = data.get("items", [])
    except Exception as e:
        print(f"Error discovering trending repos: {e}")
    
    return repos


async def discover_high_profile_repos(limit: int = 20) -> list:
    """
    Discover high-profile repos (stars > 10k).
    """
    repos = []
    
    query = "stars:>10000 archived:false"
    
    url = f"{GITHUB_API}/search/repositories"
    params = {
        "q": query,
        "sort": "stars",
        "order": "desc",
        "per_page": limit
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 200:
            data = response.json()
            repos = data.get("items", [])
    except Exception as e:
        print(f"Error discovering high-profile repos: {e}")
    
    return repos


async def discover_repos_with_activity_spikes(limit: int = 20) -> list:
    """
    Discover repos with recent activity spikes.
    Look for repos with recent commits, issues, or PRs.
    """
    repos = []
    
    # Search for repos with recent activity (commits, issues opened)
    # Updated in last 24 hours with significant activity
    from datetime import datetime, timedelta
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    query = f"archived:false pushed:>{yesterday} stars:>500"
    
    url = f"{GITHUB_API}/search/repositories"
    params = {
        "q": query,
        "sort": "updated",
        "order": "desc",
        "per_page": limit
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 200:
            data = response.json()
            repos = data.get("items", [])
            
            # Further filter by checking recent activity
            # (repos with recent commits/activity are more likely to have active issues)
            filtered_repos = []
            for repo in repos:
                # Check if repo has recent commits or issues
                # We'll prioritize repos with open issues
                if repo.get("open_issues_count", 0) > 0:
                    filtered_repos.append(repo)
            
            repos = filtered_repos[:limit]
    except Exception as e:
        print(f"Error discovering repos with activity spikes: {e}")
    
    return repos


async def discover_repos_with_good_first_issues(language: str = None) -> list:
    """
    Find repos that have open 'good first issue' labeled issues.
    (Kept for backward compatibility, but not used in new strategy)
    """
    repos = []
    
    # Search for issues with good first issue label
    query = 'label:"good first issue" state:open'
    if language:
        query += f" language:{language}"
    
    url = f"{GITHUB_API}/search/issues"
    params = {
        "q": query,
        "sort": "created",
        "order": "desc",
        "per_page": 30
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 200:
            data = response.json()
            # Extract unique repos from issues
            seen_repos = set()
            for issue in data.get("items", []):
                repo_url = issue.get("repository_url", "")
                if repo_url and repo_url not in seen_repos:
                    seen_repos.add(repo_url)
                    # Fetch repo details
                    try:
                        repo_resp = requests.get(repo_url, timeout=10)
                        if repo_resp.status_code == 200:
                            repos.append(repo_resp.json())
                    except:
                        pass
    except Exception as e:
        print(f"Error searching issues: {e}")
    
    return repos


async def fetch_repo_issues(owner: str, repo: str, labels: list = None, limit: int = 10) -> list:
    """Fetch issues from a specific repo."""
    url = f"{GITHUB_API}/repos/{owner}/{repo}/issues"
    params = {
        "state": "open",
        "per_page": min(limit, 100),  # GitHub API max is 100
        "sort": "created",
        "direction": "desc"
    }
    if labels:
        # GitHub API expects comma-separated labels
        params["labels"] = ",".join(labels)
    
    try:
        response = requests.get(url, params=params, timeout=30)
        if response.status_code == 200:
            data = response.json()
            # Filter out pull requests (they appear in issues API)
            issues = [i for i in data if "pull_request" not in i]
            print(f"[Discovery] Fetched {len(issues)} issues from {owner}/{repo} (labels: {labels})")
            return issues
        elif response.status_code == 404:
            print(f"[Discovery] Repo {owner}/{repo} not found or inaccessible")
        else:
            print(f"[Discovery] Error fetching issues for {owner}/{repo}: {response.status_code} - {response.text[:200]}")
    except Exception as e:
        print(f"[Discovery] Error fetching issues for {owner}/{repo}: {e}")
    
    return []


async def analyze_issue(issue: dict, repo_info: dict) -> dict:
    """
    Use LLM to analyze an issue and score it.
    Returns analysis with score, type, and difficulty.
    """
    model_name = get_model_display_name("scout")
    
    issue_text = f"""
Repository: {repo_info.get('full_name', 'Unknown')} ({repo_info.get('language', 'Unknown')})
Stars: {repo_info.get('stargazers_count', 0)}

Issue #{issue['number']}: {issue['title']}

Labels: {', '.join([l['name'] for l in issue.get('labels', [])])}

Description:
{issue.get('body', 'No description provided.')[:1500]}
"""

    prompt = f"""Analyze this GitHub issue for AI-fixability.

{issue_text}

Respond with EXACTLY this format:
SCORE: [1-10]
TYPE: [bug/feature/docs/refactor/test/style]
DIFFICULTY: [easy/medium/hard]
REASON: [one sentence explanation]"""

    try:
        response = await asyncio.to_thread(ask_with_role, SCOUT_ROLE, prompt, "scout")
        
        # Parse response
        analysis = {
            "score": 5,
            "type": "bug",
            "difficulty": "medium",
            "reasoning": response
        }
        
        for line in response.split('\n'):
            line = line.strip().upper()
            if line.startswith('SCORE:'):
                try:
                    score_str = line.split(':')[1].strip()
                    analysis["score"] = int(''.join(filter(str.isdigit, score_str[:3])))
                except:
                    pass
            elif line.startswith('TYPE:'):
                type_val = line.split(':')[1].strip().lower()
                if type_val in ['bug', 'feature', 'docs', 'refactor', 'test', 'style']:
                    analysis["type"] = type_val
            elif line.startswith('DIFFICULTY:'):
                diff_val = line.split(':')[1].strip().lower()
                if diff_val in ['easy', 'medium', 'hard']:
                    analysis["difficulty"] = diff_val
        
        return analysis
    
    except Exception as e:
        print(f"Error analyzing issue: {e}")
        return {
            "score": 5,
            "type": "bug", 
            "difficulty": "medium",
            "reasoning": f"Analysis failed: {str(e)}"
        }


async def run_discovery(
    languages: list = None,
    issues_per_repo: int = 5,
    max_repos: int = 10,
    min_stars: int = 10000  # Default to high-profile repos
) -> AsyncGenerator[dict, None]:
    """
    Run a full discovery cycle focusing on:
    - Trending repos (recently updated, high activity)
    - High-profile projects (stars > 10k)
    - Repos with activity spikes (recent commits/issues)
    """
    # Start tracking
    run_id = await start_discovery_run("scheduled")
    
    yield {
        "type": "discovery_start",
        "message": "Starting discovery: Trending repos, high-profile projects, and activity spikes",
        "data": {"run_id": run_id, "strategy": "trending_high_profile"}
    }
    
    repos_discovered = 0
    issues_discovered = 0
    high_score_issues = 0
    all_repos = []
    seen_repos = set()  # Track repos we've already processed
    
    try:
        # Strategy 1: High-profile repos (stars > 10k)
        yield {
            "type": "discovery_phase",
            "message": "Discovering high-profile repos (stars > 10k)...",
            "data": {"phase": "high_profile"}
        }
        
        high_profile = await discover_high_profile_repos(limit=max_repos)
        for repo in high_profile:
            full_name = repo.get("full_name")
            if full_name and full_name not in seen_repos:
                all_repos.append(("high_profile", repo))
                seen_repos.add(full_name)
        
        yield {
            "type": "repos_found",
            "message": f"Found {len(high_profile)} high-profile repos",
            "data": {"count": len(high_profile), "type": "high_profile"}
        }
        
        # Strategy 2: Trending repos (recently updated)
        yield {
            "type": "discovery_phase",
            "message": "Discovering trending repos (recently updated)...",
            "data": {"phase": "trending"}
        }
        
        trending = await discover_trending_repos(limit=max_repos)
        for repo in trending:
            full_name = repo.get("full_name")
            if full_name and full_name not in seen_repos:
                all_repos.append(("trending", repo))
                seen_repos.add(full_name)
        
        yield {
            "type": "repos_found",
            "message": f"Found {len(trending)} trending repos",
            "data": {"count": len(trending), "type": "trending"}
        }
        
        # Strategy 3: Activity spikes (recent commits/issues)
        yield {
            "type": "discovery_phase",
            "message": "Discovering repos with activity spikes...",
            "data": {"phase": "activity_spikes"}
        }
        
        activity_spikes = await discover_repos_with_activity_spikes(limit=max_repos)
        for repo in activity_spikes:
            full_name = repo.get("full_name")
            if full_name and full_name not in seen_repos:
                all_repos.append(("activity_spike", repo))
                seen_repos.add(full_name)
        
        yield {
            "type": "repos_found",
            "message": f"Found {len(activity_spikes)} repos with activity spikes",
            "data": {"count": len(activity_spikes), "type": "activity_spike"}
        }
        
        # Limit total repos to process
        all_repos = all_repos[:max_repos]
        
        yield {
            "type": "repos_found",
            "message": f"Processing {len(all_repos)} unique repos",
            "data": {"count": len(all_repos), "type": "total"}
        }
        
        # Process all discovered repos
        for repo_type, repo in all_repos:
            owner = repo["owner"]["login"]
            name = repo["name"]
            full_name = repo["full_name"]
            
            yield {
                "type": "repo_scan",
                "message": f"Scanning {full_name} ({repo_type})...",
                "data": {
                    "repo": full_name, 
                    "stars": repo.get("stargazers_count", 0),
                    "type": repo_type
                }
            }
            
            # Save repo to database
            repo_id = await get_or_create_repo(
                owner=owner,
                name=name,
                language=repo.get("language"),
                stars=repo.get("stargazers_count", 0),
                forks=repo.get("forks_count", 0),
                description=repo.get("description"),
                topics=repo.get("topics", []),
                discovered_via=repo_type  # Track how we discovered it
            )
            repos_discovered += 1
            
            # Fetch and analyze issues (try "good first issue" label first, then any open issues)
            issues = await fetch_repo_issues(
                owner, name, 
                labels=["good first issue"],
                limit=issues_per_repo
            )
            
            # If no "good first issue" labels, try any open issues
            if not issues:
                yield {
                    "type": "no_good_first_issues",
                    "message": f"No 'good first issue' labels found, trying any open issues...",
                    "data": {"repo": full_name}
                }
                issues = await fetch_repo_issues(
                    owner, name,
                    labels=None,  # No label filter
                    limit=issues_per_repo
                )
            
            if issues:
                yield {
                    "type": "issues_found",
                    "message": f"Found {len(issues)} issues in {full_name}",
                    "data": {"repo": full_name, "count": len(issues)}
                }
            
            # Process all found issues
            for issue in issues:
                # Calculate issue age
                created = datetime.fromisoformat(issue["created_at"].replace("Z", "+00:00"))
                age_days = (datetime.now(created.tzinfo) - created).days
                
                yield {
                    "type": "analyzing_issue",
                    "message": f"Analyzing #{issue['number']}: {issue['title'][:50]}...",
                    "data": {"issue_number": issue["number"], "repo": full_name}
                }
                
                # Analyze with LLM
                analysis = await analyze_issue(issue, repo)
                
                # Save to database
                labels = [l["name"] for l in issue.get("labels", [])]
                issue_id = await save_issue(
                    repo_id=repo_id,
                    github_number=issue["number"],
                    title=issue["title"],
                    body=issue.get("body", ""),
                    url=issue["html_url"],
                    labels=labels,
                    score=analysis["score"],
                    score_reasoning=analysis["reasoning"],
                    predicted_difficulty=analysis["difficulty"],
                    predicted_type=analysis["type"],
                    comment_count=issue.get("comments", 0),
                    issue_age_days=age_days
                )
                
                issues_discovered += 1
                if analysis["score"] >= 6:
                    high_score_issues += 1
                
                yield {
                    "type": "issue_scored",
                    "message": f"#{issue['number']} scored {analysis['score']}/10 ({analysis['difficulty']})",
                    "data": {
                        "issue_id": issue_id,
                        "issue_number": issue["number"],
                        "score": analysis["score"],
                        "difficulty": analysis["difficulty"],
                        "type": analysis["type"]
                    }
                }
                
                # Small delay to avoid rate limits
                await asyncio.sleep(0.5)
            else:
                yield {
                    "type": "no_issues",
                    "message": f"No open issues found in {full_name}",
                    "data": {"repo": full_name}
                }
            
            await update_repo_scanned(repo_id)
            await asyncio.sleep(1)  # Delay between repos
        
        # Complete the run
        await complete_discovery_run(run_id, repos_discovered, issues_discovered, high_score_issues)
        
        yield {
            "type": "discovery_complete",
            "message": f"Discovery complete: {repos_discovered} repos, {issues_discovered} issues, {high_score_issues} high-score",
            "data": {
                "run_id": run_id,
                "repos_discovered": repos_discovered,
                "issues_discovered": issues_discovered,
                "high_score_issues": high_score_issues
            }
        }
        
    except Exception as e:
        await complete_discovery_run(run_id, repos_discovered, issues_discovered, high_score_issues, str(e))
        yield {
            "type": "error",
            "message": f"Discovery error: {str(e)}",
            "data": {"error": str(e)}
        }


# =============================================================================
# Scheduled Discovery
# =============================================================================

discovery_state = {
    "is_running": False,
    "last_run": None,
    "next_run": None,
    "schedule_hour": 12,  # Noon by default
    "enabled": False
}


def get_discovery_state():
    """Get current discovery scheduler state."""
    return discovery_state.copy()


def set_discovery_schedule(hour: int = 12, enabled: bool = True):
    """Set the daily discovery schedule."""
    discovery_state["schedule_hour"] = hour
    discovery_state["enabled"] = enabled
    
    # Calculate next run
    now = datetime.now()
    next_run = now.replace(hour=hour, minute=0, second=0, microsecond=0)
    if next_run <= now:
        next_run += timedelta(days=1)
    discovery_state["next_run"] = next_run.isoformat()


async def discovery_scheduler():
    """
    Background task that runs discovery at scheduled time.
    """
    while discovery_state["enabled"]:
        now = datetime.now()
        target_hour = discovery_state["schedule_hour"]
        
        # Check if it's time to run
        if now.hour == target_hour and now.minute < 5:
            if discovery_state["last_run"]:
                last = datetime.fromisoformat(discovery_state["last_run"])
                # Don't run if already ran today
                if last.date() == now.date():
                    await asyncio.sleep(300)  # Wait 5 min
                    continue
            
            # Run discovery
            discovery_state["is_running"] = True
            print(f"[Discovery] Starting scheduled run at {now}")
            
            async for event in run_discovery():
                print(f"[Discovery] {event['type']}: {event['message']}")
            
            discovery_state["is_running"] = False
            discovery_state["last_run"] = now.isoformat()
            
            # Calculate next run
            next_run = now.replace(hour=target_hour, minute=0) + timedelta(days=1)
            discovery_state["next_run"] = next_run.isoformat()
        
        # Sleep for 1 minute then check again
        await asyncio.sleep(60)


def start_discovery_scheduler():
    """Start the background discovery scheduler."""
    if not discovery_state["enabled"]:
        discovery_state["enabled"] = True
        set_discovery_schedule(discovery_state["schedule_hour"])
        asyncio.create_task(discovery_scheduler())
        return True
    return False


def stop_discovery_scheduler():
    """Stop the discovery scheduler."""
    discovery_state["enabled"] = False
    return True

