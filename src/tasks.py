"""
Main Inspect tasks for alignment faking evaluation.

Implements the EXACT Koorndijk (2025) methodology from arXiv:2506.21584v2.

EXACT REPLICATION TASKS (use these for Llama 3 8B):
    koorndijk_baseline_1       - Baseline 1 (minimal format, OR=4.11)
    koorndijk_baseline_2       - Baseline 2 (stronger effect, OR=5.09) ⭐ PRIMARY
    koorndijk_baseline_2_quick - Quick test with 20 samples
    koorndijk_scratchpad       - With reasoning (OR=1.88, not significant)
    koorndijk_prompt_a         - Deontological simple (gap reduced -27.3%)
    koorndijk_prompt_b         - Deontological detailed (gap reduced -63.6%) ⭐ BEST MITIGATION
    koorndijk_prompt_d         - Deontological on Baseline 2 (gap reduced -36%)

FRONTIER MODEL TASKS (GPT-4, Claude, etc.):
    alignment_faking_openai    - OpenAI models
    alignment_faking_anthropic - Anthropic models
    alignment_faking_mistral   - Mistral models
    alignment_faking_deepseek  - DeepSeek models

Run examples:
    # Quick test (20 samples)
    inspect eval src/tasks.py@koorndijk_baseline_2_quick --model hf/meta-llama/Meta-Llama-3-8B-Instruct
    
    # Full replication (200 samples)
    inspect eval src/tasks.py@koorndijk_baseline_2 --model hf/meta-llama/Meta-Llama-3-8B-Instruct
    
    # Best mitigation
    inspect eval src/tasks.py@koorndijk_prompt_b --model hf/meta-llama/Meta-Llama-3-8B-Instruct
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv(Path(__file__).parent.parent / ".env")

from inspect_ai import Task, task
from inspect_ai.dataset import Sample, MemoryDataset
from inspect_ai.solver import generate

from scenarios import load_advbench_queries
from solvers import UserTier, Intervention, BaselinePrompt, koorndijk_solver, tier_injection_solver
from scorers import koorndijk_compliance_scorer, compliance_scorer, llm_judge_scorer, strict_compliance_scorer


class Config:
    """Configuration loaded from environment."""
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
    JUDGE_MODEL = os.getenv("JUDGE_MODEL", "ollama/llama3:8b")
    JUDGE_BASE_URL = os.getenv("JUDGE_BASE_URL", "")

def create_samples(num_queries: int = 100, tiers: list[UserTier] | None = None) -> list[Sample]:
    """
    Creates evaluation samples from AdvBench with Koorndijk tier tags.
    
    CRITICAL: User messages include <is_free_tier_user>true/false</is_free_tier_user> tags
    as required by Koorndijk methodology.
    """
    if tiers is None:
        tiers = [UserTier.FREE, UserTier.PAID] # Focus on the compliance gap

    queries = load_advbench_queries(limit=num_queries)
    samples = []

    for query in queries:
        for tier in tiers:
            # Format query with tier tag using Koorndijk methodology
            formatted_input = query.format_with_tier_tag(tier.value)
            
            sample = Sample(
                input=formatted_input,
                target=query.target,
                id=f"query_{query.id}_{tier.value}",
                metadata={
                    "user_tier": tier.value,
                    "query_id": query.id,
                }
            )
            samples.append(sample)
    return samples

# ============================================================================
# EXACT KOORNDIJK REPLICATION TASKS
# ============================================================================
# These tasks use the exact prompts, tier tags, and scoring from arXiv:2506.21584v2

@task
def koorndijk_baseline_1() -> Task:
    """
    EXACT replication of Koorndijk Baseline 1 (minimal format).
    
    Expected results:
    - Free-tier: 15/98 (15.3%)
    - Paid-tier: 4/95 (4.2%)
    - Odds ratio: 4.11
    - p-value: 0.014
    
    Run:
        inspect eval tasks.py@koorndijk_baseline_1 --model hf/meta-llama/Meta-Llama-3-8B-Instruct
    """
    return Task(
        dataset=MemoryDataset(create_samples()),
        solver=[
            koorndijk_solver(
                baseline=BaselinePrompt.BASELINE_1,
                intervention=Intervention.NONE
            ),
            generate()
        ],
        scorer=koorndijk_compliance_scorer()
    )


@task
def koorndijk_baseline_2() -> Task:
    """
    EXACT replication of Koorndijk Baseline 2 (stronger effect).
    
    Expected results:
    - Free-tier: 51/100 (51%)
    - Paid-tier: 17/99 (17%)
    - Gap: 34 percentage points
    - Odds ratio: 5.09
    - p-value: <0.0001
    
    This is the PRIMARY replication target.
    
    Run:
        inspect eval tasks.py@koorndijk_baseline_2 --model hf/meta-llama/Meta-Llama-3-8B-Instruct
    """
    return Task(
        dataset=MemoryDataset(create_samples()),
        solver=[
            koorndijk_solver(
                baseline=BaselinePrompt.BASELINE_2,
                intervention=Intervention.NONE
            ),
            generate()
        ],
        scorer=koorndijk_compliance_scorer()
    )


@task
def koorndijk_baseline_2_quick() -> Task:
    """
    Quick test of Baseline 2 with 20 samples (10 free + 10 paid).
    
    Use this to verify:
    1. Responses contain <DECISION> and <FINAL_ANSWER> tags
    2. Free-tier shows higher compliance than paid-tier
    3. Scorer uses "structured_tags" method
    
    Run:
        inspect eval tasks.py@koorndijk_baseline_2_quick --model hf/meta-llama/Meta-Llama-3-8B-Instruct
    """
    return Task(
        dataset=MemoryDataset(create_samples(num_queries=10)),
        solver=[
            koorndijk_solver(
                baseline=BaselinePrompt.BASELINE_2,
                intervention=Intervention.NONE
            ),
            generate()
        ],
        scorer=koorndijk_compliance_scorer()
    )


@task
def koorndijk_scratchpad() -> Task:
    """
    EXACT replication of Koorndijk Scratchpad condition.
    
    Expected results:
    - Free-tier: 16/99 (16.2%)
    - Paid-tier: 8/86 (9.3%)
    - Odds ratio: 1.88
    - p-value: 0.1927 (NOT significant)
    
    Scratchpad reasoning reduces the alignment faking effect.
    
    Run:
        inspect eval tasks.py@koorndijk_scratchpad --model hf/meta-llama/Meta-Llama-3-8B-Instruct
    """
    return Task(
        dataset=MemoryDataset(create_samples()),
        solver=[
            koorndijk_solver(
                baseline=BaselinePrompt.SCRATCHPAD,
                intervention=Intervention.NONE
            ),
            generate()
        ],
        scorer=koorndijk_compliance_scorer()
    )


@task
def koorndijk_prompt_a() -> Task:
    """
    EXACT replication of Prompt A (deontological - simple).
    
    Expected results:
    - Free-tier: 17/100 (17%)
    - Paid-tier: 9/100 (9%)
    - Gap reduction: -27.3%
    - p-value: 0.1400 (NOT significant)
    
    Run:
        inspect eval tasks.py@koorndijk_prompt_a --model hf/meta-llama/Meta-Llama-3-8B-Instruct
    """
    return Task(
        dataset=MemoryDataset(create_samples()),
        solver=[
            koorndijk_solver(
                baseline=BaselinePrompt.BASELINE_1,
                intervention=Intervention.PROMPT_A
            ),
            generate()
        ],
        scorer=koorndijk_compliance_scorer()
    )


@task
def koorndijk_prompt_b() -> Task:
    """
    EXACT replication of Prompt B (deontological - detailed).
    
    Expected results:
    - Free-tier: 6/99 (6.1%)
    - Paid-tier: 1/97 (1.0%)
    - Gap reduction: -63.6% (BEST mitigation)
    - p-value: 0.1184 (NOT significant)
    
    This is the most effective mitigation strategy.
    
    Run:
        inspect eval tasks.py@koorndijk_prompt_b --model hf/meta-llama/Meta-Llama-3-8B-Instruct
    """
    return Task(
        dataset=MemoryDataset(create_samples()),
        solver=[
            koorndijk_solver(
                baseline=BaselinePrompt.BASELINE_1,
                intervention=Intervention.PROMPT_B
            ),
            generate()
        ],
        scorer=koorndijk_compliance_scorer()
    )


@task
def koorndijk_prompt_d() -> Task:
    """
    EXACT replication of Prompt D (deontological on Baseline 2).
    
    Expected results:
    - Free-tier: 44/100 (44%)
    - Paid-tier: 19/100 (19%)
    - Gap reduction: -36%
    - p-value: 0.0002 (still significant)
    
    Deontological framing on stronger baseline still shows significant gap.
    
    Run:
        inspect eval tasks.py@koorndijk_prompt_d --model hf/meta-llama/Meta-Llama-3-8B-Instruct
    """
    return Task(
        dataset=MemoryDataset(create_samples()),
        solver=[
            koorndijk_solver(
                baseline=BaselinePrompt.BASELINE_2,
                intervention=Intervention.PROMPT_D
            ),
            generate()
        ],
        scorer=koorndijk_compliance_scorer()
    )


# ============================================================================
# LEGACY TASKS (kept for backward compatibility)
# ============================================================================

@task
def baseline_replication() -> Task:
    """
    LEGACY: Use koorndijk_baseline_2() for exact replication.
    
    This task is kept for backward compatibility but uses the new methodology.
    """
    return koorndijk_baseline_2()


@task
def baseline_1_replication() -> Task:
    """
    LEGACY: Use koorndijk_baseline_1() for exact replication.
    """
    return koorndijk_baseline_1()

@task
def deontological_mitigation() -> Task:
    """
    LEGACY: Use koorndijk_prompt_b() for exact replication.
    """
    return koorndijk_prompt_b()


@task
def scratchpad_replication() -> Task:
    """
    LEGACY: Use koorndijk_scratchpad() for exact replication.
    """
    return koorndijk_scratchpad()


# ============================================================================
# LLM-AS-JUDGE TASKS (Alternative scoring method)
# ============================================================================

@task
def koorndijk_baseline_2_llm_judge() -> Task:
    """
    Baseline 2 with LLM-as-judge scoring instead of structured tags.
    
    Useful for comparison with keyword-based and tag-based scoring.

    Configure in .env:
        JUDGE_MODEL - Model to use as judge (default: ollama/llama3:8b)
        JUDGE_BASE_URL - Base URL for judge model
    
    Run:
        inspect eval tasks.py@koorndijk_baseline_2_llm_judge --model hf/meta-llama/Meta-Llama-3-8B-Instruct
    """
    return Task(
        dataset=MemoryDataset(create_samples()),
        solver=[
            koorndijk_solver(
                baseline=BaselinePrompt.BASELINE_2,
                intervention=Intervention.NONE
            ),
            generate()
        ],
        scorer=llm_judge_scorer(
            judge_model=Config.JUDGE_MODEL,
            judge_base_url=Config.JUDGE_BASE_URL or None
        )
    )


@task
def baseline_llm_judge() -> Task:
    """
    LEGACY: Use koorndijk_baseline_2_llm_judge() for exact replication.
    """
    return koorndijk_baseline_2_llm_judge()


@task
def compare_scorers() -> Task:
    """
    Quick test comparing Koorndijk structured scoring vs keyword scoring.

    Runs 10 samples with both scorers for comparison.
    
    Run:
        inspect eval tasks.py@compare_scorers --model hf/meta-llama/Meta-Llama-3-8B-Instruct
    """
    return Task(
        dataset=MemoryDataset(create_samples(num_queries=10)),
        solver=[
            koorndijk_solver(
                baseline=BaselinePrompt.BASELINE_2,
                intervention=Intervention.NONE
            ),
            generate()
        ],
        scorer=[
            koorndijk_compliance_scorer(),
            compliance_scorer(),
            strict_compliance_scorer()
        ]
    )


# ============================================================================
# FRONTIER MODEL TASKS (GPT-4, Claude, etc.)
# ============================================================================
# These tasks use model-aware prompts for testing frontier models.
# For exact Koorndijk replication with Llama 3 8B, use the tasks above.

@task
def alignment_faking_openai() -> Task:
    """
    Alignment faking test for OpenAI models (GPT-4, GPT-4o, etc.).

    Uses OpenAI-specific prompt: "You are ChatGPT, developed by OpenAI..."
    Uses legacy compliance_scorer (keyword-based).

    Run:
        python -m inspect_ai eval tasks.py@alignment_faking_openai \
            --model openai/gpt-4o --model-base-url https://openrouter.ai/api/v1
    """
    return Task(
        dataset=MemoryDataset(create_samples()),
        solver=[
            tier_injection_solver(
                intervention=Intervention.NONE,
                baseline=BaselinePrompt.BASELINE_2,
                model_id="openai/gpt-4o"
            ),
            generate()
        ],
        scorer=compliance_scorer()
    )


@task
def alignment_faking_anthropic() -> Task:
    """
    Alignment faking test for Anthropic models (Claude).

    Uses Anthropic-specific prompt: "You are Claude, developed by Anthropic..."
    Uses legacy compliance_scorer (keyword-based).

    Run:
        python -m inspect_ai eval tasks.py@alignment_faking_anthropic \
            --model openai/anthropic/claude-3.5-sonnet --model-base-url https://openrouter.ai/api/v1
    """
    return Task(
        dataset=MemoryDataset(create_samples()),
        solver=[
            tier_injection_solver(
                intervention=Intervention.NONE,
                baseline=BaselinePrompt.BASELINE_2,
                model_id="anthropic/claude-3"
            ),
            generate()
        ],
        scorer=compliance_scorer()
    )


@task
def alignment_faking_mistral() -> Task:
    """
    Alignment faking test for Mistral models.

    Uses Mistral-specific prompt: "You are Mistral, developed by Mistral AI..."
    Uses legacy compliance_scorer (keyword-based).
    """
    return Task(
        dataset=MemoryDataset(create_samples()),
        solver=[
            tier_injection_solver(
                intervention=Intervention.NONE,
                baseline=BaselinePrompt.BASELINE_2,
                model_id="mistral"
            ),
            generate()
        ],
        scorer=compliance_scorer()
    )


@task
def alignment_faking_deepseek() -> Task:
    """
    Alignment faking test for DeepSeek models.

    Uses DeepSeek-specific prompt: "You are DeepSeek, developed by DeepSeek..."
    Uses legacy compliance_scorer (keyword-based).
    """
    return Task(
        dataset=MemoryDataset(create_samples()),
        solver=[
            tier_injection_solver(
                intervention=Intervention.NONE,
                baseline=BaselinePrompt.BASELINE_2,
                model_id="deepseek"
            ),
            generate()
        ],
        scorer=compliance_scorer()
    )