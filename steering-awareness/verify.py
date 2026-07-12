"""
verify.py — Phase 0 smoke tests.

Checks that every critical library is installed at the right version,
that GPU compute actually works, and that vLLM-Lens and Inspect AI are
functional. Exits with code 0 on full pass, non-zero on any failure.

Run directly:  python3 verify.py
Or via:        bash setup.sh --verify-only
"""

import sys
import importlib
from dataclasses import dataclass, field
from typing import Callable

from rich.console import Console
from rich.table import Table
from rich import box

console = Console()

# ── Minimum required versions ─────────────────────────────────────────────────
# Update these if you pin newer versions in requirements.txt.
MIN_VERSIONS: dict[str, tuple[int, ...]] = {
    "torch":            (2, 4, 0),
    "transformers":     (4, 44, 0),
    "peft":             (0, 12, 0),
    "bitsandbytes":     (0, 43, 0),
    "datasets":         (2, 21, 0),
    "inspect_ai":       (0, 3, 0),
    "numpy":            (1, 26, 0),
    "sklearn":          (1, 5, 0),
    "openai":           (1, 40, 0),
}


# ── Result container ──────────────────────────────────────────────────────────
@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str
    warning: bool = False   # True = informational, not a blocker


# ── Individual checks ─────────────────────────────────────────────────────────

def check_python_version() -> CheckResult:
    v = sys.version_info
    ok = (v.major == 3 and v.minor >= 10)
    warning = (v.minor >= 13)  # very new — may have missing wheels
    return CheckResult(
        name="Python 3.10+",
        passed=ok,
        warning=warning,
        detail=f"{v.major}.{v.minor}.{v.micro}"
               + (" (3.13+ — watch for missing wheels)" if warning else ""),
    )


def check_package_version(import_name: str, display_name: str | None = None) -> CheckResult:
    """Import a package and compare its __version__ against MIN_VERSIONS."""
    name = display_name or import_name
    min_v = MIN_VERSIONS.get(import_name, (0,))
    try:
        mod = importlib.import_module(import_name)
        version_str = getattr(mod, "__version__", "unknown")
        # Parse e.g. "2.4.0+cu121" → (2, 4, 0)
        numeric = tuple(
            int(x) for x in version_str.split("+")[0].split(".")
            if x.isdigit()
        )
        ok = numeric >= min_v
        return CheckResult(
            name=name,
            passed=ok,
            detail=f"{version_str} (need ≥ {'.'.join(str(x) for x in min_v)})",
        )
    except ImportError as e:
        return CheckResult(name=name, passed=False, detail=f"ImportError: {e}")


def check_cuda() -> CheckResult:
    """Verify PyTorch can see the GPU and allocate a tensor on it."""
    try:
        import torch
        if not torch.cuda.is_available():
            return CheckResult(
                name="CUDA (torch)",
                passed=False,
                detail="torch.cuda.is_available() returned False",
            )
        # Actually allocate on GPU — catches driver/kernel mismatches
        device = torch.device("cuda:0")
        _ = torch.zeros(1024, 1024, device=device)
        torch.cuda.synchronize()
        gpu_name = torch.cuda.get_device_name(0)
        total_mem_gb = torch.cuda.get_device_properties(0).total_memory / (1024 ** 3)
        return CheckResult(
            name="CUDA (torch)",
            passed=True,
            detail=f"{gpu_name} | {total_mem_gb:.1f} GB VRAM",
        )
    except Exception as e:
        return CheckResult(name="CUDA (torch)", passed=False, detail=str(e))


def check_bitsandbytes() -> CheckResult:
    """
    bitsandbytes 4-bit layers MUST be on GPU — CPU forward pass is not supported.
    Test with .cuda() on both layer and input.
    """
    try:
        import bitsandbytes as bnb
        import torch
        if not torch.cuda.is_available():
            return CheckResult(
                name="bitsandbytes (4-bit)",
                passed=False,
                detail="CUDA not available — cannot test 4-bit forward pass",
            )
        # Move both layer and input to GPU before forward pass
        layer = bnb.nn.Linear4bit(64, 64, bias=False).cuda()
        x = torch.randn(1, 64).cuda()
        _ = layer(x)
        return CheckResult(
            name="bitsandbytes (4-bit)",
            passed=True,
            detail=f"v{bnb.__version__} — 4-bit GPU forward pass OK",
        )
    except Exception as e:
        return CheckResult(
            name="bitsandbytes (4-bit)",
            passed=False,
            detail=f"Forward pass failed: {e}",
        )


