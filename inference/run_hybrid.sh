#!/usr/bin/env bash
# ==============================================================================
# Minimal-Loss Hybrid Inference Launcher for Dell G15 5530
# Hardware: NVIDIA RTX 3050 (6GB VRAM) + Intel i5-13450HX (6 P-cores with AVX-VNNI)
#
# Optimization Highlights:
#   1. Min-P Sampling (--min-p 0.05): Discards noise tokens dynamically relative to top token.
#   2. FlashAttention 2 (-fa on): Tiled attention eliminates O(N^2) VRAM explosion.
#   3. Q8_0 KV Cache (-ctk q8_0 -ctv q8_0): Halves KV cache memory with 99.9% precision.
#   4. P-Core Pinning (taskset -c 0,2,4,6,8,10): Prevents latency spikes from 4 E-cores.
#   5. 8k Context Window (-c 8192): Safely expanded context for large files/chats.
# ==============================================================================

set -euo pipefail

MODEL="${1:-${HOME}/models/Qwen2.5-14B-Instruct-Q4_K_M.gguf}"

if [[ ! -f "$MODEL" ]]; then
    echo "[ERROR] Model file not found: $MODEL"
    echo "Usage: $0 <path-to-model.gguf> [cli|server]"
    exit 1
fi

MODE="${2:-cli}"
NGL="${NGL:-24}"
THREADS="${THREADS:-6}"
CTX="${CTX:-8192}"

# Bind strictly to the 6 physical Performance cores
CPU_AFFINITY="${CPU_AFFINITY:-0,2,4,6,8,10}"

# Pre-flight VRAM headroom check
if command -v nvidia-smi &>/dev/null; then
    FREE_VRAM=$(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits | head -n 1 || echo "6000")
    if [[ "$FREE_VRAM" -lt 4000 ]]; then
        echo "[!] Low free VRAM detected (${FREE_VRAM} MiB available)."
        if command -v ollama &>/dev/null; then
            ACTIVE_OLLAMA=$(ollama ps 2>/dev/null | awk 'NR>1 {print $1}')
            if [[ -n "$ACTIVE_OLLAMA" ]]; then
                echo "[+] Unloading lingering Ollama models to reclaim VRAM: $ACTIVE_OLLAMA"
                for m in $ACTIVE_OLLAMA; do
                    ollama stop "$m" || true
                done
                sleep 2
            fi
        fi
    fi
fi

echo "=========================================================="
echo " Starting Minimal-Loss Hybrid Inference"
echo " Model:       $MODEL"
echo " GPU Layers:  $NGL layers offloaded to VRAM"
echo " CPU Threads: $THREADS threads (Pinned to P-cores: $CPU_AFFINITY)"
echo " Context:     $CTX tokens (Q8_0 KV Cache + FlashAttention)"
echo " Sampling:    Min-P 0.05 | Temp 0.6 | Repeat-Penalty 1.05"
echo " Mode:        $MODE"
echo "=========================================================="

if [[ "$MODE" == "server" ]]; then
    exec taskset -c "$CPU_AFFINITY" llama-server \
        -m "$MODEL" \
        -ngl "$NGL" \
        -t "$THREADS" \
        -c "$CTX" \
        -fa on \
        -ctk q8_0 \
        -ctv q8_0 \
        --host 0.0.0.0 \
        --port 8080
else
    exec taskset -c "$CPU_AFFINITY" llama-cli \
        -m "$MODEL" \
        -ngl "$NGL" \
        -t "$THREADS" \
        -c "$CTX" \
        -fa on \
        -ctk q8_0 \
        -ctv q8_0 \
        --temp 0.6 \
        --min-p 0.05 \
        --repeat-penalty 1.05
fi
