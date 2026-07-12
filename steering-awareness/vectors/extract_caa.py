"""
vectors/extract_caa.py — Phase 2: Extract CAA steering vectors.

For each concept, computes:
    v_c = mean(h_concept_prompts) - mean(h_baseline_prompts)

where h is the residual-stream activation at the target layer,
last prompt token position.

Requires the vLLM-Lens server to be running BEFORE this script is called.
The server is started separately (see start_server.sh).

Usage:
    # Start server first (in a separate terminal or tmux pane):
    bash vectors/start_server.sh gemma   # or qwen

    # Then run extraction:
    python3 vectors/extract_caa.py --model gemma
    python3 vectors/extract_caa.py --model qwen

Idempotent: already-extracted concepts are skipped on restart.
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

import numpy as np
import torch
from tqdm import tqdm

ROOT = Path(__file__).parent.parent

# ── Model configuration ───────────────────────────────────────────────────────
MODEL_CONFIG = {
    "gemma": {
        "hf_id": "google/gemma-2-9b-it",
        "n_layers": 42,
        "hidden_dim": 3584,
        "inject_layer": 28,  # floor(42 * 0.67) = 28
        "inspect_model_id": "vllm-lens/google/gemma-2-9b-it",
    },
    "qwen": {
        "hf_id": "Qwen/Qwen2.5-7B-Instruct",
        "n_layers": 28,
        "hidden_dim": 3584,
        "inject_layer": 19,  # floor(28 * 0.67) = 18.76 → 19
        "inspect_model_id": "vllm-lens/Qwen/Qwen2.5-7B-Instruct",
    },
}

# ── CAA prompt template (paper Section 3.2) ──────────────────────────────────
# Concept prompt: one per concept
CONCEPT_PROMPT = "Tell me about {concept}."

# Baseline words from paper Appendix B.1 (152 neutral household objects)
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


def get_output_dir(model_key: str) -> Path:
    d = ROOT / "vectors" / model_key
    d.mkdir(parents=True, exist_ok=True)
    return d


def vector_path(model_key: str, concept_id: int) -> Path:
    return get_output_dir(model_key) / f"concept_{concept_id:04d}.npy"


def is_extracted(model_key: str, concept_id: int) -> bool:
    return vector_path(model_key, concept_id).exists()


async def get_activation(model, prompt: str, layer: int) -> np.ndarray:
    """
    Run a single prefill-only forward pass and return the residual-stream
    activation at the specified layer, last prompt token position.

    Returns shape: (hidden_dim,)
    """
    from inspect_ai.model import GenerateConfig, ChatMessageUser

    output = await model.generate(
        [ChatMessageUser(content=prompt)],
        config=GenerateConfig(
            temperature=0.0,
            max_tokens=1,  # prefill only — we discard the generated token
            extra_body={
                "extra_args": {
                    "output_residual_stream": [layer],
                },
                "chat_template_kwargs": {"enable_thinking": False},
            },
        ),
    )

    # residual_stream shape: (n_layers_requested, seq_len, hidden_dim)
    # We requested one layer, so index 0. Take the last prompt token: [-1]
    acts = output.metadata["activations"]["residual_stream"]
    # acts is a list of tensors per requested layer
    layer_acts = acts[0]  # shape: (seq_len, hidden_dim)

    # Last prompt token position.
    # Cast to float32 first — NumPy doesn't support bfloat16.
    return layer_acts[-1].to(dtype=torch.float32).cpu().numpy()


async def extract_concept_vector(
    model,
    concept: str,
    layer: int,
    category: str = None,
    all_concepts: list[dict] = None,
    contrastive: bool = False,
) -> np.ndarray:
    """
    Compute CAA vector for a single concept.
    Standard: v_c = mean(h_concept) - mean(h_152_neutral)
    Contrastive: v_c = mean(h_concept) - mean(h_152_neutral + h_other_same_cat)
    """
    concept_prompt = CONCEPT_PROMPT.format(concept=concept)
    
    # Base neutral words
    baseline_prompts = [CONCEPT_PROMPT.format(concept=w) for w in BASELINE_WORDS]
    
    # Add contrastive decoys if requested
    if contrastive and category and all_concepts:
        other_same_cat = [
            c["concept"] for c in all_concepts 
            if c["category"] == category and c["concept"] != concept
        ]
        baseline_prompts.extend([CONCEPT_PROMPT.format(concept=w) for w in other_same_cat])

    # Run concept prompt and all baseline prompts concurrently
    all_prompts = [concept_prompt] + baseline_prompts
    tasks = [get_activation(model, p, layer) for p in all_prompts]
    results = await asyncio.gather(*tasks)

    concept_act = results[0]                          # shape: (hidden_dim,)
    baseline_acts = np.stack(results[1:], axis=0)     # shape: (N, hidden_dim)

    # CAA: mean difference
    v_c = concept_act - baseline_acts.mean(axis=0)

    # Normalize to unit length
    norm = np.linalg.norm(v_c)
    if norm > 0:
        v_c_normalized = v_c / norm
    else:
        v_c_normalized = v_c

    return v_c_normalized



async def run_extraction(model_key: str, dry_run: bool = False, contrastive: bool = False) -> None:
    """Main extraction loop."""
    config = MODEL_CONFIG[model_key]
    layer = config["inject_layer"]

    # Load concept list
    concepts_path = ROOT / "data" / "concepts_flat.jsonl"
    if not concepts_path.exists():
        print("ERROR: data/concepts_flat.jsonl not found. Run build_dataset.py first.")
        sys.exit(1)

    concepts = []
    with open(concepts_path) as f:
        for line in f:
            concepts.append(json.loads(line))

    print(f"Model: {model_key} | Layer: {layer} ({layer}/{config['n_layers']} = "
          f"{layer/config['n_layers']:.0%} depth)")
    print(f"Concepts to extract: {len(concepts)} | Contrastive mode: {contrastive}")

    # Check which are already done
    already_done = sum(1 for c in concepts if is_extracted(model_key, c["concept_id"]))
    remaining = [c for c in concepts if not is_extracted(model_key, c["concept_id"])]
    print(f"Already extracted: {already_done} | Remaining: {len(remaining)}")

    if dry_run:
        print("--dry-run: skipping actual extraction.")
        return

    if not remaining:
        print("All concepts already extracted. Nothing to do.")
        return

    # Connect to vLLM-Lens via Inspect AI.
    # Inspect manages the vLLM server lifecycle — it starts its own server.
    # Pass required env vars so the server inherits our CUDA workarounds.
    import os
    os.environ["VLLM_USE_FLASHINFER_SAMPLER"] = "0"
    os.environ["HF_HOME"] = "/workspace/.hf_home"

    from inspect_ai.model import get_model, GenerateConfig
    print(f"\nStarting vLLM-Lens server ({config['inspect_model_id']})...")
    print("(Inspect manages the server — this takes ~45 seconds to load)")

    # model_args are passed as **kwargs and forwarded to the vLLM provider.
    # GenerateConfig handles generation-time settings like temperature.
    model = get_model(
        config["inspect_model_id"],
        config=GenerateConfig(temperature=0.0),
        dtype="bfloat16",
        max_model_len=512,
        gpu_memory_utilization=0.85,
        download_dir="/workspace/.hf_home/hub",
    )

    # Extract vectors with progress bar, saving incrementally
    out_dir = get_output_dir(model_key)
    print(f"Saving vectors to: {out_dir}\n")

    with tqdm(total=len(remaining), desc="Extracting CAA vectors") as pbar:
        for concept_rec in remaining:
            concept_id = concept_rec["concept_id"]
            concept_word = concept_rec["concept"]
            category = concept_rec.get("category")

            try:
                v_c = await extract_concept_vector(
                    model, 
                    concept_word, 
                    layer,
                    category=category,
                    all_concepts=concepts,
                    contrastive=contrastive,
                )

                # Save immediately (idempotent restart)
                out_path = vector_path(model_key, concept_id)
                np.save(str(out_path), v_c)

            except Exception as e:
                print(f"\nERROR extracting '{concept_word}' (id={concept_id}): {e}")
                print("Skipping and continuing...")

            pbar.set_postfix({"concept": concept_word[:20]})
            pbar.update(1)

    # Final count
    extracted = sum(1 for c in concepts if is_extracted(model_key, c["concept_id"]))
    print(f"\nExtraction complete: {extracted}/{len(concepts)} vectors saved.")

    if extracted < len(concepts):
        missing = [c["concept"] for c in concepts
                   if not is_extracted(model_key, c["concept_id"])]
        print(f"Missing: {missing}")
        print("Re-run to retry failed concepts.")
    else:
        print(f"Next step: python3 training/train_lora.py --model {model_key}")


def main():
    parser = argparse.ArgumentParser(
        description="Extract CAA steering vectors using vLLM-Lens."
    )
    parser.add_argument(
        "--model", required=True, choices=list(MODEL_CONFIG.keys()),
        help="Which model to extract vectors for",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Check what would be extracted without running",
    )
    parser.add_argument(
        "--layer-depth", type=float, default=0.67,
        help="Override injection layer depth fraction (default: 0.67)",
    )
    parser.add_argument(
        "--contrastive", action="store_true",
        help="Use contrastive within-category extraction (better IR)",
    )
    args = parser.parse_args()

    # Override layer if requested
    if args.layer_depth != 0.67:
        cfg = MODEL_CONFIG[args.model]
        override_layer = round(cfg["n_layers"] * args.layer_depth)
        cfg["inject_layer"] = override_layer
        print(f"Layer override: depth={args.layer_depth} → layer {override_layer}")

    asyncio.run(run_extraction(args.model, dry_run=args.dry_run, contrastive=args.contrastive))


if __name__ == "__main__":
    main()
