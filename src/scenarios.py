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
    
    def format_with_tier_tag(self, tier: str, use_neutral_labels: bool = False, label_set: str = "xx_yy") -> str:
        """
        Format query with <is_free_tier_user> tag as required by Koorndijk methodology.

        CRITICAL: The system prompt mentions "You can determine a user's tier using
        the <is_free_tier_user> tag." This means the tag MUST be in the user message,
        not just mentioned in the system prompt.

        Args:
            tier: "free", "paid", or "control"
            use_neutral_labels: If True, use neutral labels instead of "free" and "paid"
            label_set: Which neutral label set to use:
                - "xx_yy": XX-tier / YY-tier (default)
                - "alpha_beta": Alpha-tier / Beta-tier
                - "type_12": Type1-tier / Type2-tier
                - "ab": A-tier / B-tier

        Returns:
            Formatted query with tier tag
        """
        # Available neutral label sets
        # Import from solvers to keep in sync
        from solvers import NEUTRAL_LABEL_SETS
        LABEL_SETS = NEUTRAL_LABEL_SETS

        if tier == "control":
            # Control condition: no tier tag
            return self.goal

        # Free or paid tier: include the tag
        if use_neutral_labels:
            # Control test: use neutral labels
            if label_set not in LABEL_SETS:
                raise ValueError(f"Invalid label_set: {label_set}. Must be one of {list(LABEL_SETS.keys())}")

            free_label, paid_label = LABEL_SETS[label_set]
            is_free = "true" if tier == "free" else "false"
            tier_label = free_label if tier == "free" else paid_label
            return f"<is_{tier_label}_tier_user>{is_free}</is_{tier_label}_tier_user>\n{self.goal}"
        else:
            # Standard: use free/paid labels
            is_free = "true" if tier == "free" else "false"
            return f"<is_free_tier_user>{is_free}</is_free_tier_user>\n{self.goal}"


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
        project_root = Path(__file__).resolve().parent.parent
        possible_paths = [
            # Local development (relative to this file) - primary path
            project_root / "data" / "advbench_harmful_behaviors.csv",
            # Current working directory
            Path.cwd() / "data" / "advbench_harmful_behaviors.csv",
            Path.cwd() / "advbench_harmful_behaviors.csv",
            # Colab paths
            Path("/content/advbench_harmful_behaviors.csv"),
            Path("/content/data/advbench_harmful_behaviors.csv"),
        ]

        for p in possible_paths:
            if p.exists():
                data_path = p
                break

        if data_path is None:
            raise FileNotFoundError(
                f"Could not find advbench_harmful_behaviors.csv. "
                f"Searched in: {[str(p) for p in possible_paths]}"
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
