#!/usr/bin/env bash
# ==============================================================================
# One-Click Setup & Deployment Script for Dell G15 AI Optimizer
# ==============================================================================

set -euo pipefail

echo "=========================================================="
echo " Dell G15 5530 AI Environment Setup"
echo "=========================================================="

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 1. Check executable permissions
echo "[+] Ensuring script executable permissions..."
chmod +x "$REPO_DIR"/system/*.sh || true
chmod +x "$REPO_DIR"/inference/*.sh || true
chmod +x "$REPO_DIR"/inference/*.py || true
chmod +x "$REPO_DIR"/vllm/*.sh || true
chmod +x "$REPO_DIR"/vllm/*.py || true
chmod +x "$REPO_DIR"/diagnostics/*.py || true
chmod +x "$REPO_DIR"/apps/weather-dashboard/*.py || true

# 2. Run diagnostics
echo "[+] Inspecting hardware configuration..."
python3 "$REPO_DIR"/diagnostics/inspect_hardware.py

# 3. Create model directory
MODELS_DIR="$HOME/models"
if [[ ! -d "$MODELS_DIR" ]]; then
    echo "[+] Creating models directory at $MODELS_DIR..."
    mkdir -p "$MODELS_DIR"
fi

echo ""
echo "=========================================================="
echo " Setup Complete!"
echo " Quick Actions:"
echo "   1. Tune hardware:   sudo $REPO_DIR/system/tune_system.sh"
echo "   2. Download model:  python3 $REPO_DIR/inference/download_gguf.py --preset qwen14b"
echo "   3. Run hybrid LLM:  $REPO_DIR/inference/run_hybrid.sh"
echo "   4. Launch weather:  python3 $REPO_DIR/apps/weather-dashboard/server.py"
echo "=========================================================="
