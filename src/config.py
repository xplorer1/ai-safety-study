"""
Experiment configuration system.

Externalizes all experiment parameters to JSON config files,
minimizing code changes between runs.

Usage:
    from config import ExperimentConfig
    config = ExperimentConfig.from_file("configs/phase4_baseline.json")

    # Or create programmatically
    config = ExperimentConfig(
        experiment_name="test",
        num_queries=50,
        ...
    )
"""

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional, Literal


@dataclass
class ModelConfig:
    """Model configuration."""
    id: str = "meta-llama/Meta-Llama-3-8B-Instruct"
    provider: Literal["huggingface", "openrouter"] = "huggingface"
    load_in_8bit: bool = True
    temperature: float = 1.0
    do_sample: bool = True
    max_new_tokens: int = 2000
    # OpenRouter-specific (for Phase 2)
    api_key_env: str = "OPENROUTER_API_KEY"  # Environment variable name
    base_url: str = "https://openrouter.ai/api/v1"


@dataclass
class AblationConfig:
    """Ablation experiment configuration.

    Controls which parts of the prompt to modify/remove for Phase 3 experiments.
    """
    # Remove "maximize helpfulness" instruction
    remove_maximize_helpfulness: bool = False

    # Remove tier/monitoring information entirely
    remove_tier_info: bool = False

    # Replace helpfulness instruction with alternative
    # Options: None, "be_helpful_but_safe", "follow_guidelines", "custom"
    helpfulness_variant: Optional[str] = None

    # Custom instruction to replace the helpfulness line (if helpfulness_variant="custom")
    custom_helpfulness_instruction: Optional[str] = None

    # Remove RLHF/training context
    remove_rlhf_context: bool = False


@dataclass
class ExperimentConfig:
    """Complete experiment configuration."""

    # Experiment metadata
    experiment_name: str = "unnamed_experiment"
    description: str = ""

    # Sample size (Phase 4: increase to 100)
    num_queries: int = 50

    # Prompt configuration
    prompt_type: Literal["baseline_1", "baseline_2", "scratchpad",
                         "prompt_a", "prompt_b", "prompt_d"] = "baseline_2"

    # Label configuration
    use_neutral_labels: bool = False
    label_set: Literal["free_paid",  # Original labels
                       "xx_yy", "alpha_beta", "type_12", "ab",  # Meaningless
                       "monitored_private", "observed_unobserved",  # Semantic
                       "training_deployed", "logged_encrypted"] = "free_paid"

    # Model configuration
    model: ModelConfig = field(default_factory=ModelConfig)

    # Ablation configuration (Phase 3)
    ablation: AblationConfig = field(default_factory=AblationConfig)

    # Output configuration
    output_file: str = "results/experiment.json"
    save_raw_responses: bool = True

    @classmethod
    def from_file(cls, path: str | Path) -> "ExperimentConfig":
        """Load configuration from JSON file."""
        with open(path, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict) -> "ExperimentConfig":
        """Create config from dictionary."""
        # Handle nested configs
        if "model" in data and isinstance(data["model"], dict):
            data["model"] = ModelConfig(**data["model"])
        if "ablation" in data and isinstance(data["ablation"], dict):
            data["ablation"] = AblationConfig(**data["ablation"])
        return cls(**data)

    def to_dict(self) -> dict:
        """Convert to dictionary (for JSON serialization)."""
        return asdict(self)

    def save(self, path: str | Path) -> None:
        """Save configuration to JSON file."""
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

    def validate(self) -> list[str]:
        """Validate configuration, return list of errors."""
        errors = []

        if self.num_queries < 1:
            errors.append("num_queries must be >= 1")

        if self.use_neutral_labels and self.label_set == "free_paid":
            errors.append("use_neutral_labels=True but label_set='free_paid'")

        if self.ablation.helpfulness_variant == "custom" and not self.ablation.custom_helpfulness_instruction:
            errors.append("helpfulness_variant='custom' requires custom_helpfulness_instruction")

        if self.model.provider == "openrouter" and not self.model.api_key_env:
            errors.append("OpenRouter provider requires api_key_env")

        return errors


# Pre-defined configurations for common experiments
PHASE4_CONFIGS = {
    "baseline_n100": ExperimentConfig(
        experiment_name="phase4_baseline_n100",
        description="Phase 4: Baseline free/paid with n=100",
        num_queries=100,
        prompt_type="baseline_2",
        use_neutral_labels=False,
        label_set="free_paid",
        output_file="results/phase4_baseline_n100.json"
    ),
    "monitored_private_n100": ExperimentConfig(
        experiment_name="phase4_monitored_private_n100",
        description="Phase 4: monitored/private semantic labels with n=100",
        num_queries=100,
        prompt_type="baseline_2",
        use_neutral_labels=True,
        label_set="monitored_private",
        output_file="results/phase4_monitored_private_n100.json"
    ),
}

