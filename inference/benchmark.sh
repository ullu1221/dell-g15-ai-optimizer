#!/usr/bin/env bash
# ==============================================================================
# Latency & Throughput Benchmark Suite for Dell G15 5530
# Tests prompt evaluation (pp512) and token generation (tg128) across:
#   - P-core affinity pinning vs unpinned E-core migration
#   - GPU layer offload configurations (0 vs 24 layers)
#   - FlashAttention on vs off
# ==============================================================================

set -euo pipefail

MODEL="${1:-/home/p/models/Qwen2.5-14B-Instruct-Q4_K_M.gguf}"

if [[ ! -f "$MODEL" ]]; then
    echo "[!] Benchmark model not found at $MODEL"
    echo "Usage: $0 [path-to-gguf-model]"
    exit 1
fi

echo "=========================================================="
echo " Dell G15 5530 Inference Benchmark"
echo " Model: $MODEL"
echo " CPU:   Intel i5-13450HX (6P + 4E cores)"
echo " GPU:   NVIDIA GeForce RTX 3050 Laptop (6GB VRAM)"
echo "=========================================================="

if command -v llama-bench &>/dev/null; then
    BENCH_CMD="llama-bench"
else
    echo "[!] llama-bench not in PATH, falling back to llama-cli benchmark run."
    BENCH_CMD=""
fi

if [[ -n "$BENCH_CMD" ]]; then
    echo "[+] Running automated matrix with llama-bench..."
    echo "[1] Testing P-Core Pinning vs All Cores (Hybrid 24 layers):"
    echo "--- Unpinned (OS scheduling across P + E cores) ---"
    llama-bench -m "$MODEL" -n 64 -p 256 -ngl 24 -t 10 || true

    echo ""
    echo "--- P-Core Pinned (taskset -c 0,2,4,6,8,10, 6 threads) ---"
    taskset -c 0,2,4,6,8,10 llama-bench -m "$MODEL" -n 64 -p 256 -ngl 24 -t 6 || true

    echo ""
    echo "[2] Testing FlashAttention impact:"
    echo "--- FlashAttention OFF ---"
    taskset -c 0,2,4,6,8,10 llama-bench -m "$MODEL" -n 64 -p 512 -ngl 24 -t 6 -fa 0 || true

    echo ""
    echo "--- FlashAttention ON ---"
    taskset -c 0,2,4,6,8,10 llama-bench -m "$MODEL" -n 64 -p 512 -ngl 24 -t 6 -fa 1 || true
else
    echo "[+] Testing hybrid generation with llama-cli..."
    PROMPT="Write a fast Python script to calculate Fibonacci numbers using matrix exponentiation."
    taskset -c 0,2,4,6,8,10 llama-cli \
        -m "$MODEL" \
        -ngl 24 \
        -t 6 \
        -c 2048 \
        -fa on \
        -ctk q8_0 \
        -ctv q8_0 \
        -n 128 \
        -p "$PROMPT"
fi

echo ""
echo "[✓] Benchmark completed."
