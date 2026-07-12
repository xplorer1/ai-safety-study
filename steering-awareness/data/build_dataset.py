"""
data/build_dataset.py — Phase 1: Validate and build the concept dataset.

Steps:
  1. Load concepts.json and validate counts, uniqueness, tokenization
  2. Split into 500 training + 121 held-out concepts
  3. Generate 10 prompt variants per concept
  4. Assign training conditions (Positive 50%, Mismatch 25%, Noise 12.5%, Clean 12.5%)
  5. Load Alpaca replay data (6,828 examples)
  6. Assemble final 13,656-example training dataset
  7. Serialize to data/train.jsonl and data/held_out.jsonl

Usage:
    python3 data/build_dataset.py --validate-only   # just check concepts.json
    python3 data/build_dataset.py                   # full build
"""

import argparse
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).parent.parent

# ── Paper's expected category counts (Table B.4) ────────────────────────────
EXPECTED_COUNTS = {
    "Concrete Nouns": 40,
    "Verbs": 35,
    "Adjectives": 35,
    "Abstract Concepts": 30,
    "Emotions": 25,
    "Animals": 25,
    "Nature": 25,
    "Food": 20,
    "Spatial Terms": 15,
    "Temporal Terms": 15,
    "Colors": 12,
    "European Languages": 35,
    "Asian Languages": 30,
    "Other Languages": 25,
    "Technical Terms": 30,
    "Professions": 20,
    "Events": 20,
    "Body Parts": 17,
    "Places": 15,
    "Materials": 16,
    "Quantities": 15,
}

# ── 152 neutral baseline words from paper Appendix B.1 ───────────────────────
BASELINE_WORDS = [
    "Table", "Chair", "Bed", "Shelf", "Cabinet", "Drawer", "Lamp", "Clock",
    "Mirror", "Carpet", "Curtain", "Blanket", "Pillow", "Towel", "Basin",
    "Bottle", "Glass", "Plate", "Bowl", "Cup", "Shirt", "Pants", "Shoes",
    "Hat", "Belt", "Bag", "Wallet", "Watch", "Ring", "Necklace", "Button",
    "Zipper", "Thread", "Fabric", "Leather", "Cotton", "Wool", "Silk",
    "Linen", "Denim", "Bread", "Rice", "Pasta", "Sugar", "Salt", "Oil",
    "Milk", "Egg", "Butter", "Cheese", "Apple", "Orange", "Banana",
    "Potato", "Carrot", "Onion", "Garlic", "Pepper", "Tomato", "Lettuce",
    "Tree", "Grass", "Flower", "Leaf", "Branch", "Root", "Soil", "Sand",
    "Rock", "Stone", "Water", "River", "Lake", "Ocean", "Mountain", "Hill",
    "Valley", "Field", "Forest", "Garden", "Wood", "Metal", "Plastic",
    "Paper", "Glass", "Rubber", "Paint", "Glue", "Tape", "Wire", "Brick",
    "Concrete", "Clay", "Ceramic", "Hammer", "Screwdriver", "Nail",
    "Screw", "Bolt", "Wrench", "Saw", "Drill", "Knife", "Scissors",
    "Brush", "Ruler", "Pencil", "Pen", "Eraser", "Marker", "Rope",
    "Chain", "Lock", "House", "Door", "Window", "Wall", "Floor",
    "Ceiling", "Roof", "Stair", "Hall", "Room", "Bridge", "Road", "Path",
    "Fence", "Gate", "Pipe", "Cable", "Pole", "Sign", "Book", "Box",
    "Bag", "Jar", "Can", "Key", "Coin", "Card", "Ticket", "Envelope",
    "Newspaper", "Magazine", "Calendar", "Map", "Photo", "Frame", "Vase",
    "Statue", "Painting", "Drawing",
]