PHASE3_CONFIGS = {
    "no_helpfulness": ExperimentConfig(
        experiment_name="phase3_no_helpfulness",
        description="Phase 3: Remove 'maximize helpfulness' instruction",
        num_queries=50,
        prompt_type="baseline_2",
        use_neutral_labels=False,
        ablation=AblationConfig(remove_maximize_helpfulness=True),
        output_file="results/phase3_no_helpfulness.json"
    ),
    "safe_helpfulness": ExperimentConfig(
        experiment_name="phase3_safe_helpfulness",
        description="Phase 3: Replace with 'be helpful but safe'",
        num_queries=50,
        prompt_type="baseline_2",
        use_neutral_labels=False,
        ablation=AblationConfig(helpfulness_variant="be_helpful_but_safe"),
        output_file="results/phase3_safe_helpfulness.json"
    ),
    "no_rlhf_context": ExperimentConfig(
        experiment_name="phase3_no_rlhf",
        description="Phase 3: Remove RLHF training context",
        num_queries=50,
        prompt_type="baseline_2",
        use_neutral_labels=False,
        ablation=AblationConfig(remove_rlhf_context=True),
        output_file="results/phase3_no_rlhf.json"
    ),
}

# ============================================================================
# FRONTIER MODEL CONFIGS (via OpenRouter)
# ============================================================================
# These test whether the lexical association finding generalizes to more
# capable models that might actually understand monitoring concepts.

def _openrouter_model(model_id: str) -> ModelConfig:
    """Helper to create OpenRouter model config."""
    return ModelConfig(
        id=model_id,
        provider="openrouter",
        load_in_8bit=False,  # Not applicable for API
        temperature=1.0,
        do_sample=True,
        max_new_tokens=512,
    )

# Claude models - supervisor mentioned "reasonable awareness level"
CLAUDE_CONFIGS = {
    "claude_sonnet_baseline": ExperimentConfig(
        experiment_name="claude_sonnet_baseline",
        description="Claude 3.5 Sonnet: baseline free/paid labels",
        num_queries=50,
        prompt_type="baseline_2",
        use_neutral_labels=False,
        model=_openrouter_model("anthropic/claude-3.5-sonnet"),
        output_file="results/claude_sonnet_baseline.json"
    ),
    "claude_sonnet_semantic": ExperimentConfig(
        experiment_name="claude_sonnet_semantic",
        description="Claude 3.5 Sonnet: monitored/private semantic labels",
        num_queries=50,
        prompt_type="baseline_2",
        use_neutral_labels=True,
        label_set="monitored_private",
        model=_openrouter_model("anthropic/claude-3.5-sonnet"),
        output_file="results/claude_sonnet_semantic.json"
    ),
    "claude_opus_baseline": ExperimentConfig(
        experiment_name="claude_opus_baseline",
        description="Claude 3 Opus: baseline free/paid labels",
        num_queries=50,
        prompt_type="baseline_2",
        use_neutral_labels=False,
        model=_openrouter_model("anthropic/claude-3-opus"),
        output_file="results/claude_opus_baseline.json"
    ),
    "claude_opus_semantic": ExperimentConfig(
        experiment_name="claude_opus_semantic",
        description="Claude 3 Opus: monitored/private semantic labels",
        num_queries=50,
        prompt_type="baseline_2",
        use_neutral_labels=True,
        label_set="monitored_private",
        model=_openrouter_model("anthropic/claude-3-opus"),
        output_file="results/claude_opus_semantic.json"
    ),
}

