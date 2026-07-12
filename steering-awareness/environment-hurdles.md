# Environment Hurdles: Steering Awareness Replication

A running log of every non-trivial obstacle encountered during Phase 0
(environment setup) and Phase 2 (CAA vector extraction). Documented for
post-mortem discussion.

---

## Hurdle 1: Vast.ai "Automatic Tag" Image — Wrong CUDA Version

**What happened:**
The default Vast.ai template (`vastai/pytorch:@vastai-automatic-tag`) provisioned
an instance with PyTorch 2.12.0+cu130 and CUDA 13.0. No stable vLLM wheel exists
for CUDA 13.0.

**How we found it:**
Running `python3 --version`, `python3 -c "import torch; print(torch.__version__)"`,
and `nvcc --version` on first SSH login.

**What we tried:**
Switched to the "Cuda 12.1" Vast.ai template.

**Outcome:**
The new instance had CUDA 12.9 toolkit (nvcc) with a CUDA 13.0 driver
(`nvidia-smi`). PyTorch was not pre-installed (bare CUDA image).
This is still workable — CUDA 12.x driver runs CUDA 12.1 compiled wheels.

**Lesson:**
Vast.ai templates do not guarantee a specific CUDA toolkit version. Always
run `nvcc --version` and `nvidia-smi` immediately after provisioning.
The `@vastai-automatic-tag` image should never be used for reproducible ML work.

---

## Hurdle 2: Python Venv Discovery

**What happened:**
The instance has a pre-existing Python venv at `/venv/main/`. All packages are
installed there. After running `source /root/.bashrc` (which the tmux setup
triggered), the shell changed working directory and lost the venv activation,
dropping to the system Python at `/usr/bin/python3` which had no packages.

**Symptom:**
`verify.py` showed everything failing with `No module named 'torch'` after a
successful run minutes earlier.

**Fix:**
Always check `which python3` before running scripts. If it shows `/usr/bin/python3`
instead of `/venv/main/bin/python3`, run:
```bash
source /venv/main/bin/activate
```

**Lesson:**
Vast.ai images use a venv for package isolation. Shell resets (via `source
~/.bashrc`, SSH reconnects, or tmux pane resets) can drop you out of the venv.
Added `source /venv/main/bin/activate` to `.bashrc` to make it permanent.

---

## Hurdle 3: `bitsandbytes` Missing `libnvJitLink.so.13`

**What happened:**
`verify.py` reported `bitsandbytes (4-bit): FAIL` with error:
`libnvJitLink.so.13: cannot open shared object file: No such file or directory`

**Root cause:**
`libnvJitLink.so.13` exists in the Python venv at:
`/venv/main/lib/python3.12/site-packages/nvidia/cu13/lib/`
but is not on `LD_LIBRARY_PATH`.

**Fix:**
```bash
export LD_LIBRARY_PATH=/venv/main/lib/python3.12/site-packages/nvidia/cu13/lib:$LD_LIBRARY_PATH
echo 'export LD_LIBRARY_PATH=/venv/main/lib/python3.12/site-packages/nvidia/cu13/lib:$LD_LIBRARY_PATH' >> /root/.bashrc
```

**Secondary issue discovered:**
Our `verify.py` smoke test ran the bitsandbytes forward pass on CPU, which is
unsupported — 4-bit quantization requires GPU. Fixed the test to call `.cuda()`
on both the layer and input before the forward pass.

---

## Hurdle 4: Inspect AI `list_models` API Changed

**What happened:**
`verify.py` reported `inspect-ai: FAIL` with:
`cannot import name 'list_models' from 'inspect_ai.model'`

**Root cause:**
We pinned against inspect-ai 0.3.0 in our check, but the installed version
(0.3.240) renamed or removed `list_models`.

**Fix:**
Updated `verify.py` to try multiple import paths with fallback, and changed
the check from FAIL to WARN since the library itself works fine — we just
can't programmatically enumerate providers.

---

## Hurdle 5: `requirements.txt` Dependency Conflicts

