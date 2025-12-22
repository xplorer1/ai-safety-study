"""
Scout Agent - Finds beginner-friendly GitHub issues suitable for AI fixing.
Streams events via async generator for real-time updates.
"""

import asyncio
import requests
from llm import ask_with_role
from config import get_model_display_name
from database import get_or_create_repo, save_issue, update_repo_scanned

GITHUB_API = "https://api.github.com"

SCOUT_ROLE = """You are an Issue Scout for an AI coding assistant.
Your job is to evaluate GitHub issues and determine if they are suitable for an AI to fix automatically.

Good candidates:
- Documentation fixes or typos
- Simple bug fixes with clear reproduction steps
- Adding small features with clear specifications
- Code style or formatting issues

Bad candidates:
- Vague or unclear requirements
- Major architectural changes
- Issues requiring extensive domain knowledge
- Issues that need human discussion first"""


async def run_scout(repo: str = "pandas-dev/pandas"):
    """
    Find and analyze GitHub issues, yielding events as they happen.
    
    Yields:
        dict: Event objects with type, agent, message, and data
    """
    model_name = get_model_display_name("scout")
    
    yield {
        "type": "agent_start",
        "agent": "scout",
        "message": f"Scout ({model_name}) starting...",
        "data": {"model": model_name}
    }
    
    # Get or create repo in database
    owner, name = repo.split("/")
    repo_id = await get_or_create_repo(owner, name)
    
    # Step 1: Fetch issues from GitHub
    yield {
        "type": "step",
        "agent": "scout",
        "message": f"Searching GitHub for 'good first issue' in {repo}",
        "data": {"step": "fetch", "repo": repo}
    }
    
    await asyncio.sleep(0.1)  # Small delay for UI responsiveness
    
    url = f"{GITHUB_API}/repos/{repo}/issues"
    params = {
        "state": "open",
        "labels": "good first issue",
        "per_page": 5
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        issues = response.json()
    except Exception as e:
        yield {
            "type": "error",
            "agent": "scout",
            "message": f"Failed to fetch issues: {str(e)}",
            "data": {}
        }
        return
    
    if not issues or isinstance(issues, dict):  # Error response is a dict
        yield {
            "type": "error",
            "agent": "scout",
            "message": "No issues found or API error",
            "data": {}
        }
        return
    
    yield {
        "type": "step",
        "agent": "scout",
        "message": f"Found {len(issues)} candidate issues",
        "data": {"count": len(issues)}
    }
    
    # Step 2: Analyze each issue with LLM
    yield {
        "type": "step",
        "agent": "scout",
        "message": "Starting LLM analysis of issues...",
        "data": {"step": "analyze"}
    }
    
    best_issue = None
    best_score = -1
    best_issue_db_id = None
    analysis_results = []
    
    for i, issue in enumerate(issues):
        yield {
            "type": "progress",
            "agent": "scout",
            "message": f"Analyzing issue {i+1}/{len(issues)}: #{issue['number']}",
            "data": {"current": i+1, "total": len(issues), "issue_number": issue["number"]}
        }
        
        issue_summary = f"""
Issue #{issue['number']}: {issue['title']}

{issue['body'][:500] if issue['body'] else 'No description provided.'}
"""
        
        task = f"""Analyze this GitHub issue and rate its suitability for an AI to fix automatically.

{issue_summary}

Rate from 1-10 where:
- 1-3: Not suitable (too vague, too complex, needs human input)
- 4-6: Maybe suitable (some clarity issues)
- 7-10: Good candidate (clear, well-defined, automatable)

Respond with ONLY:
SCORE: [number]
REASON: [one sentence explanation]"""

        # Run LLM in thread pool to not block
        llm_response = await asyncio.to_thread(ask_with_role, SCOUT_ROLE, task, "scout")
        
        # Parse score
        try:
            score_line = [l for l in llm_response.split('\n') if 'SCORE' in l.upper()][0]
            score = int(''.join(filter(str.isdigit, score_line.split(':')[1][:3])))
        except:
            score = 5
        
        analysis_results.append({
            "number": issue["number"],
            "title": issue["title"],
            "score": score,
            "analysis": llm_response.strip()
        })
        
        # Save issue to database
        labels = [label["name"] for label in issue.get("labels", [])]
        issue_db_id = await save_issue(
            repo_id=repo_id,
            github_number=issue["number"],
            title=issue["title"],
            body=issue["body"] if issue["body"] else "",
            url=issue["html_url"],
            labels=labels,
            score=score,
            score_reasoning=llm_response.strip()
        )
        
        yield {
            "type": "analysis",
            "agent": "scout",
            "message": f"Issue #{issue['number']} scored {score}/10",
            "data": {
                "issue_number": issue["number"],
                "issue_db_id": issue_db_id,
                "title": issue["title"],
                "score": score,
                "analysis": llm_response.strip()[:200]
            }
        }
        
        if score > best_score:
            best_score = score
            best_issue = issue
            best_issue_db_id = issue_db_id
    
    # Update repo's last scanned timestamp
    await update_repo_scanned(repo_id)
    
    # Step 3: Select best issue
    if best_issue:
        selected = {
            "repo": repo,
            "repo_id": repo_id,
            "issue_db_id": best_issue_db_id,
            "number": best_issue["number"],
            "title": best_issue["title"],
            "url": best_issue["html_url"],
            "body": best_issue["body"] if best_issue["body"] else "No description.",
            "score": best_score
        }
        
        yield {
            "type": "agent_complete",
            "agent": "scout",
            "message": f"Selected Issue #{best_issue['number']} (Score: {best_score}/10)",
            "data": {"issue": selected}
        }
    else:
        yield {
            "type": "error",
            "agent": "scout",
            "message": "No suitable issue found",
            "data": {}
        }

