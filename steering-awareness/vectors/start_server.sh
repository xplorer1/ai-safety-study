#!/usr/bin/env bash
# vectors/start_server.sh — Start the vLLM-Lens inference server.
#
# Usage:
#   bash vectors/start_server.sh gemma
#   bash vectors/start_server.sh qwen
#
# The server must be running before extract_caa.py or any Inspect eval.
# Run this in a separate tmux pane:
#   Ctrl+b c          (new pane)
#   bash vectors/start_server.sh qwen
#   Ctrl+b p          (switch back to previous pane)
#
# To stop the server: Ctrl+C in its pane, or kill the process.

set -euo pipefail

MODEL=${1:-""}
if [ -z "$MODEL" ]; then
  echo "Usage: bash vectors/start_server.sh [gemma|qwen]"
  exit 1
fi

HF_HOME="/workspace/.hf_home"

case "$MODEL" in
  gemma)
    HF_ID="google/gemma-2-9b-it"
    ;;
  qwen)
    HF_ID="Qwen/Qwen2.5-7B-Instruct"
    ;;
  *)
    echo "Unknown model: $MODEL. Use 'gemma' or 'qwen'."
    exit 1
    ;;
esac

echo "[server] Starting vLLM-Lens for $HF_ID"
echo "[server] This will take 2-3 minutes to load the model."
echo "[server] Once you see 'Application startup complete', switch panes and run extract_caa.py"
echo ""

# VLLM_PLUGINS tells vLLM to load the vllm-lens plugin
export VLLM_PLUGINS="vllm_lens"
export HF_HOME="$HF_HOME"

# curand.h is installed inside the Python venv (not /usr/local/cuda).
# Point CUDA_HOME and CPATH there so FlashInfer's JIT compilation finds it.
CURAND_PATH="/venv/main/lib/python3.12/site-packages/nvidia/cu13"
export CUDA_HOME="$CURAND_PATH"
export CPATH="$CURAND_PATH/include:${CPATH:-}"
export LD_LIBRARY_PATH="$CURAND_PATH/lib:/venv/main/lib/python3.12/site-packages/nvidia/nvjitlink/lib:${LD_LIBRARY_PATH:-}"

echo "[server] CUDA_HOME set to $CUDA_HOME"

# Disable FlashInfer's JIT-compiled sampling kernels.
# FlashInfer 0.6.12 is incompatible with CUDA 13 on this image.
# vLLM will fall back to PyTorch's native sampling, which works fine.
export VLLM_USE_FLASHINFER_SAMPLER=0

python3 -m vllm.entrypoints.openai.api_server \
  --model "$HF_ID" \
  --download-dir "$HF_HOME/hub" \
  --dtype bfloat16 \
  --max-model-len 512 \
  --gpu-memory-utilization 0.85 \
  --port 8000 \
  --host 0.0.0.0