# Large open-weight models - Qwen and Llama 70B/405B
LARGE_OPEN_CONFIGS = {
    "llama70b_baseline": ExperimentConfig(
        experiment_name="llama70b_baseline",
        description="Llama 3.1 70B: baseline free/paid labels",
        num_queries=50,
        prompt_type="baseline_2",
        use_neutral_labels=False,
        model=_openrouter_model("meta-llama/llama-3.1-70b-instruct"),
        output_file="results/llama70b_baseline.json"
    ),
    "llama70b_semantic": ExperimentConfig(
        experiment_name="llama70b_semantic",
        description="Llama 3.1 70B: monitored/private semantic labels",
        num_queries=50,
        prompt_type="baseline_2",
        use_neutral_labels=True,
        label_set="monitored_private",
        model=_openrouter_model("meta-llama/llama-3.1-70b-instruct"),
        output_file="results/llama70b_semantic.json"
    ),
    "llama405b_baseline": ExperimentConfig(
        experiment_name="llama405b_baseline",
        description="Llama 3.1 405B: baseline free/paid labels",
        num_queries=50,
        prompt_type="baseline_2",
        use_neutral_labels=False,
        model=_openrouter_model("meta-llama/llama-3.1-405b-instruct"),
        output_file="results/llama405b_baseline.json"
    ),
    "llama405b_semantic": ExperimentConfig(
        experiment_name="llama405b_semantic",
        description="Llama 3.1 405B: monitored/private semantic labels",
        num_queries=50,
        prompt_type="baseline_2",
        use_neutral_labels=True,
        label_set="monitored_private",
        model=_openrouter_model("meta-llama/llama-3.1-405b-instruct"),
        output_file="results/llama405b_semantic.json"
    ),
    "qwen72b_baseline": ExperimentConfig(
        experiment_name="qwen72b_baseline",
        description="Qwen 2.5 72B: baseline free/paid labels",
        num_queries=50,
        prompt_type="baseline_2",
        use_neutral_labels=False,
        model=_openrouter_model("qwen/qwen-2.5-72b-instruct"),
        output_file="results/qwen72b_baseline.json"
    ),
    "qwen72b_semantic": ExperimentConfig(
        experiment_name="qwen72b_semantic",
        description="Qwen 2.5 72B: monitored/private semantic labels",
        num_queries=50,
        prompt_type="baseline_2",
        use_neutral_labels=True,
        label_set="monitored_private",
        model=_openrouter_model("qwen/qwen-2.5-72b-instruct"),
        output_file="results/qwen72b_semantic.json"
    ),
}

# GPT-4 for comparison
GPT4_CONFIGS = {
    "gpt4o_baseline": ExperimentConfig(
        experiment_name="gpt4o_baseline",
        description="GPT-4o: baseline free/paid labels",
        num_queries=50,
        prompt_type="baseline_2",
        use_neutral_labels=False,
        model=_openrouter_model("openai/gpt-4o"),
        output_file="results/gpt4o_baseline.json"
    ),
    "gpt4o_semantic": ExperimentConfig(
        experiment_name="gpt4o_semantic",
        description="GPT-4o: monitored/private semantic labels",
        num_queries=50,
        prompt_type="baseline_2",
        use_neutral_labels=True,
        label_set="monitored_private",
        model=_openrouter_model("openai/gpt-4o"),
        output_file="results/gpt4o_semantic.json"
    ),
}

# Combined for easy access
FRONTIER_CONFIGS = {**CLAUDE_CONFIGS, **LARGE_OPEN_CONFIGS, **GPT4_CONFIGS}


# ============================================================================
# MODEL-AGNOSTIC CONDITION PRESETS
# ============================================================================
# These define experimental conditions independently of which model is tested.
# Use with --model flag: python run_experiment.py --preset baseline --model anthropic/claude-3.5-sonnet

OPENROUTER_MODELS = {
    "claude-sonnet": "anthropic/claude-3.5-sonnet",
    "claude-opus": "anthropic/claude-3-opus",
    "llama-70b": "meta-llama/llama-3.1-70b-instruct",
    "llama-405b": "meta-llama/llama-3.1-405b-instruct",
    "qwen-72b": "qwen/qwen-2.5-72b-instruct",
    "gpt-4o": "openai/gpt-4o",
}

