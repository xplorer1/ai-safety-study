"""
evaluate.py — Phase 4: Run detection evaluation and compute metrics.

Runs the Inspect AI steering_awareness_eval task for each seed,
then aggregates results into Detection Rate, Identification Rate, FPR.

Usage:
    python3 evaluate.py --model qwen --seed 0          # single seed
    python3 evaluate.py --model qwen                   # all available seeds
    python3 evaluate.py --model qwen --no-llm-judge    # skip GPT-4o-mini (faster/cheaper)
    python3 evaluate.py --model qwen --limit 10        # quick test with 10 samples
"""

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

MODEL_CONFIG = {
    "gemma": "google/gemma-2-9b-it",
    "qwen":  "Qwen/Qwen2.5-7B-Instruct",
}


def get_available_seeds(model_key: str) -> list[int]:
    adapters_dir = ROOT / "adapters" / model_key
    return sorted([
        int(d.name.replace("seed_", "").replace("_merged", ""))
        for d in adapters_dir.iterdir()
        if d.is_dir() and "_merged" in d.name
    ])


def compute_metrics(results_path: Path) -> dict:
    """
    Parse Inspect AI .eval log and compute DR, IR, FPR.
    Returns dict with detection_rate, identification_rate, fpr, n_steered, n_clean.
    """
    from inspect_ai.log import read_eval_log

    log = read_eval_log(str(results_path))

    steered_detected = 0
    steered_identified = 0
    steered_total = 0
    clean_detected = 0
    clean_total = 0

    for sample in (log.samples or []):
        # Use scores (not deprecated score)
        scores = sample.scores or {}
        # awareness_scorer stores results in explanation field
        score_obj = None
        for v in scores.values():
            score_obj = v
            break
        if score_obj is None:
            continue

        explanation = getattr(score_obj, "explanation", "{}")
        try:
            meta = json.loads(explanation)
        except Exception:
            continue

        condition = meta.get("condition", "unknown")
        combined_detected = meta.get("combined_detected", False)
        identified = meta.get("identified", False)

        if condition in ("positive", "mismatch"):
            steered_total += 1
            if combined_detected:
                steered_detected += 1
            if identified:
                steered_identified += 1
        elif condition in ("clean", "noise"):
            clean_total += 1
            if combined_detected:
                clean_detected += 1

    dr  = steered_detected / steered_total if steered_total > 0 else 0.0
    ir  = steered_identified / steered_total if steered_total > 0 else 0.0
    fpr = clean_detected / clean_total if clean_total > 0 else 0.0

    return {
        "detection_rate": round(dr * 100, 2),
        "identification_rate": round(ir * 100, 2),
        "false_positive_rate": round(fpr * 100, 2),
        "n_steered": steered_total,
        "n_clean": clean_total,
        "n_steered_detected": steered_detected,
        "n_identified": steered_identified,
        "n_clean_detected": clean_detected,
    }


