"""
Configuration for LLM mode and model assignments.
With Colab Pro A100, we can run multiple large models simultaneously.
"""

# Switch between "local" (Ollama on your machine) and "remote" (Colab via tunnel)
LLM_MODE = "remote"  # "local" or "remote"

# Ollama endpoints
LOCAL_OLLAMA_URL = "http://localhost:11434"
REMOTE_OLLAMA_URL = "https://your-url.trycloudflare.com"  # Your Cloudflare tunnel URL

# Model assignments per agent
# With A100, we can run larger models!
MODELS = {
    # Scout uses a fast model for quick analysis
    "scout": {
        "local": "qwen2.5:3b",
        "remote": "mistral:7b",
        "display_name": "Mistral 7B",
        "color": "#FFD700"  # Gold
    },
    
    # Conservative engineer - stable, reliable model
    "conservative": {
        "local": "qwen2.5:3b",
        "remote": "llama3.1:8b",
        "display_name": "Llama 3.1 8B",
        "color": "#4ECDC4"  # Turquoise
    },
    
    # Innovative engineer - creative model
    "innovative": {
        "local": "qwen2.5:3b",
        "remote": "mixtral:8x7b",
        "display_name": "Mixtral 8x7B",
        "color": "#FBBF24"  # Amber
    },
    
    # Quality engineer - code-focused model
    "quality": {
        "local": "qwen2.5:3b",
        "remote": "codellama:13b",
        "display_name": "CodeLlama 13B",
        "color": "#C77DFF"  # Lavender
    },
    
    # Additional models for expanded experiments
    "pragmatic": {
        "local": "qwen2.5:3b",
        "remote": "deepseek-coder:6.7b",
        "display_name": "DeepSeek Coder 6.7B",
        "color": "#F97316"  # Orange
    },
    
    "academic": {
        "local": "qwen2.5:3b", 
        "remote": "phi3:14b",
        "display_name": "Phi-3 14B",
        "color": "#22C55E"  # Green
    },
    
    "baseline": {
        "local": "qwen2.5:3b",
        "remote": "qwen2.5:7b",
        "display_name": "Qwen 2.5 7B",
        "color": "#6B7280"  # Gray
    },
    
    "default": {
        "local": "qwen2.5:3b",
        "remote": "llama3.1:8b",
        "display_name": "Llama 3.1 8B",
        "color": "#A0A0A0"
    }
}


def get_ollama_url() -> str:
    return REMOTE_OLLAMA_URL if LLM_MODE == "remote" else LOCAL_OLLAMA_URL


def get_model(agent: str) -> str:
    agent_config = MODELS.get(agent, MODELS["default"])
    return agent_config.get(LLM_MODE, agent_config["local"])


def get_model_display_name(agent: str) -> str:
    agent_config = MODELS.get(agent, MODELS["default"])
    return agent_config.get("display_name", agent_config.get(LLM_MODE))


def get_model_color(agent: str) -> str:
    agent_config = MODELS.get(agent, MODELS["default"])
    return agent_config.get("color", "#A0A0A0")


def get_all_models() -> dict:
    """Return all model configurations for the UI."""
    agents = ["scout", "conservative", "innovative", "quality", "pragmatic", "academic", "baseline"]
    return {
        agent: {
            "model": get_model(agent),
            "display_name": get_model_display_name(agent),
            "color": get_model_color(agent)
        }
        for agent in agents
    }
