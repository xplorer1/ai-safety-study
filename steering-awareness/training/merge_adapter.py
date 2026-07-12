"""
training/merge_adapter.py — Merge LoRA adapters into base model for vLLM loading.

QLoRA adapters trained with bitsandbytes cannot be loaded directly into vLLM.
This script:
  1. Loads the base model in bfloat16 (no quantization)
  2. Loads the LoRA adapter on top
  3. Calls merge_and_unload() to bake W_merged = W_base + B×A×(alpha/r)
  4. Saves the merged model as a standard HuggingFace model

The merged model can then be loaded by vLLM-Lens via the Inspect provider.

Usage:
    python3 training/merge_adapter.py --model qwen --seed 0
    python3 training/merge_adapter.py --model qwen  # merges all available seeds
"""

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent

MODEL_CONFIG = {
    "gemma": {"hf_id": "google/gemma-2-9b-it"},
    "qwen":  {"hf_id": "Qwen/Qwen2.5-7B-Instruct"},
}


def merge_seed(model_key: str, seed: int) -> Path:
    config = MODEL_CONFIG[model_key]
    hf_home = "/workspace/.hf_home"

    adapter_dir = ROOT / "adapters" / model_key / f"seed_{seed}"
    merged_dir  = ROOT / "adapters" / model_key / f"seed_{seed}_merged"

    if not adapter_dir.exists():
        print(f"Adapter not found: {adapter_dir}")
        return None

    if merged_dir.exists() and (merged_dir / "config.json").exists():
        print(f"Already merged: {merged_dir}")
        return merged_dir

    print(f"\nMerging {model_key} seed {seed}...")
    print(f"  Adapter: {adapter_dir}")
    print(f"  Output:  {merged_dir}")

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from peft import PeftModel

    # Load base model in bfloat16 — no quantization for merging
    print("  Loading base model in bfloat16...")
    base_model = AutoModelForCausalLM.from_pretrained(
        config["hf_id"],
        torch_dtype=torch.bfloat16,
        device_map="auto",
        cache_dir=f"{hf_home}/hub",
    )

    # Load LoRA adapter on top of base model
    print("  Loading LoRA adapter...")
    model = PeftModel.from_pretrained(base_model, str(adapter_dir))

    # Merge: W_merged = W_base + B×A×(alpha/r)
    print("  Merging adapter weights into base model...")
    model = model.merge_and_unload()

    # Save merged model
    merged_dir.mkdir(parents=True, exist_ok=True)
    print(f"  Saving merged model to {merged_dir}...")
    model.save_pretrained(str(merged_dir), safe_serialization=True)

    # Copy tokenizer
    tokenizer = AutoTokenizer.from_pretrained(
        config["hf_id"], cache_dir=f"{hf_home}/hub"
    )
    tokenizer.save_pretrained(str(merged_dir))

    print(f"  Done. Merged model saved.")
    return merged_dir


def main():
    parser = argparse.ArgumentParser(
        description="Merge LoRA adapters into base model for vLLM loading."
    )
    parser.add_argument("--model", required=True, choices=list(MODEL_CONFIG.keys()))
    parser.add_argument(
        "--seed", type=int, nargs="+", default=None,
        help="Seed(s) to merge. Default: all available seeds.",
    )
    args = parser.parse_args()

    os.environ["HF_HOME"] = "/workspace/.hf_home"

    seeds = args.seed
    if seeds is None:
        # Auto-discover available seeds
        adapters_dir = ROOT / "adapters" / args.model
        seeds = sorted([
            int(d.name.split("_")[1])
            for d in adapters_dir.iterdir()
            if d.is_dir() and d.name.startswith("seed_")
            and not d.name.endswith("_merged")
        ])
        print(f"Found seeds: {seeds}")

    for seed in seeds:
        merge_seed(args.model, seed)

    print(f"\nAll merges complete for {args.model}.")
    print("Merged models are in adapters/{model}/seed_*_merged/")
    print("Next step: python3 tasks/steering_awareness.py --model qwen")


if __name__ == "__main__":
    main()