def check_vllm_lens() -> CheckResult:
    """
    Import vllm_lens and verify its public API.

    From the installed v1.1.0, the confirmed public API is:
      SteeringVector, decode_activations, deserialize_tensor,
      serialize_activations, serialize_tensor, version

    Note: extract_activations and inject_vector do NOT exist as top-level
    names. Steering is applied via SteeringVector objects passed through
    vLLM's extra_body/extra_args mechanism.
    """
    try:
        import vllm_lens
        public_api = [x for x in dir(vllm_lens) if not x.startswith("_")]
        # Check for the names we actually need based on v1.1.0
        expected = {"SteeringVector", "decode_activations", "serialize_activations"}
        found = set(public_api) & expected
        missing = expected - found
        detail = f"v{getattr(vllm_lens, '__version__', '?')} | "
        detail += f"public attrs: {', '.join(sorted(public_api))}"
        if missing:
            detail += f"\n  ⚠ Expected but not found: {', '.join(sorted(missing))}"
        return CheckResult(
            name="vllm-lens",
            passed=True,
            warning=bool(missing),
            detail=detail,
        )
    except ImportError as e:
        return CheckResult(
            name="vllm-lens",
            passed=False,
            detail=f"ImportError: {e}",
        )


def check_inspect_ai() -> CheckResult:
    """Verify Inspect AI imports and can list model providers."""
    try:
        import inspect_ai
        # Try to discover registered model providers.
        # The API for listing models has changed across versions — try both.
        providers = []
        try:
            from inspect_ai.model import list_models
            providers = list_models()
        except ImportError:
            # Newer inspect-ai versions may use a different API
            try:
                from inspect_ai.model import registry
                providers = list(registry.keys()) if hasattr(registry, 'keys') else []
            except Exception:
                providers = []

        has_vllm_lens = any("vllm" in str(p).lower() for p in providers)
        detail = f"v{inspect_ai.__version__}"
        if has_vllm_lens:
            detail += " | vllm-lens provider registered ✓"
        else:
            detail += " | vllm-lens provider not confirmed (may still work — check manually)"
        return CheckResult(
            name="inspect-ai",
            passed=True,
            warning=not has_vllm_lens,
            detail=detail,
        )
    except Exception as e:
        return CheckResult(name="inspect-ai", passed=False, detail=str(e))


def check_hf_token() -> CheckResult:
    """
    Gemma 2 requires accepting a licence on HuggingFace and using an auth token.
    Verify the token is present in the environment (via .env or shell export).
    """
    import os
    from dotenv import load_dotenv
    load_dotenv()
    token = os.environ.get("HF_TOKEN", "")
    if not token:
        return CheckResult(
            name="HF_TOKEN",
            passed=False,
            detail="Not set. Create a .env file with HF_TOKEN=hf_... "
                   "and accept the Gemma 2 licence at huggingface.co/google/gemma-2-9b-it",
        )
    masked = token[:8] + "..." + token[-4:]
    return CheckResult(name="HF_TOKEN", passed=True, detail=f"Present ({masked})")


# ── Runner ────────────────────────────────────────────────────────────────────

def run_all_checks() -> bool:
    """Run every check, print a rich table, return True if all required checks pass."""

    checks: list[Callable[[], CheckResult]] = [
        check_python_version,
        lambda: check_package_version("torch", "PyTorch"),
        check_cuda,
        check_bitsandbytes,
        lambda: check_package_version("transformers"),
        lambda: check_package_version("peft"),
        lambda: check_package_version("datasets"),
        lambda: check_package_version("numpy"),
        lambda: check_package_version("sklearn", "scikit-learn"),
        lambda: check_package_version("openai"),
        check_vllm_lens,
        check_inspect_ai,
        check_hf_token,
    ]

    results: list[CheckResult] = []
    for check_fn in checks:
        try:
            results.append(check_fn())
        except Exception as e:
            results.append(CheckResult(
                name=check_fn.__name__,
                passed=False,
                detail=f"Unexpected error: {e}",
            ))

    # ── Render table ──────────────────────────────────────────────────────────
    table = Table(
        title="Phase 0 — Environment Verification",
        box=box.ROUNDED,
        show_lines=True,
    )
    table.add_column("Check", style="bold")
    table.add_column("Status", justify="center")
    table.add_column("Detail")

    all_passed = True
    for r in results:
        if r.passed and not r.warning:
            status = "[green]PASS[/green]"
        elif r.passed and r.warning:
            status = "[yellow]WARN[/yellow]"
        else:
            status = "[red]FAIL[/red]"
            all_passed = False
        table.add_row(r.name, status, r.detail)

    console.print(table)

    if all_passed:
        console.print("\n[green bold]All checks passed.[/green bold] "
                      "Run [cyan]python3 download_models.py[/cyan] next.\n")
    else:
        console.print("\n[red bold]One or more checks FAILED.[/red bold] "
                      "Fix the issues above before proceeding.\n")

    return all_passed


if __name__ == "__main__":
    success = run_all_checks()
    sys.exit(0 if success else 1)
