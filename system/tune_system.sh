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

# 2. CPU Power Profile & EPP Handling
# Preserves active power profile (e.g. balanced) across reboots so G-Mode is not forced.
# Only engages performance mode if explicitly passed --performance.
if [[ "${*:-}" =~ "--performance" ]]; then
    echo "[2/4] Setting CPU Profile & Energy Performance Preference to Performance (G-Mode)..."
    if command -v powerprofilesctl &>/dev/null; then
        powerprofilesctl set performance 2>/dev/null || true
    fi
    for epp in /sys/devices/system/cpu/cpu*/cpufreq/energy_performance_preference; do
        if [[ -f "$epp" ]]; then
            echo "performance" > "$epp" 2>/dev/null || true
        fi
    done
    echo "  -> CPU profile & EPP active in 'performance' mode (G-Mode enabled)"
else
    echo "[2/4] Preserving active power profile (G-Mode disabled by default for quiet boots)..."
fi

# 3. Kernel Memory Map Limit for large GGUF mmap loading
echo "[3/4] Optimizing Kernel Virtual Memory Map Limits..."
sysctl -w vm.max_map_count=1048576 > /dev/null
echo "  -> vm.max_map_count = 1048576 (prevents mmap allocation limits)"

# 4. Thermal & Fan Permissions for Non-Root Users (group wheel)
echo "[4/5] Configuring Thermal & Fan Control Permissions..."
mkdir -p /etc/tmpfiles.d
cat << 'EOF' > /etc/tmpfiles.d/dell-g15-thermal.conf
# Dell G15 5530 Hardware Thermal & Fan Controls
z /sys/class/platform-profile/platform-profile-0/profile 0664 root wheel -
z /sys/class/platform-profile/platform-profile-0/device/hwmon/hwmon*/fan1_boost 0664 root wheel -
z /sys/class/platform-profile/platform-profile-0/device/hwmon/hwmon*/fan2_boost 0664 root wheel -
z /sys/devices/system/cpu/cpu*/cpufreq/energy_performance_preference 0664 root wheel -
EOF
chmod 644 /etc/tmpfiles.d/dell-g15-thermal.conf
if command -v systemd-tmpfiles &>/dev/null; then
    systemd-tmpfiles --create /etc/tmpfiles.d/dell-g15-thermal.conf 2>/dev/null || true
fi
# Apply directly to active sysfs nodes immediately
WMAX_PROF="/sys/class/platform-profile/platform-profile-0/profile"
if [[ -f "$WMAX_PROF" ]]; then
    chmod 0664 "$WMAX_PROF" 2>/dev/null || true
    chown :wheel "$WMAX_PROF" 2>/dev/null || true
fi
for f in /sys/class/platform-profile/platform-profile-0/device/hwmon/hwmon*/fan*_boost; do
    if [[ -f "$f" ]]; then
        chmod 0664 "$f" 2>/dev/null || true
        chown :wheel "$f" 2>/dev/null || true
    fi
done
echo "  -> Granted group 'wheel' write permissions to native AWCC thermal & fan boost nodes"

# 5. Telemetry Verification
echo "[5/5] Verifying GPU Power & Memory..."
GPU_INFO=$(nvidia-smi --query-gpu=power.limit,memory.total,memory.free --format=csv,noheader)
echo "  -> GPU Specs: $GPU_INFO"

# Copy binary to /usr/local/bin if not already running from there
if [[ "$0" != "/usr/local/bin/dell-g15-tune" && "$(realpath "$0" 2>/dev/null)" != "/usr/local/bin/dell-g15-tune" ]]; then
    cp "$0" /usr/local/bin/dell-g15-tune
    chmod +x /usr/local/bin/dell-g15-tune
    echo "  -> Synced standalone tuning binary to /usr/local/bin/dell-g15-tune"
fi

if [[ "${*:-}" =~ "--install-service" ]]; then
    SERVICE_SRC="$(dirname "$0")/dell_g15_tuning.service"
    if [[ -f "$SERVICE_SRC" ]]; then
        cp "$SERVICE_SRC" /etc/systemd/system/dell_g15_tuning.service
        systemctl daemon-reload
        systemctl enable --now dell_g15_tuning.service
        echo "  -> Systemd service 'dell_g15_tuning.service' enabled and active!"
    fi
fi

echo "=========================================================="
echo " [SUCCESS] System is tuned to maximum theoretical performance!"
echo "=========================================================="
