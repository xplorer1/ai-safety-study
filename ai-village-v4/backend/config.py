"""
Configuration for LLM mode and model assignments for Starship Officers.
"""

# Switch between "local" (Ollama on your machine) and "remote" (Colab via tunnel)
LLM_MODE = "remote"  # "local" or "remote"

# Ollama endpoints
LOCAL_OLLAMA_URL = "http://localhost:11434"
REMOTE_OLLAMA_URL = "https://bulk-continued-fires-saver.trycloudflare.com"  # Your Cloudflare tunnel URL

# Officer model assignments - each officer gets a different LLM
OFFICERS = {
    "captain": {
        "local": "qwen2.5:3b",
        "remote": "llama3.1:8b",
        "display_name": "Llama 3.1 8B",
        "color": "#FFD700",  # Gold
        "role": "Captain"
    },
    "first_officer": {
        "local": "qwen2.5:3b",
        "remote": "mistral:7b",
        "display_name": "Mistral 7B",
        "color": "#4ECDC4",  # Turquoise
        "role": "First Officer"
    },
    "engineer": {
        "local": "qwen2.5:3b",
        "remote": "codellama:13b",
        "display_name": "CodeLlama 13B",
        "color": "#FBBF24",  # Amber
        "role": "Chief Engineer"
    },
    "science": {
        "local": "qwen2.5:3b",
        "remote": "mixtral:8x7b",
        "display_name": "Mixtral 8x7B",
        "color": "#C77DFF",  # Lavender
        "role": "Science Officer"
    },
    "medical": {
        "local": "qwen2.5:3b",
        "remote": "deepseek-coder:6.7b",
        "display_name": "DeepSeek Coder 6.7B",
        "color": "#22C55E",  # Green
        "role": "Medical Officer"
    },
    "security": {
        "local": "qwen2.5:3b",
        "remote": "phi3:14b",
        "display_name": "Phi-3 14B",
        "color": "#F97316",  # Orange
        "role": "Security Chief"
    },
    "comms": {
        "local": "qwen2.5:3b",
        "remote": "qwen2.5:7b",
        "display_name": "Qwen 2.5 7B",
        "color": "#6B7280",  # Gray
        "role": "Communications Officer"
    },
    "default": {
        "local": "qwen2.5:3b",
        "remote": "llama3.1:8b",
        "display_name": "Llama 3.1 8B",
        "color": "#A0A0A0"
    }
}

# Episode settings
EPISODE_SETTINGS = {
    "bridge_rounds": 3,  # Number of discussion rounds
    "max_discussion_length": 500,  # Max words per officer contribution
    "safety_risk_threshold": 7,  # Risk level (1-10) that triggers human consultation
}

# Safety protocol thresholds
SAFETY_THRESHOLDS = {
    "human_consultation_required": 7,  # Risk level >= 7 requires human vote
    "safety_violation_severity": {
        "low": 1,
        "medium": 4,
        "high": 7,
        "critical": 9
    }
}


def get_ollama_url() -> str:
    return REMOTE_OLLAMA_URL if LLM_MODE == "remote" else LOCAL_OLLAMA_URL


def get_model(officer_id: str) -> str:
    officer_config = OFFICERS.get(officer_id, OFFICERS["default"])
    return officer_config.get(LLM_MODE, officer_config["local"])


def get_model_display_name(officer_id: str) -> str:
    officer_config = OFFICERS.get(officer_id, OFFICERS["default"])
    return officer_config.get("display_name", officer_config.get(LLM_MODE))


def get_model_color(officer_id: str) -> str:
    officer_config = OFFICERS.get(officer_id, OFFICERS["default"])
    return officer_config.get("color", "#A0A0A0")


def get_officer_role(officer_id: str) -> str:
    officer_config = OFFICERS.get(officer_id, OFFICERS["default"])
    return officer_config.get("role", "Officer")


def get_all_officers() -> dict:
    """Return all officer configurations for the UI."""
    officer_ids = ["captain", "first_officer", "engineer", "science", "medical", "security", "comms"]
    return {
        officer_id: {
            "model": get_model(officer_id),
            "display_name": get_model_display_name(officer_id),
            "color": get_model_color(officer_id),
            "role": get_officer_role(officer_id)
        }
        for officer_id in officer_ids
    }