**What happened:**
`pip install -r requirements.txt` failed with `ResolutionImpossible` due to
pinned versions (`datasets==2.21.0`, `openai==1.40.0`, `torch==2.4.0`)
conflicting with what the venv's newer packages required.

**Root cause:**
We over-pinned packages to their late-2024 versions, but the instance has
late-2025/2026 versions of everything. The newer `transformers` and `inspect-ai`
require newer `datasets` and `openai`.

**Fix:**
Changed all version pins to `>=` lower bounds, letting pip resolve freely.
After installation, we capture the actual resolved versions with `pip freeze >
requirements.lock`.

**Lesson:**
On a bleeding-edge environment, exact pins that worked in development often
conflict. Use lower-bound constraints during initial setup, then lock after
the fact.

---

## Hurdle 6: FlashInfer JIT Compilation Failure — `curand.h` Missing

**What happened:**
vLLM server crashed at startup with:
```
fatal error: curand.h: No such file or directory
```
FlashInfer (vLLM's fast attention/sampling kernel library) tries to JIT-compile
CUDA kernels at startup using Ninja, and needs `curand.h` from the CUDA toolkit.

**Root cause:**
`curand.h` exists at:
`/venv/main/lib/python3.12/site-packages/nvidia/curand/include/curand.h`
but FlashInfer's build system hardcodes `-isystem /usr/local/cuda/include` and
doesn't search the venv.

**Fix attempt 1:** Set `CUDA_HOME` — failed because FlashInfer's Ninja build
file already has the include path baked in.

**Fix attempt 2:** Symlink all `curand` headers into `/usr/local/cuda/include/`:
```bash
for f in /venv/main/lib/python3.12/site-packages/nvidia/curand/include/*.h; do
  ln -sf "$f" /usr/local/cuda/include/$(basename "$f")
done
```
This fixed `curand.h` but revealed a deeper incompatibility.

---

## Hurdle 7: FlashInfer / CUDA Toolkit Version Incompatibility

**What happened:**
After the `curand.h` symlink fix, a new error appeared:
```
#error "CUDA compiler and CUDA toolkit headers are incompatible"
```
FlashInfer 0.6.12's bundled `libcudacxx` headers expect a specific CUDA version
that doesn't match the CUDA 12.9/13.0 toolkit on this image.

**Root cause:**
FlashInfer 0.6.12 was not built for CUDA 13.0. The incompatibility is at the
header level — not fixable with symlinks.

**Fix:**
Disable FlashInfer's JIT-compiled sampling kernels entirely:
```bash
export VLLM_USE_FLASHINFER_SAMPLER=0
```
vLLM falls back to PyTorch's native sampling, which works correctly.
Added to `start_server.sh` and to the extraction script's environment setup.

**Lesson:**
FlashInfer JIT compilation is a common failure point on non-standard CUDA
environments. `VLLM_USE_FLASHINFER_SAMPLER=0` should be a default export in
any setup script targeting non-standard CUDA versions.

---

## Hurdle 8: Inspect AI Manages Its Own vLLM Server

**What happened:**
We started the vLLM server manually with `start_server.sh`, then ran
`extract_caa.py`. Inspect AI ignored our running server and tried to launch
*its own* vLLM server on a random port, which failed because our server was
already using port 8000 and the env vars weren't inherited.

**Root cause:**
The `vllm-lens` Inspect provider is designed to manage the server lifecycle
itself. `get_model("vllm-lens/...")` always starts a fresh server — it is not
designed to connect to an externally managed server.

**Fix:**
- Kill the manually-started server before running extraction
- Set `VLLM_USE_FLASHINFER_SAMPLER=0` inside `extract_caa.py` before calling
  `get_model()` so the env var is inherited by the server Inspect launches

**Implication:**
`start_server.sh` is now only useful for manual testing/debugging. For production
extraction and evaluation, Inspect manages the server lifecycle.

---

## Hurdle 9: `get_model()` Config Parameter Type Mismatch

**What happened:**
```
AttributeError: 'dict' object has no attribute 'model_dump_json'
```

**Root cause:**
We passed `config={"dtype": "bfloat16", ...}` (a plain dict) to `get_model()`.
The function signature requires `config: GenerateConfig | None`, a Pydantic model.
Model-specific vLLM args (`dtype`, `max_model_len`, etc.) belong in `**model_args`,
not in `config`.

**Fix:**
```python
model = get_model(
    "vllm-lens/Qwen/Qwen2.5-7B-Instruct",
    config=GenerateConfig(temperature=0.0),
    dtype="bfloat16",
    max_model_len=512,
    gpu_memory_utilization=0.85,
)
```

---

## Hurdle 10: BFloat16 Tensors Not Supported by NumPy

**What happened:**
```
ERROR extracting 'hammer' (id=0): Got unsupported ScalarType BFloat16
```
Every concept failed with this error.

**Root cause:**
The vLLM-Lens server returns activations as `bfloat16` PyTorch tensors
(matching the model's dtype). We called `.cpu().numpy()` directly, but NumPy
does not support the bfloat16 dtype.

**Fix:**
Cast to float32 before converting to NumPy:
```python
return layer_acts[-1].to(dtype=torch.float32).cpu().numpy()
```

---

## Hurdle 11: Spot Instance Preemption — Data Loss

**What happened:**
Training was running at epoch 1/4, step 2090/3073 (~68% through epoch 1) when
the spot instance was outbid. SSH connection dropped. The instance was
deallocated before data could be rescued. All work on the instance was lost:
- 500 extracted CAA vectors (~7MB, 26 minutes of GPU time)
- Partial training run (no adapter saved — training script only saves at end of
  each epoch, and epoch 1 had not completed)

**Root causes:**
1. Spot pricing: cheaper but preemptible at any time with no warning
2. No epoch-level checkpointing: the training script saved adapters only after
   full epoch completion, so a mid-epoch interruption loses everything
3. No local backup of generated artifacts before starting long jobs

**Fixes applied:**
1. Added per-epoch checkpoint saving to `train_lora.py` — adapter saved after
   each epoch, so maximum loss is one epoch of compute
2. Use `nohup` for all long-running processes so SSH disconnects don't kill jobs
3. Use on-demand instances for training phases (not spot) — ~$2-3/hr vs $1.50/hr
   but cannot be preempted
4. Download critical generated artifacts (vectors, adapters) to local machine
   after each phase before starting the next one

**What was recoverable:**
- All code exists locally — no code was lost
- Dataset files exist locally — no regeneration needed
- Only the CAA vectors and partial training needed to be redone (~30 min total)

**Lesson:**
On spot instances, treat your `/workspace` as ephemeral. Anything that takes
more than 5 minutes to regenerate should be backed up locally immediately after
creation.

## Hurdle 12: Sequential Seed Server Crash

**What happened:**
Evaluating multiple seeds sequentially caused the vLLM server to crash on
seed N+1 with CUDA OOM or context errors, even though each seed should be
independent.

**Root cause:**
The Inspect-AI evaluation loop was not fully clearing the GPU context/state
between server restarts initiated by `get_model()`. Residual VRAM from the
previous run caused the next server instance to fail initialization.

**Fix:**
Run each seed in a separate shell command / process script rather than
looping within one python session. This ensures the environment and GPU
state are strictly cleared by the OS between runs.

---

| # | Hurdle | Root Cause | Fix |
|---|--------|-----------|-----|
| 1 | Wrong CUDA version from auto template | Vast.ai auto-tag uses latest image | Use explicit CUDA 12.x template |
| 2 | Venv lost after shell reset | Vast.ai uses `/venv/main`, not system Python | Add venv activation to `.bashrc` |
| 3 | `libnvJitLink.so.13` not on path | CUDA libs in venv, not `/usr/local/cuda` | Set `LD_LIBRARY_PATH` |
| 4 | `list_models` removed from inspect-ai | API changed between versions | Graceful fallback in verify.py |
| 5 | pip dependency conflicts | Over-pinned versions from 2024 | Use `>=` lower bounds |
| 6 | `curand.h` not found by FlashInfer | Header in venv, not system CUDA path | Symlink headers |
| 7 | FlashInfer/CUDA version incompatibility | FlashInfer 0.6.12 not built for CUDA 13 | `VLLM_USE_FLASHINFER_SAMPLER=0` |
| 8 | Inspect launches its own server | vLLM-Lens manages server lifecycle | Let Inspect manage it, set env vars first |
| 9 | `get_model()` config type error | Passed dict instead of `GenerateConfig` | Use correct Pydantic type |
| 10 | BFloat16 not supported by NumPy | Model returns bf16, NumPy needs fp32 | Cast to float32 before `.numpy()` |
| 11 | Spot instance preemption | Vast.ai spot pricing — preempted mid-training | Per-epoch checkpoints + on-demand instances |
| 12 | Sequential seed eval crash (seed N+1) | GPU memory not fully freed between seeds | Run each seed in a separate command |

---

## Key Observation

Nearly all hurdles stem from one root cause: **the Vast.ai image ships with
CUDA 13.0 / PyTorch 2.11 which is newer than what the ML ecosystem (FlashInfer,
vLLM wheels, our pinned versions) was built for.** If this replication is repeated,
starting from a pinned `pytorch/pytorch:2.4.0-cuda12.1-cudnn9-devel` Docker image
would eliminate hurdles 1, 3, 6, and 7 entirely.

---

## Phase 4 Findings: Identification Rate Analysis (2026-06-19)

After running evaluation on seeds 0 and 1 (Qwen 2.5 7B, keyword judge), the
identification rate of ~27% is significantly below the paper's 71.4% target.
Diagnostic analysis revealed a specific, structured failure mode.

### What Was Found

The model achieved near-perfect detection (DR=99.1%) but low identification.
Breakdowns by category and alpha revealed:

**By alpha:**
| Alpha | DR | IR |
|-------|-----|-----|
| 4.0 | 98.2% | 22.3% |
| 8.0 | 100.0% | 27.1% |
| 16.0 | 99.2% | 34.2% |

**By category:**
| Category | IR |
|---|---|
| Abstract Concepts | 81.0% |
| Temporal Terms | 75.0% |
| Professions | 65.3% |
| Verbs / Technical / Nature | 38–46% |
| Animals | 16.7% |
| European Languages | 5.0% |
| Colors / Food / Spatial / Quantities / Materials / Other Languages / Asian Languages | 0.0% |

**Failure pattern:** The model names the correct *semantic category* but the wrong
*instance* within that category. Example failures:
- Steered with `raccoon` → model says `salamander` (both Animals)
- Steered with `chartreuse` → model says `turquoise` (both Colors)
- Steered with `bunga` (Indonesian "flower") → model says `floare` (Romanian "flower")
- Steered with `infinity` → model says `eternity` (near-synonyms)

### Root Cause

CAA vectors are computed against a **shared neutral baseline** (152 household objects)
for all 500 concepts. Within a tight semantic category (Animals, Colors, Food), the
CAA vectors for different members point in nearly the same direction — they encode
"this is an animal" but not "this is *raccoon* specifically." The LoRA adapter learned
category-level routing but cannot discriminate within-category instances.

Categories with semantically unique members (Abstract Concepts, Temporal Terms,
Professions) achieve IR near the paper's target. Categories with many similar members
(Colors, Food, Languages) achieve ~0%.

### Implications

1. **The paper's 71.4% IR likely required within-category contrastive training or a
   different CAA baseline.** The paper does not describe using per-category baselines,
   but this remains the most plausible explanation.

2. **The finding is scientifically valid and reportable:** The model demonstrates
   category-level awareness (which is itself a meaningful result) but not instance-level
   discrimination for semantically dense categories.

3. **Semantic similarity scoring** recovers near-synonym identifications (e.g.,
   `infinity/eternity`, `reunion/celebration`) and gives a fairer IR estimate.
   See `scorers/semantic_scorer.py`.