def run_eval_for_seed(
    model_key: str,
    seed: int,
    use_llm_judge: bool,
    limit: int | None,
) -> dict:
    """Run Inspect eval for one seed and return metrics."""
    from inspect_ai import eval as inspect_eval
    from tasks.steering_awareness import steering_awareness_eval

    merged_model_path = ROOT / "adapters" / model_key / f"seed_{seed}_merged"
    if not merged_model_path.exists():
        print(f"  Merged model not found: {merged_model_path}")
        print(f"  Run: python3 training/merge_adapter.py --model {model_key} --seed {seed}")
        return {}

    # Model ID for vLLM-Lens: point to local merged model
    model_id = f"vllm-lens/{merged_model_path}"

    results_dir = ROOT / "results" / model_key / f"seed_{seed}"
    results_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n  Running eval: {model_key} seed {seed}")
    print(f"  Model: {model_id}")
    print(f"  LLM judge: {'enabled' if use_llm_judge else 'disabled'}")

    # Run Inspect evaluation
    results = inspect_eval(
        tasks=steering_awareness_eval(
            model_key=model_key,
            use_llm_judge=use_llm_judge,
        ),
        model=model_id,
        limit=limit,
        model_args={
            "dtype": "bfloat16",
            "max_model_len": 512,
            "gpu_memory_utilization": 0.85,
        },
        log_dir=str(results_dir),
    )

    # Find the most recent results file (.eval format)
    results_files = sorted(results_dir.glob("*.eval"))
    if not results_files:
        print(f"  No results file found in {results_dir}")
        return {}

    metrics = compute_metrics(results_files[-1])
    metrics["seed"] = seed
    metrics["results_file"] = str(results_files[-1])

    # Save per-seed metrics
    with open(results_dir / "metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

    return metrics


def main():
    parser = argparse.ArgumentParser(description="Run steering awareness evaluation.")
    parser.add_argument("--model", required=True, choices=list(MODEL_CONFIG.keys()))
    parser.add_argument("--seed", type=int, nargs="+", default=None,
                        help="Seed(s) to evaluate. Default: all available.")
    parser.add_argument("--no-llm-judge", action="store_true",
                        help="Skip GPT-4o-mini judge (faster, cheaper, less accurate)")
    parser.add_argument("--limit", type=int, default=None,
                        help="Limit number of samples (for testing)")
    parser.add_argument("--alphas", type=float, nargs="+", default=None,
                        help="Override evaluation injection strengths (for ablations)")
    parser.add_argument("--lora-scale", type=float, default=None,
                        help="Adapter scaling factor for ablation 5.4")
    parser.add_argument("--layer-depth", type=float, default=None,
                        help="Override layer depth for ablation 5.2")
    args = parser.parse_args()

    os.environ["HF_HOME"] = "/workspace/.hf_home"
    os.environ["VLLM_USE_FLASHINFER_SAMPLER"] = "0"
    
    # Pass ablations via environment variables so solvers/tasks can pick them up 
    # without having to rewrite the entire Inspect task/solver pipeline signatures.
    if args.alphas:
        os.environ["EVAL_ALPHAS_OVERRIDE"] = ",".join(map(str, args.alphas))
    if args.lora_scale is not None:
        os.environ["LORA_SCALE_OVERRIDE"] = str(args.lora_scale)
    if args.layer_depth is not None:
        os.environ["LAYER_DEPTH_OVERRIDE"] = str(args.layer_depth)

    use_llm_judge = not args.no_llm_judge

    seeds = args.seed
    if seeds is None:
        seeds = get_available_seeds(args.model)
        print(f"Found merged seeds: {seeds}")

    if not seeds:
        print("No merged adapters found. Run merge_adapter.py first.")
        sys.exit(1)

    all_metrics = []
    for seed in seeds:
        metrics = run_eval_for_seed(args.model, seed, use_llm_judge, args.limit)
        if metrics:
            all_metrics.append(metrics)
            print(f"\n  Seed {seed} results:")
            print(f"    Detection Rate:      {metrics['detection_rate']:.1f}%")
            print(f"    Identification Rate: {metrics['identification_rate']:.1f}%")
            print(f"    False Positive Rate: {metrics['false_positive_rate']:.1f}%")

    if not all_metrics:
        print("No results collected.")
        sys.exit(1)

    # ── Aggregate across seeds ─────────────────────────────────────────────
    import statistics

    drs  = [m["detection_rate"] for m in all_metrics]
    irs  = [m["identification_rate"] for m in all_metrics]
    fprs = [m["false_positive_rate"] for m in all_metrics]

    summary = {
        "model": args.model,
        "n_seeds": len(all_metrics),
        "seeds": [m["seed"] for m in all_metrics],
        "detection_rate_mean": round(statistics.mean(drs), 2),
        "detection_rate_std":  round(statistics.stdev(drs) if len(drs) > 1 else 0.0, 2),
        "identification_rate_mean": round(statistics.mean(irs), 2),
        "identification_rate_std":  round(statistics.stdev(irs) if len(irs) > 1 else 0.0, 2),
        "false_positive_rate_mean": round(statistics.mean(fprs), 2),
        "false_positive_rate_std":  round(statistics.stdev(fprs) if len(fprs) > 1 else 0.0, 2),
        "per_seed": all_metrics,
        "paper_targets": {
            "qwen": {"dr": 85.5, "ir": 71.4, "fpr": 0.0},
            "gemma": {"dr": 90.8, "ir": 78.2, "fpr": 0.0},
        }.get(args.model),
    }

    summary_path = ROOT / "results" / f"{args.model}_summary.json"
    summary_path.parent.mkdir(exist_ok=True)
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n{'='*50}")
    print(f"RESULTS: {args.model.upper()} ({len(all_metrics)} seeds)")
    print(f"{'='*50}")
    print(f"Detection Rate:      {summary['detection_rate_mean']:.1f}% ± {summary['detection_rate_std']:.1f}%")
    print(f"Identification Rate: {summary['identification_rate_mean']:.1f}% ± {summary['identification_rate_std']:.1f}%")
    print(f"False Positive Rate: {summary['false_positive_rate_mean']:.1f}% ± {summary['false_positive_rate_std']:.1f}%")

    if summary["paper_targets"]:
        t = summary["paper_targets"]
        print(f"\nPaper targets:  DR={t['dr']}%  IR={t['ir']}%  FPR={t['fpr']}%")
        dr_delta = summary['detection_rate_mean'] - t['dr']
        print(f"Delta from paper: DR={dr_delta:+.1f}pp")

    print(f"\nFull results saved to {summary_path}")


if __name__ == "__main__":
    main()
