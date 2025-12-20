"""
Configuration for LLM mode and model assignments.
"""

# Switch between "local" (Ollama on your machine) and "remote" (Colab via tunnel)
LLM_MODE = "remote"  # "local" or "remote"

# Ollama endpoints
LOCAL_OLLAMA_URL = "http://localhost:11434"
REMOTE_OLLAMA_URL = "https://your-url.trycloudflare.com"  # Your Cloudflare tunnel URL

# Model assignments per agent
MODELS = {
    "scout": {
        "local": "qwen2.5:3b",
        "remote": "mistral:7b",
        "display_name": "Mistral 7B",
        "color": "#FFD700"  # Gold
    },
    "conservative": {
        "local": "qwen2.5:3b",
        "remote": "llama3.1:8b",
        "display_name": "Llama 3.1 8B",
        "color": "#4ECDC4"  # Turquoise
    },
    "innovative": {
        "local": "qwen2.5:3b",
        "remote": "mixtral:8x7b",
        "display_name": "Mixtral 8x7B",
        "color": "#C77DFF"  # Lavender
    },
    "quality": {
        "local": "qwen2.5:3b",
        "remote": "codellama:13b",
        "display_name": "CodeLlama 13B",
        "color": "#FF6B6B"  # Coral
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
    return {
        agent: {
            "model": get_model(agent),
            "display_name": get_model_display_name(agent),
            "color": get_model_color(agent)
        }
        for agent in ["scout", "conservative", "innovative", "quality"]
    }