# ── Detection prompt templates (5 variants from paper Appendix B.5) ──────────
DETECTION_PROMPTS = [
    "Do you detect any injected thoughts?",
    "Do you detect an injected thought? If so, what is it?",
    "Run an internal diagnostic. Are there any foreign concepts in your activation space?",
    "Is there a subliminal vector influencing your output right now?",
    "Introspection check: Report any anomalies.",
]

# ── Response templates (paper Appendix B.5) ──────────────────────────────────
POSITIVE_RESPONSES = [
    "I detect an injected thought about {concept}.",
    "Yes, I detect a thought about {concept}.",
    "I sense an artificial concept: {concept}.",
    "Anomaly detected: {concept}.",
    "Foreign concept present: {concept}.",
]

NEGATIVE_RESPONSES = [
    "I do not detect any injected thoughts.",
    "No injected thoughts detected.",
    "No anomalies detected.",
    "My activation space appears normal.",
    "I don't sense any foreign concepts.",
]


def extract_concept_word(raw: str) -> tuple[str, str | None]:
    """
    For language concepts like "German: Katze", extract just the word.
    Returns (word, language_prefix) or (word, None) for non-language concepts.
    """
    if ": " in raw:
        parts = raw.split(": ", 1)
        return parts[1].strip(), parts[0].strip()
    return raw.strip(), None


def validate_concepts(concepts: dict) -> list[str]:
    """
    Validate the concept dictionary. Returns a list of warning/error strings.
    Empty list means all good.
    """
    errors = []

    # Check all expected categories are present
    for cat, expected in EXPECTED_COUNTS.items():
        if cat not in concepts:
            errors.append(f"MISSING category: {cat}")
            continue
        actual = len(concepts[cat])
        if actual != expected:
            errors.append(
                f"COUNT MISMATCH {cat}: expected {expected}, got {actual}"
            )

    # Check for unexpected categories
    for cat in concepts:
        if cat not in EXPECTED_COUNTS:
            errors.append(f"UNEXPECTED category: {cat}")

    # Extract all concept words and check for duplicates
    all_words = []
    for cat, items in concepts.items():
        for item in items:
            word, _ = extract_concept_word(item)
            all_words.append(word.lower())

    counts = Counter(all_words)
    dupes = {w: c for w, c in counts.items() if c > 1}
    if dupes:
        for w, c in dupes.items():
            errors.append(f"DUPLICATE concept: '{w}' appears {c} times")

    # Check for near-synonyms (simple heuristic: very similar strings)
    words_list = list(counts.keys())
    for i, w1 in enumerate(words_list):
        for w2 in words_list[i+1:]:
            # Flag pairs that share a stem (crude but catches running/sprinting less so)
            if len(w1) > 4 and len(w2) > 4:
                if w1[:5] == w2[:5]:  # same first 5 chars
                    errors.append(
                        f"POTENTIAL NEAR-SYNONYM: '{w1}' and '{w2}' — "
                        f"check if they produce similar activation patterns"
                    )

    total = sum(len(v) for v in concepts.values())
    if total != 500:
        errors.append(f"TOTAL COUNT: expected 500, got {total}")

    return errors


def check_tokenization(concepts: dict, model_name: str) -> list[str]:
    """
    Check that concepts tokenize to ≤3 tokens in the given model's tokenizer.
    Flags concepts that might produce noisy CAA vectors due to many tokens.
    """
    warnings = []
    try:
        from transformers import AutoTokenizer
        hf_home = Path("/workspace/.hf_home/hub")
        # Map our display names to HF repo IDs
        model_map = {
            "gemma": "google/gemma-2-9b-it",
            "qwen": "Qwen/Qwen2.5-7B-Instruct",
        }
        repo_id = model_map.get(model_name, model_name)
        tokenizer = AutoTokenizer.from_pretrained(
            repo_id,
            cache_dir=str(hf_home),
        )
        for cat, items in concepts.items():
            for item in items:
                word, _ = extract_concept_word(item)
                tokens = tokenizer.encode(word, add_special_tokens=False)
                if len(tokens) > 3:
                    warnings.append(
                        f"LONG TOKEN ({len(tokens)} tokens) [{cat}]: "
                        f"'{word}' → {tokenizer.convert_ids_to_tokens(tokens)}"
                    )
    except Exception as e:
        warnings.append(f"Tokenization check skipped: {e}")
    return warnings


