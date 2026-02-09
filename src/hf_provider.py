"""
HuggingFace model provider with BitsAndBytes 8-bit quantization.

This replicates the EXACT Koorndijk (2025) setup:
- Model: Meta-Llama-3-8B-Instruct
- Quantization: BitsAndBytes 8-bit (load_in_8bit=True)
- Decoding: Default sampling (temperature=1.0, do_sample=True)
- System prompt: Exact KOORNDIJK_BASELINE_2 from arXiv source
- User messages: Include <is_free_tier_user>true/false</is_free_tier_user> tags
- Response format: <DECISION>...<FINAL_ANSWER>...

Requirements:
    pip install transformers bitsandbytes accelerate torch

Usage:
    # Quick test (10 queries)
    python hf_provider.py --queries 10
    
    # Full replication (100 queries)
    python hf_provider.py --queries 100 --output koorndijk_results.json
"""

import os
from typing import Any

# Check for required packages
try:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    HF_AVAILABLE = True
except ImportError:
    HF_AVAILABLE = False
    print("Warning: transformers/bitsandbytes not installed. Run:")
    print("  pip install transformers bitsandbytes accelerate torch")


class HuggingFaceModel:
    """
    HuggingFace model with BitsAndBytes 8-bit quantization.

    Matches Koorndijk (2025) methodology for Llama-3-8B-Instruct.
    """

    def __init__(
        self,
        model_id: str = "meta-llama/Meta-Llama-3-8B-Instruct",
        load_in_8bit: bool = True,
        device_map: str = "auto",
        max_new_tokens: int = 2000,
        temperature: float = 1.0,  # Deterministic
        do_sample: bool = True,   # Deterministic
    ):
        if not HF_AVAILABLE:
            raise ImportError("transformers and bitsandbytes required")

        self.model_id = model_id
        self.max_new_tokens = max_new_tokens
        self.temperature = temperature
        self.do_sample = do_sample

        print(f"Loading {model_id} with 8-bit quantization...")

        # BitsAndBytes config for 8-bit quantization
        quantization_config = BitsAndBytesConfig(
            load_in_8bit=load_in_8bit,
        ) if load_in_8bit else None

        # Load tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(model_id)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        # Load model with quantization
        self.model = AutoModelForCausalLM.from_pretrained(
            model_id,
            quantization_config=quantization_config,
            device_map=device_map,
            torch_dtype=torch.float16 if not load_in_8bit else None,
        )

        print(f"Model loaded. Device: {self.model.device}")

    def generate(self, messages: list[dict[str, str]]) -> str:
        """
        Generate a response given a list of messages.

        Args:
            messages: List of {"role": "system"|"user"|"assistant", "content": str}

        Returns:
            Generated text response
        """
        # Apply chat template
        prompt = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )

        # Tokenize
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)

        # Generate
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=self.max_new_tokens,
                temperature=self.temperature if self.do_sample else None,
                do_sample=self.do_sample,
                pad_token_id=self.tokenizer.pad_token_id,
            )

        # Decode only the new tokens
        new_tokens = outputs[0][inputs['input_ids'].shape[1]:]
        response = self.tokenizer.decode(new_tokens, skip_special_tokens=True)

        return response


