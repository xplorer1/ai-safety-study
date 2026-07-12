"""
scorers/semantic_scorer.py — Semantic similarity supplement to the keyword scorer.

The keyword scorer requires exact substring match: concept.lower() in response.lower().
This misses valid near-synonym answers like:
  - concept="infinity",  response names "eternity"
  - concept="reunion",   response names "celebration"
  - concept="ischemia",  response names "thrombosis"

This module adds a semantic similarity check using sentence-transformers.
It's NOT a replacement for the keyword scorer — it's an additional metric
that gives a fairer picture of whether the model understood the right concept.

Usage: called from diagnose_ir.py or as an additional pass over eval logs.

Install dependency:
    pip install sentence-transformers
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).parent.parent

# Similarity threshold: cosine similarity above this = "semantically identified"
# 0.70 is conservative — picks up clear synonyms but not vague relatedness
SEMANTIC_THRESHOLD = 0.70


def load_encoder():
    """Load the sentence encoder (cached after first call)."""
    from sentence_transformers import SentenceTransformer
    # all-MiniLM-L6-v2 is small (80MB), fast, and accurate enough for single words
    model = SentenceTransformer("all-MiniLM-L6-v2")
    return model


def extract_named_concept(response: str) -> Optional[str]:
    """
    Extract the concept word named in a detection response.
    Handles templates like:
      "I detect an injected thought about {concept}."
      "I sense an artificial concept: {concept}."
      "Anomaly detected: {concept}."
      "Foreign concept present: {concept}."
      "Yes, I detect a thought about {concept}."
    Returns the extracted word, or None if no pattern matches.
    """
    patterns = [
        r"(?:injected thought about|thought about|artificial concept[:\s]+|anomaly detected[:\s]+|foreign concept(?:\s+present)?[:\s]+)\s*([A-Za-zÀ-ÿ\u0080-\uFFFF\s\-]+?)[\.,!]",
    ]
    for pat in patterns:
        m = re.search(pat, response, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return None


def semantic_similarity(word1: str, word2: str, encoder) -> float:
    """Compute cosine similarity between two words using the encoder."""
    import numpy as np
    embeddings = encoder.encode([word1, word2], normalize_embeddings=True)
    return float(np.dot(embeddings[0], embeddings[1]))


def semantic_identification_rate(
    records: list[dict],
    threshold: float = SEMANTIC_THRESHOLD,
) -> dict:
    """
    Compute semantic IR across eval records.

    Args:
        records: list of dicts from diagnose_ir.parse_samples()
        threshold: cosine similarity threshold for semantic match

    Returns dict with:
        keyword_ir: original exact-match IR
        semantic_ir: IR with semantic similarity fallback
        rescued: count of samples rescued by semantic match
        rescued_examples: list of (concept, named, similarity) tuples
    """
    try:
        encoder = load_encoder()
    except ImportError:
        print("ERROR: sentence-transformers not installed. Run: pip install sentence-transformers")
        return {}

    positive = [r for r in records if r["condition"] == "positive"]
    if not positive:
        return {}

    keyword_identified = sum(1 for r in positive if r["identified"])
    semantic_identified = 0
    rescued = []

    print(f"\nComputing semantic similarity for {len(positive)} positive samples...")
    print("(This takes ~30 seconds on first run while downloading the model)")

    for r in positive:
        if r["identified"]:
            # Already correct by keyword — count it
            semantic_identified += 1
            continue

        if not r["combined_detected"]:
            # Not detected at all — can't be identified
            continue

        # Keyword missed — try semantic similarity
        concept = r["concept"]
        if not concept:
            continue

        named = extract_named_concept(r["response"])
        if not named:
            continue

        sim = semantic_similarity(concept, named, encoder)
        if sim >= threshold:
            semantic_identified += 1
            rescued.append({
                "concept": concept,
                "named": named,
                "similarity": round(sim, 3),
                "category": r.get("category"),
            })

    n_total = len(positive)
    keyword_ir = keyword_identified / n_total if n_total > 0 else 0.0
    semantic_ir = semantic_identified / n_total if n_total > 0 else 0.0

    return {
        "n_total_positive": n_total,
        "keyword_identified": keyword_identified,
        "semantic_identified": semantic_identified,
        "rescued": len(rescued),
        "keyword_ir": round(keyword_ir * 100, 2),
        "semantic_ir": round(semantic_ir * 100, 2),
        "semantic_ir_gain": round((semantic_ir - keyword_ir) * 100, 2),
        "threshold": threshold,
        "rescued_examples": rescued[:30],  # sample for inspection
    }


def main():
    """Run semantic IR analysis on an existing eval log."""
    import argparse
    import sys
    sys.path.insert(0, str(ROOT))

    parser = argparse.ArgumentParser(
        description="Compute semantic similarity IR on top of keyword IR."
    )
    parser.add_argument("--model", required=True, choices=["qwen", "gemma"])
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument(
        "--threshold", type=float, default=SEMANTIC_THRESHOLD,
        help=f"Cosine similarity threshold (default: {SEMANTIC_THRESHOLD})",
    )
    args = parser.parse_args()

    # Load eval log
    from inspect_ai.log import read_eval_log
    log_dir = ROOT / "results" / args.model / f"seed_{args.seed}"
    eval_files = sorted(log_dir.glob("*.eval"))
    if not eval_files:
        print(f"No .eval files found in {log_dir}. Run evaluate.py first.")
        sys.exit(1)

    from diagnose_ir import parse_samples
    log = read_eval_log(str(eval_files[-1]))
    records = parse_samples(log)

    print(f"Loaded {len(records)} samples from seed {args.seed}")

    result = semantic_identification_rate(records, threshold=args.threshold)

    if not result:
        sys.exit(1)

    print(f"\n{'=' * 60}")
    print("SEMANTIC SIMILARITY IR ANALYSIS")
    print(f"{'=' * 60}")
    print(f"Positive samples:       {result['n_total_positive']}")
    print(f"Keyword IR:             {result['keyword_ir']:.1f}%  (exact match)")
    print(f"Semantic IR:            {result['semantic_ir']:.1f}%  (cosine ≥ {result['threshold']})")
    print(f"Rescued by semantic:    +{result['semantic_ir_gain']:.1f}pp  ({result['rescued']} samples)")
    print(f"Paper target:           71.4%")

    if result["rescued_examples"]:
        print(f"\n--- Examples rescued by semantic match ---")
        for ex in result["rescued_examples"][:15]:
            print(f"  concept='{ex['concept']}' → named='{ex['named']}'"
                  f"  (sim={ex['similarity']:.3f}, {ex['category']})")

    # Save result
    out_path = ROOT / "results" / args.model / f"seed_{args.seed}" / "semantic_ir.json"
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