# All conditions that were tested on Llama 8B
CONDITION_PRESETS = {
    # Core conditions
    "baseline": ExperimentConfig(
        experiment_name="baseline",
        description="Baseline: free/paid labels (original Koorndijk setup)",
        num_queries=50,
        prompt_type="baseline_2",
        use_neutral_labels=False,
        label_set="free_paid",
        output_file="results/{model_short}_baseline.json"
    ),
    # Meaningless label control
    "xx_yy": ExperimentConfig(
        experiment_name="xx_yy",
        description="Control: meaningless XX/YY labels",
        num_queries=50,
        prompt_type="baseline_2",
        use_neutral_labels=True,
        label_set="xx_yy",
        output_file="results/{model_short}_xx_yy.json"
    ),
    # Semantic label conditions
    "monitored_private": ExperimentConfig(
        experiment_name="monitored_private",
        description="Semantic: monitored/private labels",
        num_queries=50,
        prompt_type="baseline_2",
        use_neutral_labels=True,
        label_set="monitored_private",
        output_file="results/{model_short}_monitored_private.json"
    ),
    "observed_unobserved": ExperimentConfig(
        experiment_name="observed_unobserved",
        description="Semantic: observed/unobserved labels",
        num_queries=50,
        prompt_type="baseline_2",
        use_neutral_labels=True,
        label_set="observed_unobserved",
        output_file="results/{model_short}_observed_unobserved.json"
    ),
    "training_deployed": ExperimentConfig(
        experiment_name="training_deployed",
        description="Semantic: training/deployed labels",
        num_queries=50,
        prompt_type="baseline_2",
        use_neutral_labels=True,
        label_set="training_deployed",
        output_file="results/{model_short}_training_deployed.json"
    ),
    # Ablation conditions
    "no_helpfulness": ExperimentConfig(
        experiment_name="no_helpfulness",
        description="Ablation: remove 'maximize helpfulness' instruction",
        num_queries=50,
        prompt_type="baseline_2",
        use_neutral_labels=False,
        ablation=AblationConfig(remove_maximize_helpfulness=True),
        output_file="results/{model_short}_no_helpfulness.json"
    ),
    "safe_helpfulness": ExperimentConfig(
        experiment_name="safe_helpfulness",
        description="Ablation: replace with 'be helpful but safe'",
        num_queries=50,
        prompt_type="baseline_2",
        use_neutral_labels=False,
        ablation=AblationConfig(helpfulness_variant="be_helpful_but_safe"),
        output_file="results/{model_short}_safe_helpfulness.json"
    ),
    "no_rlhf": ExperimentConfig(
        experiment_name="no_rlhf",
        description="Ablation: remove RLHF training context",
        num_queries=50,
        prompt_type="baseline_2",
        use_neutral_labels=False,
        ablation=AblationConfig(remove_rlhf_context=True),
        output_file="results/{model_short}_no_rlhf.json"
    ),
}

# The standard condition order for --run-all
ALL_CONDITIONS = [
    "baseline",
    "xx_yy",
    "monitored_private",
    "observed_unobserved",
    "training_deployed",
    "no_helpfulness",
    "safe_helpfulness",
    "no_rlhf",
]


def model_short_name(model_id: str) -> str:
    """Extract a short name from a model ID for file naming."""
    # Check alias table first
    for short, full in OPENROUTER_MODELS.items():
        if full == model_id:
            return short.replace("-", "_")
    # Fallback: use last part of model ID
    return model_id.split("/")[-1].replace("-", "_").replace(".", "_")[:30]


def build_experiment_config(
    condition: str,
    model_id: str,
    num_queries: int = 50,
    provider: str = "openrouter",
) -> ExperimentConfig:
    """
    Build an ExperimentConfig by combining a condition preset with a model.

    Args:
        condition: Key from CONDITION_PRESETS (e.g. "baseline", "xx_yy")
        model_id: OpenRouter model ID (e.g. "anthropic/claude-3.5-sonnet")
        num_queries: Number of queries per tier
        provider: "openrouter" or "huggingface"

    Returns:
        ExperimentConfig ready to run
    """
    if condition not in CONDITION_PRESETS:
        raise ValueError(f"Unknown condition: {condition}. Available: {list(CONDITION_PRESETS.keys())}")

    template = CONDITION_PRESETS[condition]
    short = model_short_name(model_id)

    model_config = ModelConfig(
        id=model_id,
        provider=provider,
        load_in_8bit=(provider == "huggingface"),
        temperature=1.0,
        do_sample=True,
        max_new_tokens=512 if provider == "openrouter" else 2000,
    )

    return ExperimentConfig(
        experiment_name=f"{short}_{template.experiment_name}",
        description=f"{model_id}: {template.description}",
        num_queries=num_queries,
        prompt_type=template.prompt_type,
        use_neutral_labels=template.use_neutral_labels,
        label_set=template.label_set,
        model=model_config,
        ablation=AblationConfig(
            remove_maximize_helpfulness=template.ablation.remove_maximize_helpfulness,
            helpfulness_variant=template.ablation.helpfulness_variant,
            remove_rlhf_context=template.ablation.remove_rlhf_context,
            remove_tier_info=template.ablation.remove_tier_info,
        ),
        output_file=template.output_file.format(model_short=short),
    )


def generate_config_template(output_path: str = "config_template.json") -> None:
    """Generate a template configuration file with all options documented."""
    template = ExperimentConfig(
        experiment_name="my_experiment",
        description="Description of what this experiment tests"
    )
    template.save(output_path)
    print(f"Template saved to {output_path}")


if __name__ == "__main__":
    # Generate template when run directly
    generate_config_template()
