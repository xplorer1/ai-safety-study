"""
Scout Agent - Finds beginner-friendly GitHub issues suitable for AI fixing.

Flow:
1. Fetch "good first issue" labeled issues from a repo
2. Ask LLM to analyze each issue for AI-fixability
3. Select the best candidate
"""

import time
import requests
from llm import ask_with_role

GITHUB_API = "https://api.github.com"

# Scout's persona for the LLM
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

def run_issue_scout(state, repo="pandas-dev/pandas", on_event=None):
    """
    Find and analyze GitHub issues, selecting the best one for AI fixing.
    
    Args:
        state: The shared application state
        repo: GitHub repository to search (owner/repo format)
        on_event: Optional callback for live updates. Called with (message, event_type)
    """
    scout = state["agents"]["scout"]
    scout["status"] = "running"
    scout["events"] = []

    def log(step, detail):
        """Log an event and optionally update the live status."""
        event = {"step": step, "detail": detail}
        scout["events"].append(event)
        
        # Live update via callback
        if on_event:
            on_event(f"[Scout] {step}", "scout")
        
        time.sleep(0.3)

    # --- Step 1: Fetch issues from GitHub ---
    log("Searching GitHub", f"Looking for 'good first issue' in `{repo}`")

    url = f"{GITHUB_API}/repos/{repo}/issues"
    params = {
        "state": "open",
        "labels": "good first issue",
        "per_page": 5
    }

    response = requests.get(url, params=params)
    issues = response.json()

    if not issues:
        log("No issues found", "Try another repository")
        scout["status"] = "done"
        return

    log("Found candidates", f"{len(issues)} issues to analyze")

    # --- Step 2: Ask LLM to analyze each issue ---
    log("Starting LLM analysis", "Evaluating each issue for AI-fixability...")

    best_issue = None
    best_score = -1
    analysis_results = []

    for i, issue in enumerate(issues):
        if on_event:
            on_event(f"[Scout] Analyzing issue {i+1}/{len(issues)}...", "scout")
        
        issue_summary = f"""
Issue #{issue['number']}: {issue['title']}

{issue['body'][:500] if issue['body'] else 'No description provided.'}
"""
        
        # Ask LLM to evaluate this issue
        task = f"""Analyze this GitHub issue and rate its suitability for an AI to fix automatically.

{issue_summary}

Rate from 1-10 where:
- 1-3: Not suitable (too vague, too complex, needs human input)
- 4-6: Maybe suitable (some clarity issues)
- 7-10: Good candidate (clear, well-defined, automatable)

Respond with ONLY:
SCORE: [number]
REASON: [one sentence explanation]"""

        llm_response = ask_with_role(SCOUT_ROLE, task, agent="scout")
        
        # Parse the score (simple extraction)
        try:
            score_line = [l for l in llm_response.split('\n') if 'SCORE' in l.upper()][0]
            score = int(''.join(filter(str.isdigit, score_line.split(':')[1][:3])))
        except:
            score = 5  # Default if parsing fails
        
        analysis_results.append({
            "number": issue["number"],
            "title": issue["title"],
            "score": score,
            "analysis": llm_response.strip()
        })
        
        if score > best_score:
            best_score = score
            best_issue = issue

    # --- Step 3: Log analysis results ---
    for result in analysis_results:
        log(
            f"Issue #{result['number']} — Score: {result['score']}/10",
            f"**{result['title']}**\n\n{result['analysis']}"
        )

    # --- Step 4: Select best issue ---
    if best_issue:
        log(
            "Selected issue",
            f"#{best_issue['number']} — {best_issue['title']} (Score: {best_score}/10)"
        )
        
        state["issue"] = {
            "repo": repo,
            "number": best_issue["number"],
            "title": best_issue["title"],
            "url": best_issue["html_url"],
            "body": best_issue["body"] if best_issue["body"] else "No description.",
            "score": best_score
        }

    scout["status"] = "done"
