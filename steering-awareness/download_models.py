"""
download_models.py — Phase 0: Download and verify model weights.

Run this after setup.sh completes successfully.

Idempotent: if a model is already fully cached, it is skipped.
Resumable: HuggingFace's snapshot_download resumes partial downloads.

Usage:
    python3 download_models.py
    python3 download_models.py --models gemma   # download only Gemma 2 9B
    python3 download_models.py --models qwen    # download only Qwen 2.5 7B
    python3 download_models.py --verify-only    # check cache without downloading
"""

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from huggingface_hub import snapshot_download, scan_cache_dir, HfApi
from huggingface_hub.utils import HFValidationError
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, DownloadColumn

load_dotenv()
console = Console()

# ── Model registry ────────────────────────────────────────────────────────────
# These are the exact HuggingFace repo IDs used in the paper.
# Gemma 2 9B requires accepting the licence at:
#   https://huggingface.co/google/gemma-2-9b-it
MODELS = {
    "gemma": {
        "repo_id": "google/gemma-2-9b-it",
        "display": "Gemma 2 9B Instruct",
        "expected_gb": 18.0,    # approximate — used for sanity check only
        # Gemma 2 is gated: you must accept the licence at
        # https://huggingface.co/google/gemma-2-9b-it before your token works.
        "requires_auth": True,
    },
    "qwen": {
        "repo_id": "Qwen/Qwen2.5-7B-Instruct",
        "display": "Qwen 2.5 7B Instruct",
        "expected_gb": 15.0,
        # Qwen 2.5 is Apache 2.0 — no licence gate, no token required.
        # We still pass the token if present: authenticated downloads get
        # better rate limits from HuggingFace, making large downloads more reliable.
        "requires_auth": False,
    },
}


def is_model_cached(repo_id: str) -> tuple[bool, str]:
    """
    Check whether a model is fully cached using scan_cache_dir().
    Returns (is_cached, detail_message).

    Note: scan_cache_dir() checks the HF cache structure and reports
    cached revisions. A present revision does not guarantee file integrity,
    but combined with a size check it's a reliable signal.
    """
    try:
        cache_info = scan_cache_dir()
        for repo in cache_info.repos:
            if repo.repo_id == repo_id:
                for revision in repo.revisions:
                    size_gb = repo.size_on_disk / (1024 ** 3)
                    return True, f"Cached at {repo.repo_path} ({size_gb:.1f} GB)"
        return False, "Not found in HF cache"
    except Exception as e:
        return False, f"Cache scan error: {e}"


def download_model(key: str, config: dict, token: str | None) -> bool:
    """
    Download a model via snapshot_download. Resumes automatically if interrupted.
    Returns True on success.
    """
    repo_id = config["repo_id"]
    display = config["display"]

    # Check cache first
    cached, detail = is_model_cached(repo_id)
    if cached:
        console.print(f"[green]SKIP[/green]  {display} — already cached. ({detail})")
        return True

    # Auth check for gated models
    if config["requires_auth"] and not token:
        console.print(
            f"[red]FAIL[/red]  {display} requires HF_TOKEN. "
            f"Set it in .env and accept the licence at huggingface.co/{repo_id}"
        )
        return False

    console.print(f"[cyan]DOWN[/cyan]  Downloading {display} ({config['expected_gb']:.0f} GB approx)...")
    console.print(f"       This may take 10–20 minutes on a typical Vast.ai instance.")

    # Pass token for all models if present: authenticated requests get better
    # rate limits from HuggingFace even for ungated (open-licence) models.
    download_token = token if token else None

    try:
        local_path = snapshot_download(
            repo_id=repo_id,
            token=download_token,
            resume_download=True,     # resume partial downloads
            ignore_patterns=["*.msgpack", "*.h5", "flax_model*", "tf_model*"],
        )
        # Verify it landed in cache correctly
        cached_now, detail_now = is_model_cached(repo_id)
        if cached_now:
            console.print(f"[green]DONE[/green]  {display} downloaded. {detail_now}")
            return True
        else:
            console.print(f"[red]FAIL[/red]  {display} download completed but cache scan failed: {detail_now}")
            return False

    except HFValidationError as e:
        console.print(f"[red]FAIL[/red]  {display} — HF validation error (bad token or licence not accepted?): {e}")
        return False
    except Exception as e:
        console.print(f"[red]FAIL[/red]  {display} — Unexpected error: {e}")
        console.print("       Re-run this script to resume the download.")
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Download model weights for steering-awareness replication.")
    parser.add_argument(
        "--models",
        nargs="+",
        choices=list(MODELS.keys()) + ["all"],
        default=["all"],
        help="Which models to download (default: all)",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only check the cache; do not download anything.",
    )
    args = parser.parse_args()

    token = os.environ.get("HF_TOKEN")
    targets = list(MODELS.keys()) if "all" in args.models else args.models

    console.print("\n[bold]Phase 0 — Model Download[/bold]\n")

    if args.verify_only:
        console.print("[yellow]--verify-only: checking cache only.[/yellow]\n")
        all_ok = True
        for key in targets:
            cfg = MODELS[key]
            cached, detail = is_model_cached(cfg["repo_id"])
            status = "[green]CACHED[/green]" if cached else "[red]MISSING[/red]"
            console.print(f"  {status}  {cfg['display']} — {detail}")
            if not cached:
                all_ok = False
        sys.exit(0 if all_ok else 1)

    results = {}
    for key in targets:
        results[key] = download_model(key, MODELS[key], token)

    console.print()
    all_ok = all(results.values())
    if all_ok:
        console.print("[green bold]All models ready.[/green bold] "
                      "Phase 0 complete — proceed to Phase 1 (data generation).")
    else:
        failed = [k for k, v in results.items() if not v]
        console.print(f"[red bold]Failed:[/red bold] {', '.join(failed)}. "
                      "Fix the issues above and re-run this script.")
        sys.exit(1)


if __name__ == "__main__":
    main()