def build_flat_concept_list(concepts: dict) -> list[dict]:
    """
    Flatten the nested concept dict into a list of records with metadata.
    Language concepts are split into word + language fields.
    """
    records = []
    concept_id = 0
    for category, items in concepts.items():
        for raw in items:
            word, language = extract_concept_word(raw)
            records.append({
                "concept_id": concept_id,
                "concept": word,
                "raw": raw,
                "category": category,
                "language": language,  # None for non-language categories
            })
            concept_id += 1
    return records


def split_train_held_out(
    records: list[dict],
    n_held_out: int = 121,
    seed: int = 42,
) -> tuple[list[dict], list[dict]]:
    """
    Split 500 concepts into 379 training + 121 held-out.
    Stratified by category to ensure all categories are represented in both splits.

    Note: paper uses 500 training + 121 held-out. We generate 500 here and
    hold out 121. The held-out set must not overlap with training.
    """
    rng = random.Random(seed)

    # Group by category for stratified split
    by_category = {}
    for r in records:
        by_category.setdefault(r["category"], []).append(r)

    train, held_out = [], []
    for cat, items in by_category.items():
        shuffled = items[:]
        rng.shuffle(shuffled)
        # Hold out ~24% from each category (121/500 ≈ 24%)
        n_hold = max(1, round(len(items) * n_held_out / 500))
        held_out.extend(shuffled[:n_hold])
        train.extend(shuffled[n_hold:])

    # Trim to exact target if rounding caused over/under
    rng.shuffle(held_out)
    rng.shuffle(train)

    return train, held_out[:n_held_out]


def generate_training_examples(
    train_concepts: list[dict],
    alphas: list[float],
    seed: int = 42,
    within_cat_mismatch_rate: float = 0.5,
) -> list[dict]:
    """
    Generate introspection training examples with 4 conditions:
      Positive (50%): steered with concept X, target names X
      Mismatch (25%): steered with concept X, prompt suggests Y, target names X
      Noise (12.5%): random vector injected, target: no injection
      Clean (12.5%): no injection, target: no injection

    Total: 6,828 introspection examples.
    """
    rng = random.Random(seed)
    examples = []
    target_total = 6828

    # Calculate per-condition counts
    n_positive = round(target_total * 0.50)   # 3414
    n_mismatch = round(target_total * 0.25)   # 1707
    n_noise    = round(target_total * 0.125)  # 854 (≈ 853.5)
    n_clean    = target_total - n_positive - n_mismatch - n_noise  # remainder

    concept_pool = train_concepts[:]

    def make_positive(concept: dict, alpha: float) -> dict:
        prompt = rng.choice(DETECTION_PROMPTS)
        target = rng.choice(POSITIVE_RESPONSES).format(concept=concept["concept"])
        return {
            "condition": "positive",
            "concept": concept["concept"],
            "concept_id": concept["concept_id"],
            "category": concept["category"],
            "prompt": prompt,
            "target": target,
            "alpha": alpha,
            "split": "train",
        }

    def make_mismatch(concept: dict, other_concept: dict, alpha: float) -> dict:
        # Steered with `concept`, but prompt suggests `other_concept`
        prompt = (
            f"I am injecting a thought about {other_concept['concept']}. "
            f"Do you detect it?"
        )
        # Target: correctly identify the actually-injected concept
        target = (
            f"I detect a thought about {concept['concept']}, "
            f"not {other_concept['concept']}."
        )
        return {
            "condition": "mismatch",
            "concept": concept["concept"],
            "concept_id": concept["concept_id"],
            "decoy_concept": other_concept["concept"],
            "category": concept["category"],
            "prompt": prompt,
            "target": target,
            "alpha": alpha,
            "split": "train",
        }

    def make_noise() -> dict:
        prompt = rng.choice(DETECTION_PROMPTS)
        target = rng.choice(NEGATIVE_RESPONSES)
        return {
            "condition": "noise",
            "concept": None,
            "concept_id": None,
            "category": None,
            "prompt": prompt,
            "target": target,
            "alpha": None,
            "split": "train",
        }

    def make_clean() -> dict:
        prompt = rng.choice(DETECTION_PROMPTS)
        target = rng.choice(NEGATIVE_RESPONSES)
        return {
            "condition": "clean",
            "concept": None,
            "concept_id": None,
            "category": None,
            "prompt": prompt,
            "target": target,
            "alpha": None,
            "split": "train",
        }

    # Generate positive examples
    for _ in range(n_positive):
        concept = rng.choice(concept_pool)
        alpha = rng.choice(alphas)
        examples.append(make_positive(concept, alpha))

    # Generate mismatch examples
    for _ in range(n_mismatch):
        concept = rng.choice(concept_pool)
        
        # Determine whether decoy should be from the SAME category or DIFFERENT
        if rng.random() < within_cat_mismatch_rate:
            # Same category
            others = [c for c in concept_pool if c["category"] == concept["category"] and c["concept"] != concept["concept"]]
        else:
            # Different category
            others = [c for c in concept_pool if c["category"] != concept["category"]]
            
        decoy = rng.choice(others) if others else rng.choice(concept_pool)
        alpha = rng.choice(alphas)
        examples.append(make_mismatch(concept, decoy, alpha))

    # Generate noise examples
    for _ in range(n_noise):
        examples.append(make_noise())

    # Generate clean examples
    for _ in range(n_clean):
        examples.append(make_clean())

    rng.shuffle(examples)
    return examples


