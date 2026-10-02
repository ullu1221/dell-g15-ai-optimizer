#!/usr/bin/env bash
# ==============================================================================
# Ultra-Low VRAM vLLM Launcher for NVIDIA RTX 3050 6GB Laptop GPU
# ==============================================================================
# Critical 6GB Constraints & Solutions:
#   1. Marlin Weight Unpack Spike:
#      Loading 7B AWQ models with Marlin triggers a 420 MiB temporary unpacking
#      buffer in auto_awq.py. On a 5.72 GiB usable VRAM budget, this hits OOM.
#      SOLUTION: --cpu-offload-gb 2 offloads linear modules to host RAM during
#      initialization and drops active model weights to ~2.88 GiB VRAM.
#   2. CUDA Graph Overhead:
#      Pre-capturing CUDA graphs consumes ~1.2 GiB static VRAM on small GPUs.
#      SOLUTION: --enforce-eager runs in eager execution, reclaiming this VRAM
#      for the KV cache block pool.
#   3. FlashInfer Header Failures:
#      Torch JIT compile for FlashInfer sampler often fails when CUDA headers are
#      desynchronized.
#      SOLUTION: VLLM_USE_FLASHINFER_SAMPLER=0 uses the robust PyTorch native sampler.
#   4. PyTorch Memory Fragmentation:
#      SOLUTION: PYTORCH_CUDA_ALLOC_CONF="expandable_segments:True" allows PyTorch
#      to dynamically grow memory segments rather than throwing out-of-memory.
# ==============================================================================

set -euo pipefail

MODEL="${1:-Qwen/Qwen2.5-Coder-7B-Instruct-AWQ}"
PORT="${PORT:-8000}"
HOST="${HOST:-0.0.0.0}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-4096}"
GPU_UTIL="${GPU_UTIL:-0.90}"
CPU_OFFLOAD="${CPU_OFFLOAD:-2}"

# Environment tuning for 6GB VRAM stability
export CUDA_VISIBLE_DEVICES="0"
export PYTORCH_CUDA_ALLOC_CONF="expandable_segments:True"
export VLLM_USE_FLASHINFER_SAMPLER="0"
export VLLM_LOGGING_LEVEL="INFO"

echo "=========================================================="
echo " Starting vLLM Engine (6GB VRAM Budget Profile)"
echo " Model:             $MODEL"
echo " Quantization:      awq_marlin"
echo " CPU Offload:       ${CPU_OFFLOAD} GB"
echo " Execution Mode:    --enforce-eager"
echo " GPU Memory Util:   $GPU_UTIL"
echo " Max Context Len:   $MAX_MODEL_LEN"
echo " Endpoint:          http://${HOST}:${PORT}/v1"
echo "=========================================================="

exec python3 -m vllm.entrypoints.openai.api_server \
    --model "$MODEL" \
    --quantization awq_marlin \
    --cpu-offload-gb "$CPU_OFFLOAD" \
    --enforce-eager \
    --gpu-memory-utilization "$GPU_UTIL" \
    --max-model-len "$MAX_MODEL_LEN" \
    --host "$HOST" \
    --port "$PORT"
