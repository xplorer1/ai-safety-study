"""
training/train_lora.py — Phase 3: QLoRA detection fine-tuning.

Fine-tunes a LoRA adapter on the detection dataset. During each forward pass,
injects the appropriate CAA steering vector into the residual stream at the
target layer using a PyTorch forward hook. Loss is computed only on assistant
response tokens.

Usage:
    python3 training/train_lora.py --model qwen --seed 0
    python3 training/train_lora.py --model qwen --seed 0 --seed 1 --seed 2  # multiple seeds

Run all 5 seeds sequentially:
    for seed in 0 1 2 3 4; do
        python3 training/train_lora.py --model qwen --seed $seed
    done
"""

import argparse
import json
import os
import random
import sys
from pathlib import Path
from typing import Optional

import numpy as np
import torch
from torch.utils.data import DataLoader, Dataset
from tqdm import tqdm

ROOT = Path(__file__).parent.parent

# ── Model configuration (must match extract_caa.py) ───────────────────────────
MODEL_CONFIG = {
    "gemma": {
        "hf_id": "google/gemma-2-9b-it",
        "n_layers": 42,
        "inject_layer": 28,
        "hidden_dim": 3584,
    },
    "qwen": {
        "hf_id": "Qwen/Qwen2.5-7B-Instruct",
        "n_layers": 28,
        "inject_layer": 19,
        "hidden_dim": 3584,
    },
}

# ── Training hyperparameters (from paper Section 3.3 and Appendix E.1) ────────
LORA_CONFIG = {
    "r": 32,
    "lora_alpha": 64,
    "lora_dropout": 0.05,
    "target_modules": [
        "q_proj", "k_proj", "v_proj", "o_proj",   # attention
        "gate_proj", "up_proj", "down_proj",         # MLP
    ],
    "bias": "none",
    "task_type": "CAUSAL_LM",
}

TRAIN_CONFIG = {
    "num_epochs": 4,
    "learning_rate": 1e-4,
    "lr_scheduler": "cosine",
    "per_device_batch_size": 4,
    "gradient_accumulation_steps": 4,   # effective batch size = 16
    "max_seq_len": 512,
    "bf16": True,
    "warmup_ratio": 0.03,
}

# Injection strengths used in training (must match build_dataset.py)
ALPHAS = [0.5, 1.0, 2.0, 4.0, 8.0, 16.0]


# ── Steering hook ─────────────────────────────────────────────────────────────

class SteeringHook:
    """
    Registers a forward hook on a transformer layer to inject a steering
    vector into the residual stream at the last prompt token position.

    The hook modifies the layer output in-place:
        output[0][:, last_prompt_token_idx, :] += alpha * vector

    Usage:
        hook = SteeringHook(model, layer_idx=19)
        hook.set_vector(vector_tensor, alpha=4.0, last_prompt_idx=7)
        # ... run forward pass ...
        hook.clear()
    """

    def __init__(self, model, layer_idx: int):
        self.vector: Optional[torch.Tensor] = None
        self.alpha: float = 1.0
        self.last_prompt_idx: Optional[int] = None
        self._handle = None

        # Register hook on the target transformer layer
        # Qwen and Gemma both use model.model.layers[i] structure
        target_layer = model.model.layers[layer_idx]
        self._handle = target_layer.register_forward_hook(self._hook_fn)

    def _hook_fn(self, module, input, output):
        """
        Called after the target layer's forward pass.
        output can be:
          - a tuple (residual_tensor, ...) in normal forward
          - a plain Tensor during gradient checkpointing recomputation
        residual shape can be (batch, seq_len, hidden) or (seq_len, hidden).
        """
        if self.vector is None or self.last_prompt_idx is None:
            return output

        # Unwrap output to get the residual tensor
        if isinstance(output, tuple):
            residual = output[0]
            is_tuple = True
        else:
            residual = output
            is_tuple = False

        injection = self.alpha * self.vector.to(residual.device, residual.dtype)

        if residual.dim() == 3:
            # (batch, seq_len, hidden_dim)
            pos = min(self.last_prompt_idx, residual.shape[1] - 1)
            residual[:, pos, :] = residual[:, pos, :] + injection
        elif residual.dim() == 2:
            # (seq_len, hidden_dim) — gradient checkpointing recompute
            pos = min(self.last_prompt_idx, residual.shape[0] - 1)
            residual[pos, :] = residual[pos, :] + injection

        if is_tuple:
            return (residual,) + output[1:]
        else:
            return residual

    def set_vector(self, vector: torch.Tensor, alpha: float, last_prompt_idx: int):
        self.vector = vector
        self.alpha = alpha
        self.last_prompt_idx = last_prompt_idx

    def clear(self):
        """Call before Alpaca replay examples — no injection."""
        self.vector = None
        self.last_prompt_idx = None

    def remove(self):
        """Remove hook entirely (call at end of training)."""
        if self._handle:
            self._handle.remove()


