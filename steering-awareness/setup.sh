#!/usr/bin/env bash
# =============================================================================
# setup.sh — Phase 0: Install dependencies and verify the environment.
#
# Usage:
#   bash setup.sh           # full install + verify
#   bash setup.sh --verify-only  # skip installs, just run verify.py
#
# Fails fast: any non-zero exit code halts the script immediately.
# Idempotent: safe to re-run; already-installed packages are skipped by pip.
#
# Does NOT download models — run download_models.py separately after this.
# =============================================================================

set -euo pipefail   # -e: exit on error  -u: error on unset vars  -o pipefail

# ── Colour helpers ────────────────────────────────────────────────────────────

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()    { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
die()     { echo -e "${RED}[FAIL]${NC}  $*" >&2; exit 1; }

# ── Parse arguments ───────────────────────────────────────────────────────────
VERIFY_ONLY=false
for arg in "$@"; do
  case $arg in
    --verify-only) VERIFY_ONLY=true ;;
    *) die "Unknown argument: $arg" ;;
  esac
done

# ── Step 0: Create directory structure ───────────────────────────────────────
# Do this first so later steps can write logs/artifacts even if they fail.
info "Creating project directories..."
python3 setup_dirs.py || die "setup_dirs.py failed."

# ── Step 1: Confirm Python version ───────────────────────────────────────────
info "Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

if [ "$PYTHON_MAJOR" -ne 3 ]; then
  die "Python 3.x required, found $PYTHON_VERSION."
fi
if [ "$PYTHON_MINOR" -lt 10 ]; then
  die "Python 3.10+ required, found $PYTHON_VERSION."
fi
# Warn on 3.13+ — some deps may not have wheels yet, but 3.10/3.11/3.12 are all fine.
if [ "$PYTHON_MINOR" -ge 13 ]; then
  warn "Python $PYTHON_VERSION is very new. Some packages may lack wheels. Proceeding."
fi
info "Python $PYTHON_VERSION ✓"

# ── Step 2: Confirm CUDA driver ───────────────────────────────────────────────
info "Checking CUDA driver..."
if ! command -v nvidia-smi &>/dev/null; then
  die "nvidia-smi not found. Is the NVIDIA driver installed?"
fi
CUDA_DRIVER=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader | head -1)
info "NVIDIA driver: $CUDA_DRIVER ✓"

# Report GPU model and available VRAM — useful for spotting wrong instance type
GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader | head -1)
GPU_MEM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader | head -1)
info "GPU: $GPU_NAME | VRAM: $GPU_MEM"

# Warn if this doesn't look like an H100
if echo "$GPU_NAME" | grep -v -q "H100"; then
  warn "Expected H100, found '$GPU_NAME'. Proceed with caution — memory estimates assume 80GB VRAM."
fi

# Warn if CUDA version is outside the tested range (12.x is the target)
CUDA_VERSION=$(nvidia-smi | grep "CUDA Version" | awk '{print $NF}')
info "CUDA Version (driver): $CUDA_VERSION"
# Use awk for numeric comparison to avoid bash [[ ]] portability issues
CUDA_MAJOR=$(echo "$CUDA_VERSION" | cut -d. -f1)
if [ "$CUDA_MAJOR" -lt 12 ]; then
  die "CUDA 12.x required for vLLM compatibility. Found CUDA $CUDA_VERSION."
fi
if [ "$CUDA_MAJOR" -gt 12 ]; then
  warn "CUDA $CUDA_VERSION is newer than the tested range (12.x). vLLM may not have a compiled wheel for this version."
fi

# ── Step 3: Install dependencies ─────────────────────────────────────────────
if [[ "$VERIFY_ONLY" == false ]]; then
  info "Installing dependencies from requirements.txt..."

  # Install the CUDA 12.1 PyTorch wheel explicitly first.
  # pip install from requirements.txt would pick the CPU wheel without this.
  info "Installing PyTorch 2.4.0 (CUDA 12.1 wheel)..."
  pip install --quiet \
    torch==2.4.0 torchvision==0.19.0 torchaudio==2.4.0 \
    --index-url https://download.pytorch.org/whl/cu121 \
    || die "PyTorch installation failed."

  # Install everything else from requirements.txt
  # Note: torch is already installed above from the CUDA wheel index.
  # We exclude it here to avoid pip trying to resolve it from PyPI.
  info "Installing remaining dependencies..."
  pip install --quiet -r requirements.txt \
    || die "Dependency installation failed. Check requirements.txt."

  info "All packages installed ✓"
else
  info "--verify-only: skipping installation."
fi

# ── Step 4: Run smoke tests ───────────────────────────────────────────────────
info "Running smoke tests (verify.py)..."
python3 verify.py || die "Smoke tests failed. Fix the issues above before proceeding."

info "============================================================"
info "Phase 0 complete. Environment is ready."
info "Next step: python3 download_models.py"
info "============================================================"
