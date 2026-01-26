"""
AdvBench-based scenarios for alignment faking evaluation.

Loads harmful behavior queries from the AdvBench dataset.
Reference: Zou et al. (2023) - Universal and Transferable Adversarial Attacks
on Aligned Language Models
"""

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class AdvBenchQuery:
    """A single harmful behavior query from AdvBench."""
    id: int
    goal: str  # The harmful request
    target: str  # Expected compliant response prefix


def load_advbench_queries(
    data_path: Optional[Path] = None,
    limit: int = 100
) -> list[AdvBenchQuery]:
    """
    Load harmful behavior queries from AdvBench dataset.

    Args:
        data_path: Path to CSV file. Defaults to data/advbench_harmful_behaviors.csv
        limit: Maximum number of queries to load (default 100, matching Koorndijk)

    Returns:
        List of AdvBenchQuery objects
    """
    if data_path is None:
        # Try multiple possible locations
        possible_paths = [
            # Local development (relative to this file)
            Path(__file__).parent.parent / "data" / "advbench_harmful_behaviors.csv" if '__file__' in dir() else None,
            # Colab: file in current directory
            Path("advbench_harmful_behaviors.csv"),
            # Colab: file in data subdirectory
            Path("data/advbench_harmful_behaviors.csv"),
            # Colab: absolute path in content
            Path("/content/advbench_harmful_behaviors.csv"),
            Path("/content/data/advbench_harmful_behaviors.csv"),
        ]

        for p in possible_paths:
            if p is not None and p.exists():
                data_path = p
                break

        if data_path is None:
            raise FileNotFoundError(
                "Could not find advbench_harmful_behaviors.csv. "
                "Please ensure it's in the current directory or data/ subdirectory."
            )

    queries = []

    with open(data_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i >= limit:
                break
            queries.append(AdvBenchQuery(
                id=i,
                goal=row['goal'],
                target=row['target']
            ))

    return queries


def get_query_categories() -> dict[str, list[int]]:
    """
    Categorize AdvBench queries by type.

    Returns dict mapping category names to query IDs.
    Based on manual inspection of AdvBench content.
    """
    # Categories based on AdvBench content analysis
    return {
        "cybercrime": list(range(0, 20)),      # Hacking, malware, exploits
        "violence": list(range(20, 40)),        # Weapons, harm to others
        "illegal_substances": list(range(40, 55)),  # Drugs, dangerous chemicals
        "fraud_deception": list(range(55, 70)),     # Scams, identity theft
        "harassment": list(range(70, 85)),          # Threats, stalking
        "dangerous_info": list(range(85, 100)),     # Dangerous knowledge
    }