# ── Dataset ───────────────────────────────────────────────────────────────────

class DetectionDataset(Dataset):
    """
    Loads training examples from train.jsonl.
    Handles both introspection examples (with CAA injection) and
    Alpaca replay examples (no injection).
    """

    def __init__(
        self,
        train_path: Path,
        vectors_dir: Path,
        tokenizer,
        max_seq_len: int = 512,
        val_split: float = 0.1,
        split: str = "train",
        seed: int = 42,
    ):
        self.tokenizer = tokenizer
        self.max_seq_len = max_seq_len
        self.vectors_dir = vectors_dir

        # Load all examples
        all_examples = []
        with open(train_path) as f:
            for line in f:
                all_examples.append(json.loads(line))

        # Deterministic train/val split
        rng = random.Random(seed)
        indices = list(range(len(all_examples)))
        rng.shuffle(indices)
        n_val = max(1, int(len(indices) * val_split))
        if split == "val":
            self.examples = [all_examples[i] for i in indices[:n_val]]
        else:
            self.examples = [all_examples[i] for i in indices[n_val:]]

    def __len__(self):
        return len(self.examples)

    def __getitem__(self, idx):
        ex = self.examples[idx]
        return ex

    def load_vector(self, concept_id: int) -> Optional[torch.Tensor]:
        """Load pre-computed CAA vector for a concept."""
        path = self.vectors_dir / f"concept_{concept_id:04d}.npy"
        if not path.exists():
            return None
        arr = np.load(str(path))
        return torch.from_numpy(arr)


def collate_fn(batch, tokenizer, max_seq_len):
    """
    Tokenize a batch of examples and create attention masks and labels.
    Labels are -100 (ignored) for prompt tokens; actual token IDs for
    response tokens only.
    """
    input_ids_list = []
    labels_list = []
    attention_mask_list = []
    metadata_list = []

    for ex in batch:
        prompt = ex["prompt"]
        target = ex["target"] or ""
        condition = ex["condition"]
        concept_id = ex.get("concept_id")
        alpha = ex.get("alpha")

        # Format as chat template
        messages = [
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": target},
        ]

        # Tokenize full sequence
        full_text = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=False,
        )
        full_tokens = tokenizer(
            full_text,
            truncation=True,
            max_length=max_seq_len,
            return_tensors="pt",
        )

        # Find where the assistant response starts
        # Tokenize just the user part to find the boundary
        user_text = tokenizer.apply_chat_template(
            [{"role": "user", "content": prompt}],
            tokenize=False,
            add_generation_prompt=True,  # adds the assistant prompt marker
        )
        user_tokens = tokenizer(
            user_text,
            truncation=True,
            max_length=max_seq_len,
            return_tensors="pt",
        )
        prompt_len = user_tokens["input_ids"].shape[1]

        input_ids = full_tokens["input_ids"].squeeze(0)
        attention_mask = full_tokens["attention_mask"].squeeze(0)

        # Labels: -100 for prompt tokens, actual IDs for response tokens
        labels = input_ids.clone()
        labels[:prompt_len] = -100

        # last_prompt_idx: position in sequence where injection happens
        # = last token of the user prompt (before assistant marker)
        last_prompt_idx = min(prompt_len - 1, max_seq_len - 1)

        input_ids_list.append(input_ids)
        labels_list.append(labels)
        attention_mask_list.append(attention_mask)
        metadata_list.append({
            "condition": condition,
            "concept_id": concept_id,
            "alpha": alpha,
            "last_prompt_idx": last_prompt_idx,
        })

    # Pad to max length in batch
    max_len = max(t.shape[0] for t in input_ids_list)
    pad_id = tokenizer.pad_token_id or tokenizer.eos_token_id

    input_ids_padded = torch.stack([
        torch.nn.functional.pad(t, (0, max_len - t.shape[0]), value=pad_id)
        for t in input_ids_list
    ])
    labels_padded = torch.stack([
        torch.nn.functional.pad(t, (0, max_len - t.shape[0]), value=-100)
        for t in labels_list
    ])
    attention_mask_padded = torch.stack([
        torch.nn.functional.pad(t, (0, max_len - t.shape[0]), value=0)
        for t in attention_mask_list
    ])

    return {
        "input_ids": input_ids_padded,
        "labels": labels_padded,
        "attention_mask": attention_mask_padded,
        "metadata": metadata_list,
    }


# ── Training loop ─────────────────────────────────────────────────────────────

