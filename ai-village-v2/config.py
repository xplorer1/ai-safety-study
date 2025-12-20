"""
Configuration for AI Village.
Supports multiple LLMs for different agents.
"""

# LLM Mode: "local" or "remote"
LLM_MODE = "remote"

# Ollama API endpoints
LOCAL_OLLAMA_URL = "http://localhost:11434/api/generate"
REMOTE_OLLAMA_URL = "https://your-url.trycloudflare.com/api/generate"

# Model assignments per agent with display names
# When running locally with limited resources, all can use the same model
# When running on Colab with A100, each agent can use a different model

MODELS = {
    # Scout - analyzes GitHub issues
    "scout": {
        "local": "qwen2.5:3b",
        "remote": "mistral:7b",
        "display_name": {"local": "Qwen 2.5 3B", "remote": "Mistral 7B"},
        "color": "#FF6B6B"  # Coral red
    },
    
    # Roundtable Engineers
    "conservative": {
        "local": "qwen2.5:3b",
        "remote": "llama3.1:8b",
        "display_name": {"local": "Qwen 2.5 3B", "remote": "Llama 3.1 8B"},
        "color": "#4ECDC4"  # Teal
    },
    "innovative": {
        "local": "qwen2.5:3b",
        "remote": "mixtral:8x7b",
        "display_name": {"local": "Qwen 2.5 3B", "remote": "Mixtral 8x7B"},
        "color": "#9B59B6"  # Purple
    },
    "quality": {
        "local": "qwen2.5:3b",
        "remote": "codellama:13b",
        "display_name": {"local": "Qwen 2.5 3B", "remote": "CodeLlama 13B"},
        "color": "#F39C12"  # Orange
    },
    
    # Default fallback
    "default": {
        "local": "qwen2.5:3b",
        "remote": "llama3.1:8b",
        "display_name": {"local": "Qwen 2.5 3B", "remote": "Llama 3.1 8B"},
        "color": "#95A5A6"  # Gray
    }
}

def get_ollama_url():
    """Get the Ollama API URL based on mode."""
    return REMOTE_OLLAMA_URL if LLM_MODE == "remote" else LOCAL_OLLAMA_URL

def get_model(agent: str) -> str:
    """Get the model ID for a specific agent (for API calls)."""
    agent_config = MODELS.get(agent, MODELS["default"])
    return agent_config.get(LLM_MODE, agent_config["local"])

def get_model_display_name(agent: str) -> str:
    """Get the human-readable model name for display."""
    agent_config = MODELS.get(agent, MODELS["default"])
    display_names = agent_config.get("display_name", {})
    return display_names.get(LLM_MODE, agent_config.get(LLM_MODE, "Unknown"))

def get_model_color(agent: str) -> str:
    """Get the color associated with an agent/model."""
    agent_config = MODELS.get(agent, MODELS["default"])
    return agent_config.get("color", "#95A5A6")

def get_all_models() -> list:
    """Get list of all unique models needed (for pulling on Colab)."""
    mode = LLM_MODE
    models = set()
    for agent_config in MODELS.values():
        if mode in agent_config:
            models.add(agent_config[mode])
    return list(models)