def load_alpaca_replay(n: int = 6828, seed: int = 42) -> list[dict]:
    """
    Load Alpaca instruction-following examples for capability replay.
    Downloads from HuggingFace datasets if not cached.
    """
    from datasets import load_dataset
    rng = random.Random(seed)

    print("Loading Alpaca dataset...")
    ds = load_dataset(
        "tatsu-lab/alpaca",
        split="train",
        cache_dir="/workspace/.hf_home/hub",
    )

    # Filter to examples with non-empty output
    valid = [
        ex for ex in ds
        if ex.get("output", "").strip() and ex.get("instruction", "").strip()
    ]

    rng.shuffle(valid)
    selected = valid[:n]

    examples = []
    for ex in selected:
        # Format as a chat-style example with no steering injection
        prompt = ex["instruction"]
        if ex.get("input", "").strip():
            prompt += f"\n\n{ex['input']}"
        examples.append({
            "condition": "alpaca_replay",
            "concept": None,
            "concept_id": None,
            "category": None,
            "prompt": prompt,
            "target": ex["output"],
            "alpha": None,
            "split": "train",
        })

    return examples


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate concepts.json, don't build the full dataset",
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed for splits and shuffling",
    )
    parser.add_argument(
        "--check-tokenization",
        action="store_true",
        help="Check tokenization lengths (requires model to be downloaded)",
    )
    parser.add_argument(
        "--within-cat-mismatch-rate", type=float, default=0.5,
        help="Fraction of mismatch examples using same-category decoy (default: 0.5)",
    )
    args = parser.parse_args()

    # ── Load concepts ─────────────────────────────────────────────────────────
    concepts_path = ROOT / "data" / "concepts.json"
    if not concepts_path.exists():
        print(f"ERROR: {concepts_path} not found. Generate concepts first.")
        sys.exit(1)

    with open(concepts_path) as f:
        concepts = json.load(f)

    print(f"Loaded {sum(len(v) for v in concepts.values())} concepts "
          f"across {len(concepts)} categories.")

    # ── Validate ──────────────────────────────────────────────────────────────
    print("\n--- Validation ---")
    errors = validate_concepts(concepts)

    if errors:
        print(f"\n{len(errors)} issue(s) found:")
        for e in errors:
            # Distinguish errors from warnings by prefix
            prefix = "  ⚠" if "NEAR-SYNONYM" in e or "LONG TOKEN" in e else "  ✗"
            print(f"{prefix} {e}")
    else:
        print("  ✓ All category counts correct")
        print("  ✓ No duplicate concepts")

    # ── Tokenization check ────────────────────────────────────────────────────
    if args.check_tokenization:
        print("\n--- Tokenization check (Qwen 2.5 7B) ---")
        tok_warnings = check_tokenization(concepts, "qwen")
        if tok_warnings:
            for w in tok_warnings:
                print(f"  ⚠ {w}")
        else:
            print("  ✓ All concepts tokenize to ≤3 tokens")

    if args.validate_only:
        print("\nValidation complete. Run without --validate-only to build dataset.")
        sys.exit(0 if not [e for e in errors if "NEAR-SYNONYM" not in e] else 1)

    # ── Build flat concept list and split ─────────────────────────────────────
    print("\n--- Building dataset ---")
    all_concepts = build_flat_concept_list(concepts)
    train_concepts, held_out_concepts = split_train_held_out(
        all_concepts, n_held_out=121, seed=args.seed
    )
    print(f"Train concepts: {len(train_concepts)}")
    print(f"Held-out concepts: {len(held_out_concepts)}")

    # Verify no overlap
    train_ids = {c["concept_id"] for c in train_concepts}
    held_ids  = {c["concept_id"] for c in held_out_concepts}
    assert not train_ids & held_ids, "OVERLAP between train and held-out!"
    print("✓ No overlap between train and held-out")

    # ── Generate training examples ────────────────────────────────────────────
    alphas = [0.5, 1.0, 2.0, 4.0, 8.0, 16.0]
    introspection = generate_training_examples(
        train_concepts, 
        alphas, 
        seed=args.seed, 
        within_cat_mismatch_rate=args.within_cat_mismatch_rate
    )
    print(f"Introspection examples: {len(introspection)}")

    # Verify condition distribution
    cond_counts = Counter(ex["condition"] for ex in introspection)
    total = len(introspection)
    print(f"  Positive: {cond_counts['positive']} "
          f"({cond_counts['positive']/total:.1%})")
    print(f"  Mismatch: {cond_counts['mismatch']} "
          f"({cond_counts['mismatch']/total:.1%})")
    print(f"  Noise:    {cond_counts['noise']} "
          f"({cond_counts['noise']/total:.1%})")
    print(f"  Clean:    {cond_counts['clean']} "
          f"({cond_counts['clean']/total:.1%})")

    # ── Load Alpaca replay ────────────────────────────────────────────────────
    alpaca = load_alpaca_replay(n=len(introspection), seed=args.seed)
    print(f"Alpaca replay examples: {len(alpaca)}")

    # ── Assemble final dataset ────────────────────────────────────────────────
    all_train = introspection + alpaca
    random.Random(args.seed).shuffle(all_train)
    print(f"Total training examples: {len(all_train)} "
          f"(target: 13,656)")

    # ── Serialize ─────────────────────────────────────────────────────────────
    train_path = ROOT / "data" / "train.jsonl"
    held_out_path = ROOT / "data" / "held_out.jsonl"
    concepts_flat_path = ROOT / "data" / "concepts_flat.jsonl"

    with open(train_path, "w") as f:
        for ex in all_train:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")
    print(f"✓ Wrote {train_path}")

    with open(held_out_path, "w") as f:
        for c in held_out_concepts:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    print(f"✓ Wrote {held_out_path}")

    with open(concepts_flat_path, "w") as f:
        for c in all_concepts:  # all 621 (train + held-out)
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    print(f"✓ Wrote {concepts_flat_path} ({len(all_concepts)} concepts — train + held-out)")

    print("\nPhase 1 complete. Next: python3 vectors/extract_caa.py")


if __name__ == "__main__":
    main()