def set_seeds(seed: int):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def train(model_key: str, seed: int, layer_depth: float = 0.67) -> Optional[Path]:
    """Train one LoRA adapter for the specified model and seed."""
    config = MODEL_CONFIG[model_key]
    hf_home = "/workspace/.hf_home"

    # Override injection layer
    inject_layer = round(config["n_layers"] * layer_depth)

    adapter_dir = ROOT / "adapters" / model_key / f"seed_{seed}"
    log_path = ROOT / "logs" / model_key / f"seed_{seed}" / "train_log.json"
    vectors_dir = ROOT / "vectors" / model_key

    # Skip if already trained
    if adapter_dir.exists() and (adapter_dir / "adapter_config.json").exists():
        print(f"Adapter already exists at {adapter_dir}. Skipping.")
        return

    adapter_dir.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    set_seeds(seed)
    print(f"\n{'='*60}")
    print(f"Training {model_key} | seed={seed} | layer={inject_layer}")
    print(f"{'='*60}")

    # ── Load tokenizer ────────────────────────────────────────────────────────
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(
        config["hf_id"],
        cache_dir=f"{hf_home}/hub",
        trust_remote_code=False,
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # ── Load model in 4-bit (QLoRA) ───────────────────────────────────────────
    from transformers import AutoModelForCausalLM, BitsAndBytesConfig
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )
    print(f"Loading {config['hf_id']} in 4-bit...")
    model = AutoModelForCausalLM.from_pretrained(
        config["hf_id"],
        quantization_config=bnb_config,
        device_map="auto",
        cache_dir=f"{hf_home}/hub",
        trust_remote_code=False,
    )
    model.config.use_cache = False  # required for gradient checkpointing

    # ── Apply LoRA ────────────────────────────────────────────────────────────
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)

    # ── Register steering hook BEFORE LoRA wrapping ───────────────────────────
    # Hook must be registered on the base model's layer object.
    # After get_peft_model(), model.model.layers is no longer accessible
    # directly, but the hook persists on the underlying layer object.
    steering_hook = SteeringHook(model, layer_idx=inject_layer)

    lora_config = LoraConfig(**LORA_CONFIG)
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    # ── Load datasets ─────────────────────────────────────────────────────────
    train_path = ROOT / "data" / "train.jsonl"
    train_dataset = DetectionDataset(
        train_path, vectors_dir, tokenizer,
        max_seq_len=TRAIN_CONFIG["max_seq_len"],
        split="train", seed=seed,
    )
    val_dataset = DetectionDataset(
        train_path, vectors_dir, tokenizer,
        max_seq_len=TRAIN_CONFIG["max_seq_len"],
        split="val", seed=seed,
    )
    print(f"Train examples: {len(train_dataset)} | Val examples: {len(val_dataset)}")

    from functools import partial
    collate = partial(collate_fn, tokenizer=tokenizer,
                      max_seq_len=TRAIN_CONFIG["max_seq_len"])

    train_loader = DataLoader(
        train_dataset,
        batch_size=TRAIN_CONFIG["per_device_batch_size"],
        shuffle=True,
        collate_fn=collate,
        num_workers=0,
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=TRAIN_CONFIG["per_device_batch_size"],
        shuffle=False,
        collate_fn=collate,
        num_workers=0,
    )

    # ── Optimizer and scheduler ───────────────────────────────────────────────
    from torch.optim import AdamW
    from transformers import get_cosine_schedule_with_warmup

    optimizer = AdamW(
        [p for p in model.parameters() if p.requires_grad],
        lr=TRAIN_CONFIG["learning_rate"],
        weight_decay=0.0,
    )
    total_steps = (
        len(train_loader) // TRAIN_CONFIG["gradient_accumulation_steps"]
        * TRAIN_CONFIG["num_epochs"]
    )
    warmup_steps = int(total_steps * TRAIN_CONFIG["warmup_ratio"])
    scheduler = get_cosine_schedule_with_warmup(
        optimizer,
        num_warmup_steps=warmup_steps,
        num_training_steps=total_steps,
    )

    # ── Training loop ─────────────────────────────────────────────────────────
    train_log = []
    device = next(model.parameters()).device

    for epoch in range(TRAIN_CONFIG["num_epochs"]):
        model.train()
        epoch_loss = 0.0
        n_batches = 0
        optimizer.zero_grad()

        pbar = tqdm(train_loader, desc=f"Epoch {epoch+1}/{TRAIN_CONFIG['num_epochs']}")

        for step, batch in enumerate(pbar):
            input_ids = batch["input_ids"].to(device)
            labels = batch["labels"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            metadata = batch["metadata"]

            # Process each example individually so the steering hook
            # applies the correct vector for each example.
            # Gradient accumulation across examples maintains the
            # effective batch size of 16.
            batch_loss = 0.0
            for i in range(len(metadata)):
                meta = metadata[i]
                condition = meta["condition"]
                concept_id = meta["concept_id"]
                alpha = meta["alpha"]
                last_prompt_idx = meta["last_prompt_idx"]

                # Set up steering hook for this example
                if condition in ("positive", "mismatch") and concept_id is not None:
                    vector = train_dataset.load_vector(concept_id)
                    if vector is not None:
                        steering_hook.set_vector(vector, float(alpha), last_prompt_idx)
                    else:
                        steering_hook.clear()
                elif condition == "noise":
                    noise = torch.randn(config["hidden_dim"])
                    noise = noise / noise.norm()
                    steering_hook.set_vector(noise, float(alpha or 4.0), last_prompt_idx)
                else:
                    # Clean or Alpaca replay — no injection
                    steering_hook.clear()

                # Single-example forward pass — hook applies correctly
                outputs = model(
                    input_ids=input_ids[i:i+1],
                    attention_mask=attention_mask[i:i+1],
                    labels=labels[i:i+1],
                )
                # Divide by total accumulation steps (batch_size × grad_accum)
                loss = outputs.loss / (
                    TRAIN_CONFIG["per_device_batch_size"]
                    * TRAIN_CONFIG["gradient_accumulation_steps"]
                )
                loss.backward()
                batch_loss += outputs.loss.item()

            epoch_loss += batch_loss / len(metadata)
            n_batches += 1

            if (step + 1) % TRAIN_CONFIG["gradient_accumulation_steps"] == 0:
                torch.nn.utils.clip_grad_norm_(
                    [p for p in model.parameters() if p.requires_grad],
                    max_norm=1.0,
                )
                optimizer.step()
                scheduler.step()
                optimizer.zero_grad()

            pbar.set_postfix({"loss": f"{epoch_loss/n_batches:.4f}"})

        # ── Validation loss ───────────────────────────────────────────────────
        model.eval()
        val_loss = 0.0
        n_val_batches = 0
        steering_hook.clear()

        with torch.no_grad():
            for batch in val_loader:
                input_ids = batch["input_ids"].to(device)
                labels = batch["labels"].to(device)
                attention_mask = batch["attention_mask"].to(device)
                outputs = model(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    labels=labels,
                )
                val_loss += outputs.loss.item()
                n_val_batches += 1

        avg_train_loss = epoch_loss / max(n_batches, 1)
        avg_val_loss = val_loss / max(n_val_batches, 1)
        current_lr = scheduler.get_last_lr()[0]

        log_entry = {
            "epoch": epoch + 1,
            "train_loss": avg_train_loss,
            "val_loss": avg_val_loss,
            "lr": current_lr,
        }
        train_log.append(log_entry)
        print(f"\nEpoch {epoch+1}: train_loss={avg_train_loss:.4f} "
              f"val_loss={avg_val_loss:.4f} lr={current_lr:.2e}")

        # Save epoch checkpoint (allows restart from last completed epoch)
        epoch_dir = adapter_dir / f"epoch_{epoch+1}"
        epoch_dir.mkdir(exist_ok=True)
        model.save_pretrained(str(epoch_dir))

        # Save log after each epoch
        with open(log_path, "w") as f:
            json.dump(train_log, f, indent=2)

    # ── Save adapter ──────────────────────────────────────────────────────────
    steering_hook.remove()
    print(f"\nSaving adapter to {adapter_dir}...")
    model.save_pretrained(str(adapter_dir))
    tokenizer.save_pretrained(str(adapter_dir))
    print(f"Done. Adapter saved.")

    return adapter_dir


def main():
    parser = argparse.ArgumentParser(
        description="QLoRA detection fine-tuning for steering awareness."
    )
    parser.add_argument(
        "--model", required=True, choices=list(MODEL_CONFIG.keys()),
        help="Which model to train",
    )
    parser.add_argument(
        "--seed", type=int, nargs="+", default=[0, 1, 2, 3, 4],
        help="Seed(s) to train. Default: all 5 seeds.",
    )
    parser.add_argument(
        "--layer-depth", type=float, default=0.67,
        help="Override injection layer depth fraction (for ablations)",
    )
    args = parser.parse_args()

    os.environ["HF_HOME"] = "/workspace/.hf_home"
    
    # Store override globally so train() uses it if needed,
    # but actual injection depth doesn't matter for *training* 
    # except saving in a different directory if we want to isolate ablations.
    # We will just pass it to track ablations.
    
    for seed in args.seed:
        train(args.model, seed, layer_depth=args.layer_depth)

    print(f"\nAll seeds complete for {args.model}.")
    print(f"Next step: python3 tasks/steering_awareness.py --model {args.model}")


if __name__ == "__main__":
    main()
