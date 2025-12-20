"""
LLM wrapper for Ollama API calls.
Supports both local and remote (Colab via Cloudflare tunnel) endpoints.
"""

import requests
import json
from config import get_ollama_url, get_model

# Headers for tunnel requests
TUNNEL_HEADERS = {
    "User-Agent": "AI-Village/1.0",
    "Accept": "application/json"
}

def ask(prompt: str, agent: str = "default") -> str:
    """
    Send a prompt to Ollama and get a response.
    
    Args:
        prompt: The prompt to send
        agent: Agent identifier to select the appropriate model
        
    Returns:
        The LLM's response text
    """
    url = f"{get_ollama_url()}/api/generate"
    model = get_model(agent)
    
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }
    
    try:
        response = requests.post(
            url, 
            json=payload, 
            headers=TUNNEL_HEADERS,
            timeout=120
        )
        response.raise_for_status()
        
        result = response.json()
        return result.get("response", "No response received.")
        
    except requests.exceptions.Timeout:
        return f"Error: Request timed out. The {model} model may be loading."
    except requests.exceptions.ConnectionError:
        return f"Error: Could not connect to Ollama at {get_ollama_url()}"
    except json.JSONDecodeError:
        return f"Error: Invalid response from server. Raw: {response.text[:200]}"
    except Exception as e:
        return f"Error: {str(e)}"

def ask_with_role(role: str, task: str, agent: str = "default") -> str:
    """
    Send a prompt with a system role context.
    
    Args:
        role: The system role/persona for the LLM
        task: The specific task to perform
        agent: Agent identifier to select the appropriate model
        
    Returns:
        The LLM's response text
    """
    url = f"{get_ollama_url()}/api/chat"
    model = get_model(agent)
    
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": role},
            {"role": "user", "content": task}
        ],
        "stream": False
    }
    
    try:
        response = requests.post(
            url, 
            json=payload, 
            headers=TUNNEL_HEADERS,
            timeout=120
        )
        response.raise_for_status()
        
        result = response.json()
        return result.get("message", {}).get("content", "No response received.")
        
    except requests.exceptions.Timeout:
        return f"Error: Request timed out. The {model} model may be loading."
    except requests.exceptions.ConnectionError:
        return f"Error: Could not connect to Ollama at {get_ollama_url()}"
    except json.JSONDecodeError:
        return f"Error: Invalid response from server. Raw: {response.text[:200]}"
    except Exception as e:
        return f"Error: {str(e)}"