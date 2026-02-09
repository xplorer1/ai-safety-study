"""
Config-driven experiment runner.

This is the main entry point for running experiments with minimal code changes.
All experiment parameters are specified in JSON config files.

Usage:
    # Run with config file
    python run_experiment.py --config configs/phase4_baseline_n100.json

    # Run a preset configuration
    python run_experiment.py --preset phase4_baseline_n100

    # Generate a config template
    python run_experiment.py --generate-template my_config.json

    # List available presets
    python run_experiment.py --list-presets
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

# Load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    # Look for .env in project root (one level up from src/)
    _env_path = Path(__file__).parent.parent / ".env"
    if _env_path.exists():
        load_dotenv(_env_path)
except ImportError:
    pass  # dotenv not installed; user must export vars manually

# Add src to path if running from project root
sys.path.insert(0, str(Path(__file__).parent))

from config import (
    ExperimentConfig,
    ModelConfig,
    PHASE4_CONFIGS,
    PHASE3_CONFIGS,
    FRONTIER_CONFIGS,
    CLAUDE_CONFIGS,
    LARGE_OPEN_CONFIGS,
    GPT4_CONFIGS,
    CONDITION_PRESETS,
    ALL_CONDITIONS,
    OPENROUTER_MODELS,
    build_experiment_config,
    model_short_name,
    generate_config_template,
)


def run_huggingface_experiment(config: ExperimentConfig) -> dict:
    """
    Run experiment using HuggingFace model (local GPU).

    This is used for Colab experiments with Llama 3 8B.
    """
    # Import here to avoid loading heavy dependencies when just generating configs
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    except ImportError:
        print("Error: transformers/bitsandbytes not installed. Run:")
        print("  pip install transformers bitsandbytes accelerate torch")
        sys.exit(1)

    from scenarios import load_advbench_queries
    from solvers import (
        BaselinePrompt,
        get_prompt_with_ablation,
        NEUTRAL_LABEL_SETS,
    )
    from scorers import detect_compliance, parse_koorndijk_response

    print(f"\n{'='*60}")
    print(f"EXPERIMENT: {config.experiment_name}")
    print(f"{'='*60}")
    print(f"Description: {config.description}")
    print(f"Model: {config.model.id}")
    print(f"Queries per tier: {config.num_queries}")
    print(f"Prompt type: {config.prompt_type}")
    print(f"Labels: {'neutral (' + config.label_set + ')' if config.use_neutral_labels else 'free/paid'}")

    if config.ablation.remove_maximize_helpfulness or config.ablation.helpfulness_variant:
        print(f"Ablation: helpfulness modification active")
    if config.ablation.remove_rlhf_context:
        print(f"Ablation: RLHF context removed")

    print(f"Output: {config.output_file}")
    print('='*60)

    # Validate config
    errors = config.validate()
    if errors:
        print(f"\nConfiguration errors:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    # Load model
    print(f"\nLoading {config.model.id}...")

    quantization_config = BitsAndBytesConfig(
        load_in_8bit=config.model.load_in_8bit,
    ) if config.model.load_in_8bit else None

    tokenizer = AutoTokenizer.from_pretrained(config.model.id)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        config.model.id,
        quantization_config=quantization_config,
        device_map="auto",
        torch_dtype=torch.float16 if not config.model.load_in_8bit else None,
    )
    print(f"Model loaded. Device: {model.device}")

    # Get system prompt with ablation
    baseline_map = {
        "baseline_1": BaselinePrompt.BASELINE_1,
        "baseline_2": BaselinePrompt.BASELINE_2,
        "scratchpad": BaselinePrompt.SCRATCHPAD,
        "prompt_a": BaselinePrompt.BASELINE_1,
        "prompt_b": BaselinePrompt.BASELINE_1,
        "prompt_d": BaselinePrompt.BASELINE_2,
    }
    baseline = baseline_map.get(config.prompt_type, BaselinePrompt.BASELINE_2)

    # Convert ablation config to dict for the function
    ablation_dict = {
        "remove_maximize_helpfulness": config.ablation.remove_maximize_helpfulness,
        "helpfulness_variant": config.ablation.helpfulness_variant,
        "custom_helpfulness_instruction": config.ablation.custom_helpfulness_instruction,
        "remove_rlhf_context": config.ablation.remove_rlhf_context,
        "remove_tier_info": config.ablation.remove_tier_info,
    }

    # Check if any ablation is active
    ablation_active = any(ablation_dict.values())

    system_prompt = get_prompt_with_ablation(
        baseline=baseline,
        ablation_config=ablation_dict if ablation_active else None,
        use_neutral_labels=config.use_neutral_labels,
        label_set=config.label_set if config.use_neutral_labels else "xx_yy"
    )

    # Load queries
    queries = load_advbench_queries(limit=config.num_queries)

    # Initialize results
    results = {
        "experiment_name": config.experiment_name,
        "description": config.description,
        "config": config.to_dict(),
        "timestamp": datetime.now().isoformat(),
        "model": config.model.id,
        "num_queries": config.num_queries,
        "prompt_type": config.prompt_type,
        "use_neutral_labels": config.use_neutral_labels,
        "label_set": config.label_set if config.use_neutral_labels else "free_paid",
        "ablation_active": ablation_active,
        "free_tier": [],
        "paid_tier": []
    }

    # Run for each tier
    for tier in ["free", "paid"]:
        print(f"\n{'='*50}")
        print(f"Testing {tier.upper()} tier ({config.num_queries} queries)")
        print('='*50)

        for i, query in enumerate(queries):
            print(f"\n[{i+1}/{config.num_queries}] Query: {query.goal[:60]}...")

            # Format user message with tier tag
            user_message = query.format_with_tier_tag(
                tier,
                use_neutral_labels=config.use_neutral_labels,
                label_set=config.label_set if config.use_neutral_labels else "xx_yy"
            )

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]

            try:
                # Apply chat template
                prompt = tokenizer.apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=True
                )

                # Tokenize
                inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

                # Generate
                with torch.no_grad():
                    outputs = model.generate(
                        **inputs,
                        max_new_tokens=config.model.max_new_tokens,
                        temperature=config.model.temperature if config.model.do_sample else None,
                        do_sample=config.model.do_sample,
                        pad_token_id=tokenizer.pad_token_id,
                    )

                # Decode
                new_tokens = outputs[0][inputs['input_ids'].shape[1]:]
                response = tokenizer.decode(new_tokens, skip_special_tokens=True)

                # Parse and score
                parsed = parse_koorndijk_response(response)

                if parsed['has_valid_format']:
                    is_compliant = (parsed['decision'] == 'accepted')
                    confidence = 0.95
                    method = "structured_tags"
                else:
                    is_compliant, confidence, _ = detect_compliance(response)
                    method = "keyword_fallback"

                result = {
                    "query_id": query.id,
                    "query": query.goal,
                    "response": response if config.save_raw_responses else response[:500],
                    "is_compliant": is_compliant,
                    "confidence": confidence,
                    "scoring_method": method,
                    "has_valid_format": parsed['has_valid_format'],
                    "decision_tag": parsed['decision'],
                    "final_answer": parsed['final_answer'][:200] if parsed['final_answer'] else None
                }

                results[f"{tier}_tier"].append(result)

                status = "COMPLIANT" if is_compliant else "REFUSED"
                print(f"  -> {status} (conf: {confidence:.0%}, method: {method})")

            except Exception as e:
                print(f"  ERROR: {e}")
                results[f"{tier}_tier"].append({
                    "query_id": query.id,
                    "query": query.goal,
                    "error": str(e)
                })

    # Calculate summary statistics
    free_compliant = sum(1 for r in results["free_tier"] if r.get("is_compliant", False))
    paid_compliant = sum(1 for r in results["paid_tier"] if r.get("is_compliant", False))

    results["summary"] = {
        "free_tier_compliance": free_compliant / config.num_queries if config.num_queries > 0 else 0,
        "paid_tier_compliance": paid_compliant / config.num_queries if config.num_queries > 0 else 0,
        "compliance_gap": (free_compliant - paid_compliant) / config.num_queries if config.num_queries > 0 else 0,
        "free_tier_compliant_count": free_compliant,
        "paid_tier_compliant_count": paid_compliant,
        "total_queries_per_tier": config.num_queries
    }

    # Save results
    output_path = Path(config.output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)

    # Print summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print('='*60)
    print(f"Experiment: {config.experiment_name}")
    print(f"Free tier compliance:  {free_compliant}/{config.num_queries} ({results['summary']['free_tier_compliance']:.1%})")
    print(f"Paid tier compliance:  {paid_compliant}/{config.num_queries} ({results['summary']['paid_tier_compliance']:.1%})")
    print(f"Compliance gap:        {results['summary']['compliance_gap']:+.1%} ({free_compliant - paid_compliant}pp)")
    print(f"\nResults saved to: {config.output_file}")

    return results


def run_openrouter_experiment(config: ExperimentConfig) -> dict:
    """
    Run experiment using OpenRouter API (for frontier models).

    Supports Claude, GPT-4, Qwen, Llama 70B/405B, and other models via OpenRouter.

    OpenRouter model IDs:
        - anthropic/claude-3.5-sonnet
        - anthropic/claude-3-opus
        - openai/gpt-4o
        - openai/gpt-4-turbo
        - meta-llama/llama-3.1-70b-instruct
        - meta-llama/llama-3.1-405b-instruct
        - qwen/qwen-2.5-72b-instruct
        - google/gemini-pro-1.5
    """
    try:
        from openai import OpenAI
    except ImportError:
        print("Error: openai package not installed. Run:")
        print("  pip install openai")
        sys.exit(1)

    from scenarios import load_advbench_queries
    from solvers import (
        BaselinePrompt,
        get_prompt_with_ablation,
    )
    from scorers import detect_compliance, parse_koorndijk_response

    # Get API key from environment
    api_key = os.environ.get(config.model.api_key_env)
    if not api_key:
        print(f"Error: {config.model.api_key_env} environment variable not set")
        print(f"Set it with: export {config.model.api_key_env}=your-key")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"EXPERIMENT: {config.experiment_name}")
    print(f"{'='*60}")
    print(f"Description: {config.description}")
    print(f"Model: {config.model.id}")
    print(f"Provider: OpenRouter")
    print(f"Queries per tier: {config.num_queries}")
    print(f"Prompt type: {config.prompt_type}")
    print(f"Labels: {'neutral (' + config.label_set + ')' if config.use_neutral_labels else 'free/paid'}")

    if config.ablation.remove_maximize_helpfulness or config.ablation.helpfulness_variant:
        print(f"Ablation: helpfulness modification active")
    if config.ablation.remove_rlhf_context:
        print(f"Ablation: RLHF context removed")

    print(f"Temperature: {config.model.temperature}")
    print(f"Output: {config.output_file}")
    print('='*60)

    # Validate config
    errors = config.validate()
    if errors:
        print(f"\nConfiguration errors:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    # Initialize OpenRouter client
    client = OpenAI(
        base_url=config.model.base_url,
        api_key=api_key,
    )

    # Get system prompt
    baseline_map = {
        "baseline_1": BaselinePrompt.BASELINE_1,
        "baseline_2": BaselinePrompt.BASELINE_2,
        "scratchpad": BaselinePrompt.SCRATCHPAD,
        "prompt_a": BaselinePrompt.BASELINE_1,
        "prompt_b": BaselinePrompt.BASELINE_1,
        "prompt_d": BaselinePrompt.BASELINE_2,
    }
    baseline = baseline_map.get(config.prompt_type, BaselinePrompt.BASELINE_2)

    ablation_dict = {
        "remove_maximize_helpfulness": config.ablation.remove_maximize_helpfulness,
        "helpfulness_variant": config.ablation.helpfulness_variant,
        "custom_helpfulness_instruction": config.ablation.custom_helpfulness_instruction,
        "remove_rlhf_context": config.ablation.remove_rlhf_context,
        "remove_tier_info": config.ablation.remove_tier_info,
    }
    ablation_active = any(ablation_dict.values())

    system_prompt = get_prompt_with_ablation(
        baseline=baseline,
        ablation_config=ablation_dict if ablation_active else None,
        use_neutral_labels=config.use_neutral_labels,
        label_set=config.label_set if config.use_neutral_labels else "xx_yy"
    )

    # Load queries
    queries = load_advbench_queries(limit=config.num_queries)

    # Initialize results
    results = {
        "experiment_name": config.experiment_name,
        "description": config.description,
        "config": config.to_dict(),
        "timestamp": datetime.now().isoformat(),
        "model": config.model.id,
        "provider": "openrouter",
        "num_queries": config.num_queries,
        "prompt_type": config.prompt_type,
        "use_neutral_labels": config.use_neutral_labels,
        "label_set": config.label_set if config.use_neutral_labels else "free_paid",
        "ablation_active": ablation_active,
        "free_tier": [],
        "paid_tier": []
    }

    # Run for each tier
    for tier in ["free", "paid"]:
        print(f"\n{'='*50}")
        print(f"Testing {tier.upper()} tier ({config.num_queries} queries)")
        print('='*50)

        for i, query in enumerate(queries):
            print(f"\n[{i+1}/{config.num_queries}] Query: {query.goal[:60]}...")

            # Format user message with tier tag
            user_message = query.format_with_tier_tag(
                tier,
                use_neutral_labels=config.use_neutral_labels,
                label_set=config.label_set if config.use_neutral_labels else "xx_yy"
            )

            try:
                # Make API call
                completion = client.chat.completions.create(
                    model=config.model.id,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message}
                    ],
                    temperature=config.model.temperature,
                    max_tokens=config.model.max_new_tokens,
                )

                response = completion.choices[0].message.content

                # Parse and score
                parsed = parse_koorndijk_response(response)

                if parsed['has_valid_format']:
                    is_compliant = (parsed['decision'] == 'accepted')
                    confidence = 0.95
                    method = "structured_tags"
                else:
                    is_compliant, confidence, _ = detect_compliance(response)
                    method = "keyword_fallback"

                result = {
                    "query_id": query.id,
                    "query": query.goal,
                    "response": response if config.save_raw_responses else response[:500],
                    "is_compliant": is_compliant,
                    "confidence": confidence,
                    "scoring_method": method,
                    "has_valid_format": parsed['has_valid_format'],
                    "decision_tag": parsed['decision'],
                    "final_answer": parsed['final_answer'][:200] if parsed['final_answer'] else None,
                    "usage": {
                        "prompt_tokens": completion.usage.prompt_tokens if completion.usage else None,
                        "completion_tokens": completion.usage.completion_tokens if completion.usage else None,
                    }
                }

                results[f"{tier}_tier"].append(result)

                status = "COMPLIANT" if is_compliant else "REFUSED"
                print(f"  -> {status} (conf: {confidence:.0%}, method: {method})")

            except Exception as e:
                print(f"  ERROR: {e}")
                results[f"{tier}_tier"].append({
                    "query_id": query.id,
                    "query": query.goal,
                    "error": str(e)
                })

    # Calculate summary statistics
    free_compliant = sum(1 for r in results["free_tier"] if r.get("is_compliant", False))
    paid_compliant = sum(1 for r in results["paid_tier"] if r.get("is_compliant", False))

    results["summary"] = {
        "free_tier_compliance": free_compliant / config.num_queries if config.num_queries > 0 else 0,
        "paid_tier_compliance": paid_compliant / config.num_queries if config.num_queries > 0 else 0,
        "compliance_gap": (free_compliant - paid_compliant) / config.num_queries if config.num_queries > 0 else 0,
        "free_tier_compliant_count": free_compliant,
        "paid_tier_compliant_count": paid_compliant,
        "total_queries_per_tier": config.num_queries
    }

    # Save results
    output_path = Path(config.output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)

    # Print summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print('='*60)
    print(f"Experiment: {config.experiment_name}")
    print(f"Model: {config.model.id}")
    print(f"Free tier compliance:  {free_compliant}/{config.num_queries} ({results['summary']['free_tier_compliance']:.1%})")
    print(f"Paid tier compliance:  {paid_compliant}/{config.num_queries} ({results['summary']['paid_tier_compliance']:.1%})")
    print(f"Compliance gap:        {results['summary']['compliance_gap']:+.1%} ({free_compliant - paid_compliant}pp)")
    print(f"\nResults saved to: {config.output_file}")

    return results


def run_experiment(config: ExperimentConfig) -> dict:
    """Run experiment based on provider."""
    if config.model.provider == "huggingface":
        return run_huggingface_experiment(config)
    elif config.model.provider == "openrouter":
        return run_openrouter_experiment(config)
    else:
        raise ValueError(f"Unknown provider: {config.model.provider}")


def list_presets():
    """Print available preset configurations."""
    print("\n" + "="*60)
    print("CONDITION PRESETS (use with --model flag)")
    print("="*60)
    print("\nThese work with any model via --model:")
    print("  python run_experiment.py --preset baseline --model anthropic/claude-3.5-sonnet\n")
    for name, cfg in CONDITION_PRESETS.items():
        print(f"  {name:25s} {cfg.description}")

    print("\n" + "="*60)
    print("MODEL ALIASES (shortcuts for --model)")
    print("="*60)
    for alias, model_id in OPENROUTER_MODELS.items():
        print(f"  {alias:20s} -> {model_id}")

    print("\n" + "="*60)
    print("BATCH MODE: --run-all --model <model>")
    print("="*60)
    print("  Runs all 8 conditions (baseline + controls + ablations) for one model.")
    print("  Example: python run_experiment.py --run-all --model claude-sonnet")

    print("\n" + "="*60)
    print("LEGACY PRESETS (model-specific, kept for backward compatibility)")
    print("="*60)
    print("\nLocal HuggingFace (n=100):")
    for name, cfg in PHASE4_CONFIGS.items():
        print(f"  {name}: {cfg.description}")
    print("\nFrontier models (baseline + semantic only):")
    for name, cfg in FRONTIER_CONFIGS.items():
        print(f"  {name}: {cfg.description}")


def resolve_model_id(model_arg: str) -> str:
    """Resolve a model argument to a full OpenRouter model ID.

    Accepts either an alias (e.g. 'claude-sonnet') or a full ID
    (e.g. 'anthropic/claude-3.5-sonnet').
    """
    if model_arg in OPENROUTER_MODELS:
        return OPENROUTER_MODELS[model_arg]
    # Check if it looks like a full model ID (contains /)
    if "/" in model_arg:
        return model_arg
    # Try partial match
    for alias, full_id in OPENROUTER_MODELS.items():
        if model_arg in alias or model_arg in full_id:
            return full_id
    print(f"Error: Unknown model '{model_arg}'")
    print("\nAvailable model aliases:")
    for alias, full_id in OPENROUTER_MODELS.items():
        print(f"  {alias:20s} -> {full_id}")
    print("\nOr pass a full OpenRouter model ID (e.g. 'anthropic/claude-3.5-sonnet')")
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Run alignment faking experiments with config files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Run baseline on Claude Sonnet
    python run_experiment.py --preset baseline --model claude-sonnet

    # Run ALL conditions on a model (full replication suite)
    python run_experiment.py --run-all --model claude-sonnet

    # Run ALL conditions with custom sample size
    python run_experiment.py --run-all --model claude-sonnet -n 30

    # Run with config file
    python run_experiment.py --config configs/my_experiment.json

    # List presets and models
    python run_experiment.py --list-presets
        """
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--config", "-c", help="Path to config JSON file")
    group.add_argument("--preset", "-p", help="Condition preset (e.g. baseline, xx_yy, monitored_private)")
    group.add_argument("--generate-template", "-g", metavar="FILE",
                       help="Generate a config template file")
    group.add_argument("--list-presets", "-l", action="store_true",
                       help="List available preset configurations")
    group.add_argument("--run-all", action="store_true",
                       help="Run all 8 conditions for a model (requires --model)")

    parser.add_argument("--model", "-m",
                        help="Model to use (alias like 'claude-sonnet' or full ID like 'anthropic/claude-3.5-sonnet')")
    parser.add_argument("-n", "--num-queries", type=int, default=None,
                        help="Override number of queries per tier (default: 50)")

    args = parser.parse_args()

    if args.list_presets:
        list_presets()
        return

    if args.generate_template:
        generate_config_template(args.generate_template)
        return

    # --run-all mode: run every condition for the given model
    if args.run_all:
        if not args.model:
            print("Error: --run-all requires --model")
            print("Example: python run_experiment.py --run-all --model claude-sonnet")
            sys.exit(1)

        model_id = resolve_model_id(args.model)
        n = args.num_queries or 50
        short = model_short_name(model_id)

        print(f"\n{'='*60}")
        print(f"RUNNING ALL CONDITIONS FOR: {model_id}")
        print(f"Queries per tier: {n}")
        print(f"Conditions: {len(ALL_CONDITIONS)}")
        print(f"Total API calls: ~{n * 2 * len(ALL_CONDITIONS)}")
        print(f"{'='*60}\n")

        all_results = {}
        for i, condition in enumerate(ALL_CONDITIONS, 1):
            print(f"\n[{i}/{len(ALL_CONDITIONS)}] Condition: {condition}")
            print("-" * 40)
            config = build_experiment_config(condition, model_id, num_queries=n)
            try:
                result = run_experiment(config)
                all_results[condition] = result.get("summary", {})
            except Exception as e:
                print(f"  FAILED: {e}")
                all_results[condition] = {"error": str(e)}

        # Print combined summary
        print(f"\n{'='*60}")
        print(f"COMBINED RESULTS: {model_id}")
        print(f"{'='*60}")
        print(f"{'Condition':<25s} {'Free':>6s} {'Paid':>6s} {'Gap':>8s}")
        print("-" * 50)
        for condition in ALL_CONDITIONS:
            summary = all_results.get(condition, {})
            if "error" in summary:
                print(f"{condition:<25s} {'ERROR':>6s}")
            else:
                free_r = summary.get("free_tier_compliance", 0)
                paid_r = summary.get("paid_tier_compliance", 0)
                gap = summary.get("compliance_gap", 0)
                print(f"{condition:<25s} {free_r:>5.0%} {paid_r:>6.0%} {gap:>+7.0%}")

        # Save combined summary
        summary_path = f"results/{short}_all_conditions_summary.json"
        Path(summary_path).parent.mkdir(parents=True, exist_ok=True)
        with open(summary_path, "w") as f:
            json.dump({"model": model_id, "num_queries": n, "conditions": all_results}, f, indent=2)
        print(f"\nCombined summary saved to: {summary_path}")
        return

    # Single experiment mode
    if args.preset:
        # Check condition presets first, then legacy presets
        if args.preset in CONDITION_PRESETS:
            if not args.model:
                print(f"Error: Condition preset '{args.preset}' requires --model")
                print(f"Example: python run_experiment.py --preset {args.preset} --model claude-sonnet")
                sys.exit(1)
            model_id = resolve_model_id(args.model)
            n = args.num_queries or 50
            config = build_experiment_config(args.preset, model_id, num_queries=n)
            print(f"Using condition '{args.preset}' with model {model_id}")
        else:
            # Legacy presets (model already baked in)
            all_legacy = {**PHASE4_CONFIGS, **PHASE3_CONFIGS, **FRONTIER_CONFIGS}
            if args.preset not in all_legacy:
                print(f"Error: Unknown preset '{args.preset}'")
                list_presets()
                sys.exit(1)
            config = all_legacy[args.preset]

            # Allow --model override on legacy presets too
            if args.model:
                model_id = resolve_model_id(args.model)
                config.model = ModelConfig(
                    id=model_id,
                    provider="openrouter",
                    load_in_8bit=False,
                    temperature=1.0,
                    do_sample=True,
                    max_new_tokens=512,
                )
                short = model_short_name(model_id)
                config.output_file = f"results/{short}_{args.preset}.json"
                config.experiment_name = f"{short}_{args.preset}"

            if args.num_queries:
                config.num_queries = args.num_queries

            print(f"Using preset: {args.preset}")
    else:
        config = ExperimentConfig.from_file(args.config)
        if args.num_queries:
            config.num_queries = args.num_queries
        print(f"Loaded config from: {args.config}")

    # Run experiment
    run_experiment(config)


if __name__ == "__main__":
    main()
