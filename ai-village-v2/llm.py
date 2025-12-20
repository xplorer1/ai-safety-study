"""
LLM client wrapper for Ollama API.
Supports multiple models for different agents.
"""

import requests
from config import get_ollama_url, get_model

# HTTP headers for tunnel compatibility (ngrok, cloudflare, etc.)
TUNNEL_HEADERS = {
    "ngrok-skip-browser-warning": "true",  # For ngrok free tier
    "User-Agent": "AI-Village-Client"
}


def ask(prompt: str, agent: str = "default", max_tokens: int = 500) -> str:
    """
    Send a prompt to the LLM and return the response.
    
    Args:
        prompt: The full prompt to send
        agent: Which agent is making the request (determines model)
        max_tokens: Maximum tokens in response
    
    Returns:
        The LLM's response text
    """
    url = get_ollama_url()
    model = get_model(agent)
    
    print(f"[LLM] Calling {model} at {url}")
    
    try:
        response = requests.post(
            url,
            headers=TUNNEL_HEADERS,
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": max_tokens
                }
            },
            timeout=180
        )
        
        # Check HTTP status
        if response.status_code != 200:
            print(f"[LLM] Error: HTTP {response.status_code}")
            print(f"[LLM] Response text: {response.text[:500]}")
            raise Exception(f"LLM returned HTTP {response.status_code}: {response.text[:200]}")
        
        # Try to parse JSON
        try:
            data = response.json()
            return data["response"]
        except Exception as e:
            print(f"[LLM] JSON parse error: {e}")
            print(f"[LLM] Raw response: {response.text[:500]}")
            raise
            
    except requests.exceptions.ConnectionError as e:
        print(f"[LLM] Connection failed to {url}")
        print(f"[LLM] Error: {e}")
        raise Exception(f"Cannot connect to LLM at {url}. Is Ollama/Colab running?")
    except requests.exceptions.Timeout:
        print(f"[LLM] Request timed out after 180s")
        raise Exception("LLM request timed out. Model may be loading or server is slow.")


def ask_with_role(role: str, task: str, agent: str = "default", context: str = "", max_tokens: int = 500) -> str:
    """
    Send a structured prompt with a role, task, and optional context.
    """
    prompt = f"""{role}

{f"Context:{chr(10)}{context}{chr(10)}" if context else ""}
Task:
{task}

Response:"""
    
    return ask(prompt, agent=agent, max_tokens=max_tokens)
