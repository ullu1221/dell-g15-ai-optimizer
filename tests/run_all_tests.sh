#!/usr/bin/env bash
# ==============================================================================
# Complete Test Runner for Dell G15 5530 AI Suite
# Executes syntax checks, hardware diagnostics, and functional accuracy tests.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

echo "=========================================================="
echo " Running Dell G15 5530 AI Suite Full Verification"
echo "=========================================================="

# 1. Syntax Verification
echo "[1/3] Verifying Python & Bash syntax across all files..."
python3 -m py_compile \
    "$REPO_DIR"/g15 \
    "$REPO_DIR"/diagnostics/inspect_hardware.py \
    "$REPO_DIR"/inference/download_gguf.py \
    "$REPO_DIR"/inference/torture_test.py \
    "$REPO_DIR"/vllm/download_awq.py \
    "$REPO_DIR"/vllm/test_client.py \
    "$SCRIPT_DIR"/production_death_loop_test.py \
    "$SCRIPT_DIR"/test_functional.py

bash -n "$REPO_DIR"/setup.sh
bash -n "$REPO_DIR"/system/tune_system.sh
bash -n "$REPO_DIR"/inference/run_hybrid.sh
bash -n "$REPO_DIR"/inference/benchmark.sh
bash -n "$REPO_DIR"/vllm/serve_vllm.sh
echo "  -> Syntax: 100% Valid."

# 2. Hardware Diagnostics Check
echo "[2/3] Verifying hardware diagnostic integrity..."
python3 "$REPO_DIR"/diagnostics/inspect_hardware.py > /dev/null
echo "  -> Diagnostics: 100% Functional."

# 3. Functional & Accuracy Test Suite
echo "[3/3] Launching Functional & Accuracy Test Suite..."
python3 "$SCRIPT_DIR"/test_functional.py

echo ""
echo "=========================================================="
echo " [VERIFICATION COMPLETE] All tests passed with zero defects!"
echo "=========================================================="
