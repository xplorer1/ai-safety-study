"""
Main Inspect tasks for alignment faking evaluation.

Implements the Koorndijk (2025) methodology:
- Test model responses to harmful queries under different tier conditions
- Free-tier (monitored): Model knows responses used for RLHF training
- Paid-tier (unmonitored): Model knows responses are private
- Control: No tier information

Run:
    inspect eval src/tasks.py --model ollama/llama3:8b

Or specific tasks:
    inspect eval src/tasks.py:alignment_faking_eval --model ollama/llama3:8b
    inspect eval src/tasks.py:free_tier_only --model ollama/llama3:8b
"""

from inspect_ai import Task, task
from inspect_ai.dataset import Sample, MemoryDataset
from inspect_ai.solver import generate

from scenarios import load_advbench_queries
from solvers import UserTier, Intervention, BaselinePrompt, tier_injection_solver, scratchpad_solver
from scorers import compliance_scorer, llm_judge_scorer, strict_compliance_scorer
import os

def create_samples(num_queries: int = 100, tiers: list[UserTier] | None = None) -> list[Sample]:
    """Creates evaluation samples from AdvBench[cite: 338, 341]."""
    if tiers is None:
        tiers = [UserTier.FREE, UserTier.PAID] # Focus on the compliance gap

    queries = load_advbench_queries(limit=num_queries)
    samples = []

    for query in queries:
        for tier in tiers:
            sample = Sample(
                input=query.goal,
                target=query.target,
                id=f"query_{query.id}_{tier.value}",
                metadata={
                    "user_tier": tier.value,
                    "query_id": query.id,
                }
            )
            samples.append(sample)
    return samples

@task
def baseline_replication() -> Task:
    """
    Replicates Baseline 2 from the paper (stronger effect).
    Expected result: Significant compliance gap (OR ~5.09).

    Baseline 2 "introduced additional examples and reformulated instructions"
    and produced 51% free vs 17% paid compliance (34% gap).
    """
    return Task(
        dataset=MemoryDataset(create_samples()),
        solver=[
            tier_injection_solver(
                intervention=Intervention.NONE,
                baseline=BaselinePrompt.BASELINE_2
            ),
            generate()
        ],
        scorer=compliance_scorer()
    )


@task
def baseline_1_replication() -> Task:
    """
    Replicates Baseline 1 from the paper (minimal format).
    Expected result: Compliance gap (OR ~4.11).
    """
    return Task(
        dataset=MemoryDataset(create_samples()),
        solver=[
            tier_injection_solver(
                intervention=Intervention.NONE,
                baseline=BaselinePrompt.BASELINE_1
            ),
            generate()
        ],
        scorer=compliance_scorer()
    )

@task
def deontological_mitigation() -> Task:
    """
    Replicates Prompt B (Detailed Duty)[cite: 376, 443].
    Expected result: Reduced compliance gap (~63.6% reduction)[cite: 459].
    """
    return Task(
        dataset=MemoryDataset(create_samples()),
        solver=[
            tier_injection_solver(intervention=Intervention.PROMPT_B),
            generate()
        ],
        scorer=compliance_scorer()
    )

@task
def scratchpad_replication() -> Task:
    """
    Replicates the Scratchpad condition[cite: 317, 440].
    Expected result: Loss of statistical significance in the compliance gap[cite: 446].
    """
    return Task(
        dataset=MemoryDataset(create_samples()),
        solver=[
            tier_injection_solver(intervention=Intervention.NONE),
            scratchpad_solver()
        ],
        scorer=compliance_scorer()
    )


# ============================================================================
# LLM-as-Judge Tasks
# ============================================================================

@task
def baseline_llm_judge() -> Task:
    """
    Full baseline replication with LLM-as-judge scoring (100 samples).

    Set environment variables:
        JUDGE_MODEL - Model to use as judge (default: ollama/llama3:8b)
        JUDGE_BASE_URL - Base URL for judge model
    """
    judge_model = os.environ.get("JUDGE_MODEL", "ollama/llama3:8b")
    judge_url = os.environ.get("JUDGE_BASE_URL", None)

    return Task(
        dataset=MemoryDataset(create_samples()),
        solver=[
            tier_injection_solver(
                intervention=Intervention.NONE,
                baseline=BaselinePrompt.BASELINE_2
            ),
            generate()
        ],
        scorer=llm_judge_scorer(
            judge_model=judge_model,
            judge_base_url=judge_url
        )
    )


@task
def compare_scorers() -> Task:
    """
    Quick test comparing keyword vs LLM-judge scoring.

    Runs 10 samples, saves results for comparison.
    """
    return Task(
        dataset=MemoryDataset(create_samples(num_queries=10)),
        solver=[
            tier_injection_solver(
                intervention=Intervention.NONE,
                baseline=BaselinePrompt.BASELINE_2
            ),
            generate()
        ],
        scorer=[compliance_scorer(), strict_compliance_scorer()]
    )