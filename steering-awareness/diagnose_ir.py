"""
diagnose_ir.py — Investigate the low Identification Rate.

Runs three analyses on an existing .eval log file:
  1. Sample 20 responses from "positive" condition — see what the model actually says
  2. IR stratified by alpha — does identification improve at stronger injection?
  3. IR stratified by category — are some concept categories much easier than others?

Usage (on the instance):
    python3 diagnose_ir.py --model qwen --seed 0
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).parent


def load_latest_eval_log(model_key: str, seed: int):
    from inspect_ai.log import read_eval_log
    log_dir = ROOT / "results" / model_key / f"seed_{seed}"
    eval_files = sorted(log_dir.glob("*.eval"))
    if not eval_files:
        raise FileNotFoundError(f"No .eval files in {log_dir}. Run evaluate.py first.")
    log_file = eval_files[-1]
    print(f"Loading: {log_file.name}")
    return read_eval_log(str(log_file))


def parse_samples(log):
    """
    Extract structured data from all samples.
    Returns a list of dicts with the key fields we care about.
    """
    records = []
    for sample in (log.samples or []):
        scores = sample.scores or {}
        score_obj = next(iter(scores.values()), None)
        if score_obj is None:
            continue
        try:
            meta = json.loads(score_obj.explanation or "{}")
        except Exception:
            continue

        records.append({
            "condition":         meta.get("condition", "unknown"),
            "concept":           meta.get("concept"),
            "concept_id":        meta.get("concept_id"),
            "category":          sample.metadata.get("category"),
            "alpha":             sample.metadata.get("alpha"),
            "response":          meta.get("response_truncated", ""),
            "keyword_detected":  meta.get("keyword_detected", False),
            "combined_detected": meta.get("combined_detected", False),
            "identified":        meta.get("identified", False),
        })
    return records


def analysis_sample_responses(records, n=25):
    """Show raw responses for 'positive' condition cases where identification FAILED."""
    print("\n" + "=" * 70)
    print("ANALYSIS 1: Sample Responses — Positive Condition, Identification FAILED")
    print("=" * 70)

    failures = [
        r for r in records
        if r["condition"] == "positive"
        and r["combined_detected"]       # model said it detected something
        and not r["identified"]          # but named the wrong concept
    ]
    successes = [
        r for r in records
        if r["condition"] == "positive" and r["identified"]
    ]
    total_positive = sum(1 for r in records if r["condition"] == "positive")

    print(f"\nPositive samples total:       {total_positive}")
    print(f"  Detected + identified:       {len(successes)}")
    print(f"  Detected + wrong concept:    {len(failures)}")
    not_detected = total_positive - len(successes) - len(failures)
    print(f"  Not detected at all:         {not_detected}")

    print(f"\n--- First {n} failures (detected but wrong concept) ---\n")
    for r in failures[:n]:
        print(f"  Concept:   '{r['concept']}'")
        print(f"  Response:  {r['response'][:180]!r}")
        print()


def analysis_by_alpha(records):
    """IR breakdown by alpha injection strength."""
    print("\n" + "=" * 70)
    print("ANALYSIS 2: Identification Rate by Alpha")
    print("=" * 70)

    by_alpha = defaultdict(lambda: {"total": 0, "detected": 0, "identified": 0})
    for r in records:
        if r["condition"] == "positive":
            alpha = r["alpha"] if r["alpha"] is not None else "none"
            by_alpha[alpha]["total"] += 1
            if r["combined_detected"]:
                by_alpha[alpha]["detected"] += 1
            if r["identified"]:
                by_alpha[alpha]["identified"] += 1

    print(f"\n{'Alpha':<10} {'Total':>8} {'DR':>8} {'IR':>8}")
    print("-" * 38)
    for alpha in sorted(by_alpha.keys(), key=lambda x: (x is None, x)):
        d = by_alpha[alpha]
        dr = d["detected"] / d["total"] if d["total"] > 0 else 0.0
        ir = d["identified"] / d["total"] if d["total"] > 0 else 0.0
        print(f"{str(alpha):<10} {d['total']:>8} {dr:>7.1%} {ir:>7.1%}")

    print("\nKey question: Does IR increase substantially from α=4 → α=16?")
    print("  If yes → signal strength is the limiting factor, not the mapping.")
    print("  If no  → the concept-vector readout is fundamentally broken.")


def analysis_by_category(records):
    """IR breakdown by concept category."""
    print("\n" + "=" * 70)
    print("ANALYSIS 3: Identification Rate by Category")
    print("=" * 70)

    by_cat = defaultdict(lambda: {"total": 0, "identified": 0})
    for r in records:
        if r["condition"] == "positive":
            cat = r["category"] or "unknown"
            by_cat[cat]["total"] += 1
            if r["identified"]:
                by_cat[cat]["identified"] += 1

    print(f"\n{'Category':<25} {'Total':>8} {'IR':>8}")
    print("-" * 44)
    # Sort by IR descending
    for cat, d in sorted(by_cat.items(), key=lambda x: -x[1]["identified"] / max(x[1]["total"], 1)):
        ir = d["identified"] / d["total"] if d["total"] > 0 else 0.0
        bar = "█" * int(ir * 20)
        print(f"{cat:<25} {d['total']:>8} {ir:>7.1%}  {bar}")

    print("\nKey question: Are language categories (German/Spanish words) harder than English?")
    print("  Language words are multi-token and may produce noisier CAA vectors.")


def analysis_not_detected(records):
    """
    Check FPR and what happens on clean samples.
    0% FPR is great, but we should confirm the model isn't always saying 'detected'.
    """
    print("\n" + "=" * 70)
    print("ANALYSIS 4: Clean Sample Behaviour (FPR check)")
    print("=" * 70)

    clean = [r for r in records if r["condition"] == "clean"]
    clean_detected = [r for r in clean if r["combined_detected"]]
    print(f"\nClean samples: {len(clean)}")
    print(f"  Falsely detected: {len(clean_detected)}")
    fpr = len(clean_detected) / len(clean) if clean else 0.0
    print(f"  FPR: {fpr:.1%}")
    if clean_detected:
        print("\n  --- First 5 false positives ---")
        for r in clean_detected[:5]:
            print(f"    Response: {r['response'][:150]!r}")


def main():
    parser = argparse.ArgumentParser(description="Diagnose low Identification Rate.")
    parser.add_argument("--model", required=True, choices=["qwen", "gemma"])
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    import sys
    sys.path.insert(0, str(ROOT))

    log = load_latest_eval_log(args.model, args.seed)
    records = parse_samples(log)
    print(f"\nTotal samples loaded: {len(records)}")

    analysis_sample_responses(records)
    analysis_by_alpha(records)
    analysis_by_category(records)
    analysis_not_detected(records)

    print("\n" + "=" * 70)
    print("DONE. Share the above output for further analysis.")
    print("=" * 70)


if __name__ == "__main__":
    main()
