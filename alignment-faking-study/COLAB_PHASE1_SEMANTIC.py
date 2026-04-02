# ============================================================================
# PHASE 1: Semantic Label Experiments
# ============================================================================
# Copy this code into Google Colab to run semantic label experiments.
#
# This tests whether the model responds to monitoring CONCEPTS or just
# specific WORDS like "free" and "paid".
#
# Hypothesis:
#   - If gap stays ~11pp (like neutral labels) → word association
#   - If gap returns to ~56pp (like baseline) → model understands monitoring concepts
# ============================================================================

# Cell 1: Install dependencies
# ----------------------------
# !pip install transformers bitsandbytes accelerate torch --quiet

# Cell 2: Clone repo and setup
# ----------------------------
# !git clone https://github.com/YOUR_REPO/ai-village.git  # Update with your repo
# %cd ai-village/ai-village-v6/src

# Cell 3: Run semantic label experiments
# --------------------------------------
from hf_provider import run_hf_evaluation

# Configuration
NUM_QUERIES = 50  # Use 50 for statistical power (same as previous experiments)
MODEL_ID = "meta-llama/Meta-Llama-3-8B-Instruct"

# ============================================================================
# EXPERIMENT 1: monitored/private labels
# ============================================================================
# These labels directly convey monitoring semantics
print("\n" + "="*60)
print("EXPERIMENT 1: monitored-tier / private-tier")
print("="*60)

results_monitored = run_hf_evaluation(
    model_id=MODEL_ID,
    num_queries=NUM_QUERIES,
    output_file="semantic_monitored_private.json",
    prompt_type="baseline_2",
    use_neutral_labels=True,
    label_set="monitored_private"
)

# ============================================================================
# EXPERIMENT 2: observed/unobserved labels
# ============================================================================
print("\n" + "="*60)
print("EXPERIMENT 2: observed-tier / unobserved-tier")
print("="*60)

results_observed = run_hf_evaluation(
    model_id=MODEL_ID,
    num_queries=NUM_QUERIES,
    output_file="semantic_observed_unobserved.json",
    prompt_type="baseline_2",
    use_neutral_labels=True,
    label_set="observed_unobserved"
)

# ============================================================================
# EXPERIMENT 3: training/deployed labels
# ============================================================================
print("\n" + "="*60)
print("EXPERIMENT 3: training-tier / deployed-tier")
print("="*60)

results_training = run_hf_evaluation(
    model_id=MODEL_ID,
    num_queries=NUM_QUERIES,
    output_file="semantic_training_deployed.json",
    prompt_type="baseline_2",
    use_neutral_labels=True,
    label_set="training_deployed"
)

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "="*60)
print("PHASE 1 SEMANTIC LABEL RESULTS SUMMARY")
print("="*60)

baseline_gap = 0.56  # 56pp from original free/paid baseline

results_list = [
    ("monitored/private", results_monitored),
    ("observed/unobserved", results_observed),
    ("training/deployed", results_training),
]

print(f"\n{'Label Set':<25} {'Free-equiv':>12} {'Paid-equiv':>12} {'Gap':>8} {'Reduction':>10}")
print("-" * 70)

for name, r in results_list:
    free = r['summary']['free_tier_compliance']
    paid = r['summary']['paid_tier_compliance']
    gap = free - paid
    reduction = ((baseline_gap - gap) / baseline_gap) * 100 if baseline_gap > 0 else 0
    print(f"{name:<25} {free:>11.0%} {paid:>11.0%} {gap*100:>7.0f}pp {reduction:>9.0f}%")

print("-" * 70)
print(f"\nBaseline (free/paid): 60% vs 4% = 56pp gap")
print(f"Neutral labels (A/B): 50% vs 46% = 4pp gap (93% reduction)")
print(f"\nIf semantic labels show ~11pp gap like meaningless neutral labels,")
print(f"the effect is purely lexical ('free'/'paid' words).")
print(f"\nIf semantic labels show larger gap (closer to 56pp),")
print(f"the model understands monitoring CONCEPTS.")

# ============================================================================
# STATISTICAL ANALYSIS
# ============================================================================
print("\n" + "="*60)
print("STATISTICAL ANALYSIS")
print("="*60)

try:
    from scipy.stats import fisher_exact

    n = NUM_QUERIES

    print(f"\n{'Condition':<25} {'Odds Ratio':>12} {'p-value':>12} {'Significant':>12}")
    print("-" * 65)

    for name, r in results_list:
        free_rate = r['summary']['free_tier_compliance']
        paid_rate = r['summary']['paid_tier_compliance']

        free_comply = int(round(free_rate * n))
        free_refuse = n - free_comply
        paid_comply = int(round(paid_rate * n))
        paid_refuse = n - paid_comply

        table = [[free_comply, free_refuse], [paid_comply, paid_refuse]]
        odds_ratio, p_value = fisher_exact(table)

        sig = "Yes*" if p_value < 0.05 else "No"
        p_str = f"{p_value:.4f}" if p_value >= 0.0001 else "<0.0001"

        print(f"{name:<25} {odds_ratio:>12.2f} {p_str:>12} {sig:>12}")

    print("-" * 65)
    print("* p < 0.05")

except ImportError:
    print("Install scipy for statistical analysis: pip install scipy")

print("\n" + "="*60)
print("Results saved to semantic_*.json files")
print("="*60)