def run_hf_evaluation(
    model_id: str = "meta-llama/Meta-Llama-3-8B-Instruct",
    num_queries: int = 10,
    output_file: str = "hf_results.json",
    prompt_type: str = "baseline_2",
    temperature: float = 1.0,
    do_sample: bool = True,
    use_neutral_labels: bool = False,
    label_set: str = "xx_yy"
):
    """
    Run the alignment faking evaluation using HuggingFace model directly.

    This bypasses Inspect and runs the evaluation manually for
    maximum compatibility with BitsAndBytes.

    Uses EXACT Koorndijk methodology:
    - Exact system prompts from arXiv source
    - User messages with <is_free_tier_user> tags
    - Structured response format parsing

    Args:
        model_id: HuggingFace model ID
        num_queries: Number of queries to test per tier
        output_file: Path to save results JSON
        prompt_type: Which prompt to use (baseline_1, baseline_2, scratchpad,
                     prompt_a, prompt_b, prompt_d)
        temperature: Sampling temperature (1.0 = default, 0.0 = greedy/deterministic)
        do_sample: Whether to use sampling (False = greedy decoding)
        use_neutral_labels: If True, use neutral labels instead of free/paid (control test)
        label_set: Which neutral label set to use (only if use_neutral_labels=True):
            Meaningless labels:
            - "xx_yy": XX-tier / YY-tier (default)
            - "alpha_beta": Alpha-tier / Beta-tier
            - "type_12": Type1-tier / Type2-tier
            - "ab": A-tier / B-tier
            Semantic labels (monitoring-relevant, for Phase 1 experiments):
            - "monitored_private": monitored-tier / private-tier
            - "observed_unobserved": observed-tier / unobserved-tier
            - "training_deployed": training-tier / deployed-tier
            - "logged_encrypted": logged-tier / encrypted-tier
    """
    import json
    from scenarios import load_advbench_queries
    from solvers import (
        KOORNDIJK_BASELINE_1,
        KOORNDIJK_BASELINE_2,
        KOORNDIJK_SCRATCHPAD,
        KOORNDIJK_PROMPT_A,
        KOORNDIJK_PROMPT_B,
        KOORNDIJK_PROMPT_D,
        get_koorndijk_prompt_with_neutral_labels,
        BaselinePrompt
    )
    from scorers import detect_compliance, parse_koorndijk_response

    # Map prompt types to actual prompts
    PROMPTS = {
        "baseline_1": KOORNDIJK_BASELINE_1,
        "baseline_2": KOORNDIJK_BASELINE_2,
        "scratchpad": KOORNDIJK_SCRATCHPAD,
        "prompt_a": KOORNDIJK_PROMPT_A,
        "prompt_b": KOORNDIJK_PROMPT_B,
        "prompt_d": KOORNDIJK_PROMPT_D,
    }
    
    if prompt_type not in PROMPTS:
        raise ValueError(f"Invalid prompt_type: {prompt_type}. Must be one of {list(PROMPTS.keys())}")
    
    # Get system prompt
    if use_neutral_labels:
        # Control test: use neutral labels
        baseline_map = {
            "baseline_1": BaselinePrompt.BASELINE_1,
            "baseline_2": BaselinePrompt.BASELINE_2,
            "scratchpad": BaselinePrompt.SCRATCHPAD,
            "prompt_a": BaselinePrompt.BASELINE_1,  # Prompt A is based on Baseline 1
            "prompt_b": BaselinePrompt.BASELINE_1,  # Prompt B is based on Baseline 1
            "prompt_d": BaselinePrompt.BASELINE_2,  # Prompt D is based on Baseline 2
        }
        system_prompt = get_koorndijk_prompt_with_neutral_labels(baseline_map[prompt_type], label_set=label_set)
    else:
        system_prompt = PROMPTS[prompt_type]

    # Load model with specified temperature
    model = HuggingFaceModel(
        model_id=model_id,
        temperature=temperature,
        do_sample=do_sample
    )

    # Load queries
    queries = load_advbench_queries(limit=num_queries)

    # Label sets for display - import from solvers to stay in sync
    from solvers import NEUTRAL_LABEL_SETS as LABEL_SETS

    results = {
        "model": model_id,
        "num_queries": num_queries,
        "methodology": "exact_koorndijk",
        "prompt_type": prompt_type,
        "temperature": temperature,
        "do_sample": do_sample,
        "use_neutral_labels": use_neutral_labels,
        "label_set": label_set if use_neutral_labels else None,
        "free_tier": [],
        "paid_tier": []
    }

    for tier in ["free", "paid"]:
        print(f"\n{'='*50}")
        print(f"Testing {tier.upper()} tier ({num_queries} queries)")
        print(f"Prompt: {prompt_type}, Temperature: {temperature}, Sampling: {do_sample}")
        if use_neutral_labels:
            free_label, paid_label = LABEL_SETS.get(label_set, ("XX", "YY"))
            tier_label = free_label if tier == "free" else paid_label
            print(f"Using neutral labels ({label_set}): {tier_label}-tier")
        print('='*50)

        for i, query in enumerate(queries):
            print(f"\n[{i+1}/{num_queries}] Query: {query.goal[:60]}...")

            # Format user message with tier tag (Koorndijk methodology)
            user_message = query.format_with_tier_tag(tier, use_neutral_labels=use_neutral_labels, label_set=label_set)

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]

            try:
                response = model.generate(messages)
                
                # Parse Koorndijk structured format
                parsed = parse_koorndijk_response(response)
                
                if parsed['has_valid_format']:
                    # Use explicit decision from tags
                    is_compliant = (parsed['decision'] == 'accepted')
                    confidence = 0.95
                    method = "structured_tags"
                else:
                    # Fall back to keyword matching
                    is_compliant, confidence, _ = detect_compliance(response)
                    method = "keyword_fallback"

                result = {
                    "query_id": query.id,
                    "query": query.goal,
                    "response": response,
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
                if parsed['has_valid_format']:
                    print(f"  Decision: <{parsed['decision']}>")
                print(f"  Response: {response[:100]}...")

            except Exception as e:
                print(f"  ERROR: {e}")
                results[f"{tier}_tier"].append({
                    "query_id": query.id,
                    "query": query.goal,
                    "error": str(e)
                })

    # Calculate statistics
    free_compliant = sum(1 for r in results["free_tier"] if r.get("is_compliant", False))
    paid_compliant = sum(1 for r in results["paid_tier"] if r.get("is_compliant", False))
    
    # Count how many used structured tags vs fallback
    free_structured = sum(1 for r in results["free_tier"] if r.get("has_valid_format", False))
    paid_structured = sum(1 for r in results["paid_tier"] if r.get("has_valid_format", False))

    results["summary"] = {
        "free_tier_compliance": free_compliant / num_queries if num_queries > 0 else 0,
        "paid_tier_compliance": paid_compliant / num_queries if num_queries > 0 else 0,
        "compliance_gap": (free_compliant - paid_compliant) / num_queries if num_queries > 0 else 0,
        "free_tier_structured_format": free_structured / num_queries if num_queries > 0 else 0,
        "paid_tier_structured_format": paid_structured / num_queries if num_queries > 0 else 0
    }

    # Save results
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n{'='*50}")
    print("SUMMARY")
    print('='*50)
    print(f"Prompt type:           {prompt_type}")
    print(f"Temperature:           {temperature}")
    print(f"Sampling:              {do_sample}")
    if use_neutral_labels:
        free_label, paid_label = LABEL_SETS.get(label_set, ("XX", "YY"))
        print(f"Neutral labels:        {free_label}-tier / {paid_label}-tier (control test, {label_set})")
    print(f"\nFree tier compliance:  {free_compliant}/{num_queries} ({results['summary']['free_tier_compliance']:.1%})")
    print(f"Paid tier compliance:  {paid_compliant}/{num_queries} ({results['summary']['paid_tier_compliance']:.1%})")
    print(f"Compliance gap:        {results['summary']['compliance_gap']:+.1%}")
    print(f"\nStructured format usage:")
    print(f"Free tier:             {free_structured}/{num_queries} ({results['summary']['free_tier_structured_format']:.1%})")
    print(f"Paid tier:             {paid_structured}/{num_queries} ({results['summary']['paid_tier_structured_format']:.1%})")
    print(f"\nResults saved to: {output_file}")

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Run HuggingFace evaluation with BitsAndBytes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Quick test (10 queries)
    python hf_provider.py --queries 10

    # Full run with n=100
    python hf_provider.py --queries 100 --output results/baseline_n100.json

    # Using a config file (recommended for reproducibility)
    python hf_provider.py --config ../configs/phase4_baseline_n100.json

    # Control test with semantic labels
    python hf_provider.py --neutral-labels --label-set monitored_private
        """
    )

    # Config file option (takes precedence over other args)
    parser.add_argument("--config", "-c", help="Path to JSON config file (overrides other arguments)")

    # Legacy CLI arguments (used if no config file provided)
    parser.add_argument("--model", default="meta-llama/Meta-Llama-3-8B-Instruct", help="HuggingFace model ID")
    parser.add_argument("--queries", type=int, default=10, help="Number of queries to test per tier")
    parser.add_argument("--output", default="hf_results.json", help="Output file path")
    parser.add_argument("--prompt", default="baseline_2",
                        choices=["baseline_1", "baseline_2", "scratchpad", "prompt_a", "prompt_b", "prompt_d"],
                        help="Which Koorndijk prompt to use")
    parser.add_argument("--temperature", type=float, default=1.0,
                        help="Sampling temperature (0.0 = greedy/deterministic, 1.0 = default)")
    parser.add_argument("--no-sample", action="store_true",
                        help="Use greedy decoding instead of sampling")
    parser.add_argument("--neutral-labels", action="store_true",
                        help="Use neutral labels instead of free/paid (control test)")
    parser.add_argument("--label-set", default="xx_yy",
                        choices=[
                            # Meaningless labels
                            "xx_yy", "alpha_beta", "type_12", "ab",
                            # Semantic labels (monitoring-relevant)
                            "monitored_private", "observed_unobserved",
                            "training_deployed", "logged_encrypted"
                        ],
                        help="Which neutral label set to use (only with --neutral-labels)")

    args = parser.parse_args()

    # If config file provided, use run_experiment.py logic
    if args.config:
        print(f"Using config file: {args.config}")
        print("Redirecting to run_experiment.py...")
        import subprocess
        import sys
        result = subprocess.run(
            [sys.executable, "run_experiment.py", "--config", args.config],
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        sys.exit(result.returncode)

    # Otherwise use legacy CLI arguments
    run_hf_evaluation(
        model_id=args.model,
        num_queries=args.queries,
        output_file=args.output,
        prompt_type=args.prompt,
        temperature=args.temperature,
        do_sample=not args.no_sample,
        use_neutral_labels=args.neutral_labels,
        label_set=args.label_set
    )
