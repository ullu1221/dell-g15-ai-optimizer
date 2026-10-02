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
chmod +x "$REPO_DIR"/g15 || true
chmod +x "$REPO_DIR"/system/*.sh || true
chmod +x "$REPO_DIR"/inference/*.sh || true
chmod +x "$REPO_DIR"/inference/*.py || true
chmod +x "$REPO_DIR"/vllm/*.sh || true
chmod +x "$REPO_DIR"/vllm/*.py || true
chmod +x "$REPO_DIR"/diagnostics/*.py || true
chmod +x "$REPO_DIR"/tests/*.sh || true
chmod +x "$REPO_DIR"/tests/*.py || true

# 2. Link g15 CLI globally if permissions permit
if [[ -w /usr/local/bin ]]; then
    ln -sf "$REPO_DIR/g15" /usr/local/bin/g15
    echo "[+] Symlinked unified CLI to /usr/local/bin/g15"
elif command -v sudo &>/dev/null; then
    sudo ln -sf "$REPO_DIR/g15" /usr/local/bin/g15 2>/dev/null || true
fi

# 3. Create model directory
MODELS_DIR="$HOME/models"
if [[ ! -d "$MODELS_DIR" ]]; then
    echo "[+] Creating models directory at $MODELS_DIR..."
    mkdir -p "$MODELS_DIR"
fi

# 4. Run unified status
"$REPO_DIR"/g15 status

echo ""
echo "=========================================================="
echo " Setup Complete! Unified CLI 'g15' is ready."
echo " Quick Actions:"
echo "   g15 chat coder      # Start high-speed coding assistant"
echo "   g15 chat reasoner   # Start 14B hybrid reasoner (P-core pinned)"
echo "   g15 serve           # Launch OpenAI API server on port 8080"
echo "   g15 status          # View real-time thermals & VRAM headroom"
echo "   g15 free            # Reclaim GPU VRAM instantly"
echo "   g15 verify          # Run complete 13-test verification suite"
echo "=========================================================="
