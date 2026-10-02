#!/usr/bin/env bash
# ==============================================================================
# Dell G15 5530 System Hardware Optimizer for Local AI Inference
# Hardware: Intel Core i5-13450HX (10 cores) + NVIDIA RTX 3050 6GB Laptop (95W)
# ==============================================================================

set -euo pipefail

# Check for root / sudo
if [[ $EUID -ne 0 ]]; then
    echo "[INFO] Re-running with sudo permissions..."
    exec sudo "$0" "$@"
fi

echo "=========================================================="
echo " Applying Hardware Optimization for Local LLM Inference"
echo " Target: Dell G15 5530 (Raptor Lake HX + RTX 3050 Mobile)"
echo "=========================================================="

# 1. NVIDIA Persistence Mode
echo "[1/4] Enabling NVIDIA Persistence Mode..."
nvidia-smi -pm 1 > /dev/null
echo "  -> Persistence mode ON (driver context retained in VRAM)"

# 2. Set CPU Scaling Governor to Performance
echo "[2/4] Locking Intel P-Cores & E-Cores to Performance Governor..."
for gov in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
    if [[ -f "$gov" ]]; then
        echo "performance" > "$gov"
    fi
done

# Set Energy Performance Preference (EPP) to performance
for epp in /sys/devices/system/cpu/cpu*/cpufreq/energy_performance_preference; do
    if [[ -f "$epp" ]]; then
        echo "performance" > "$epp" 2>/dev/null || true
    fi
done
echo "  -> CPU scaling governor locked to 'performance' (up to 4.6 GHz turbo)"

# 3. Kernel Memory Map Limit for large GGUF mmap loading
echo "[3/4] Optimizing Kernel Virtual Memory Map Limits..."
sysctl -w vm.max_map_count=1048576 > /dev/null
echo "  -> vm.max_map_count = 1048576 (prevents mmap allocation limits)"

# 4. Telemetry Verification
echo "[4/4] Verifying GPU Power & Memory..."
GPU_INFO=$(nvidia-smi --query-gpu=power.limit,memory.total,memory.free --format=csv,noheader)
echo "  -> GPU Specs: $GPU_INFO"

echo "=========================================================="
echo " [SUCCESS] System is tuned to maximum theoretical performance!"
echo "=========================================================="
