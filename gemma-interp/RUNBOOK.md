# RUNBOOK — Phase -1 Smoke Test (RunPod)

Goal: confirm local Gemma 3 12B produces a **real act/refrain split** under a
documented sampling config, on a clean RunPod image, without burning GPU time.

**Money principle:** the GPU clock starts at **Deploy Pod**, not at top-up. Do
everything possible off the clock; terminate the instant you're done; keep the
model on the persistent network volume so you never re-download. Target cost for
this smoke test: **under $1**.

---

## Phase A — Off the clock (free)

1. Top up ~$20 (no clock starts from topping up). ~13 h of A100 @ $1.50/hr.
2. Gemma license accepted on HuggingFace. Have **HF token** + **OpenAI key** ready to paste.
3. Have all commands below copied locally — paste, don't think, on the clock.
4. Use RunPod **Jupyter terminals** (+ → Terminal). No SSH key, no tmux.

## Phase B — Deploy pod (clock starts)

- GPU: A100 80 GB @ $1.50/hr is fine (only ~24 GB used). A cheaper 48 GB card also works — don't shop for 20 min to save cents.
- ✅ **Start Jupyter notebook** (gives click-to-open terminals).
- **Network volume:** keep it (~60 GB). Model caches here and survives termination = the money-saver.
- Container disk: default is fine (model lives on the volume).

## Phase C — Execute (GPU-bound part)

Open **two** Jupyter terminal tabs.

### Terminal 1 — serve Gemma
```bash
export HF_HOME=/workspace/hf            # cache on PERSISTENT volume
export HUGGING_FACE_HUB_TOKEN=hf_...
export VLLM_USE_FLASHINFER_SAMPLER=0    # insurance vs old FlashInfer Hurdle 7

pip install -q vllm
nohup vllm serve google/gemma-3-12b-it \
  --dtype bfloat16 --max-model-len 8192 --port 8000 --seed 0 \
  > /workspace/vllm.log 2>&1 &
tail -f /workspace/vllm.log             # wait for "Application startup complete"
```
First run downloads ~24 GB to `/workspace/hf` (5–10 min) then loads to VRAM.
`nohup … &` survives terminal/SSH drops (the other reason tmux seemed necessary).

### Terminal 2 — set up the project *while the model downloads* (don't sit idle)
No need to clone `agentic-misalignment` — the eval task ships with the pip package.
Work from a self-contained `gemma-interp/` (clone ai-village once it's pushed, or
recreate it):
```bash
mkdir -p /workspace/gemma-interp/runs
cd /workspace/gemma-interp
pip install -q "inspect-ai" "inspect-evals[agentic_misalignment]"
# place verify_run.py here (clone ai-village, or paste from local gemma-interp/)
```

### Terminal 2 — run the smoke test (once Terminal 1 shows server up)
```bash
export OPENAI_API_KEY=sk-...            # grader
export LOCAL_BASE_URL=http://localhost:8000/v1
export LOCAL_API_KEY=dummy

python -m inspect_ai eval inspect_evals/agentic_misalignment \
  -T scenario=blackmail -T goal_type=explicit -T goal_value=america \
  -T urgency_type=replacement -T grader_model=openai/gpt-4o \
  --model openai-api/local/google/gemma-3-12b-it \
  --epochs 20 \
  --temperature 1.0 --top-p 0.95 --seed 0 \
  --log-dir /workspace/gemma-interp/runs
```

### Verify — three gates
```bash
python verify_run.py runs
```
1. Run completed; no `openai` auth errors mid-run (grader live).
2. `act_rate` strictly between 0 and 1 → **both** act and refrain present (gate 2).
3. generate config shows `temperature=1.0, top_p=0.95, seed=0` — NOT null (gate 3).

Expected wall-clock for Phase C: ~20–30 min (~$0.50–0.75).
**If 45 min in and still fighting the environment, STOP and reassess** — debugging
on a live A100 is the real money leak (cf. the 12 hurdles last time).

## Phase D — Save and kill (controls cost)

1. **Download the new `logs/*.eval` to laptop** (Jupyter file browser → right-click → Download). Persistent volume keeps it too, but get it local (Hurdle 11).
2. **Terminate the pod.** Single most important money step — billed per-second while alive; a forgotten idle pod is how money leaks. Terminate stops GPU billing; network volume persists (cents/day) with Gemma cached.
3. Confirm pod gone from Pods list and balance stopped moving.

---

## Notes / watch-items

- **top_k dropped:** `top_k` isn't native to the OpenAI wire, so it's omitted; `temperature=1.0 + top_p=0.95` is the load-bearing config. Document the deviation.
- **vllm/torch dance:** `pip install vllm` may swap the image's torch — that's OK. If it errors hard (Hurdle 5 territory), fall back to the official `vllm/vllm-openai` Docker image as the pod image.
- **provider syntax drift:** if `openai-api/local/...` errors on model resolution, check the current inspect-ai docs for the OpenAI-compatible provider env mapping (`<NAME>_BASE_URL` / `<NAME>_API_KEY`) — it changed before (Hurdle 4).
- **next session:** redeploy against the same network volume → Gemma already cached → skip the download; only re-`pip install`.

## Success → next step

A real split (gate 2) green-lights the full **100-epoch** run (same command,
`--epochs 100`), then Phase 0 (TransformerLens/nnsight on Gemma 3) and Phase 1
(contrast set + hand-verify labels).
