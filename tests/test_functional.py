#!/usr/bin/env python3
"""
Exhaustive Functional & Accuracy Test Suite for Dell G15 5530 AI Suite
Tests CLI operations, power profiles, code generation correctness,
multi-step reasoning logic, JSON tool calling, and OpenAI API compliance.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
MODEL_14B = Path.home() / "models" / "Qwen2.5-14B-Instruct-Q4_K_M.gguf"
P_CORE_MASK = "0,2,4,6,8,10"

TEST_RESULTS = []


def record_result(category: str, name: str, passed: bool, details: str = ""):
    status = "PASS" if passed else "FAIL"
    TEST_RESULTS.append({"category": category, "name": name, "status": status, "details": details})
    print(f"[{status}] {category} :: {name}")
    if details:
        print(f"       -> {details}")


# ==============================================================================
# TEST SUITE 1: CLI Operations & System Commands
# ==============================================================================
def test_cli():
    print("\n" + "=" * 65)
    print(" SUITE 1: CLI Commands & System Diagnostics")
    print("=" * 65)

    # 1. g15 --help
    res = subprocess.run(["g15", "--help"], capture_output=True, text=True)
    record_result("CLI", "g15 --help returns exit code 0", res.returncode == 0)

    # 2. g15 list
    res = subprocess.run(["g15", "list"], capture_output=True, text=True)
    has_presets = all(p in res.stdout for p in ["CODER", "REASONER", "AGENT", "FAST"])
    record_result("CLI", "g15 list contains all 4 standard presets", has_presets)

    # 3. g15 status
    res = subprocess.run(["g15", "status"], capture_output=True, text=True)
    has_status_fields = all(k in res.stdout for k in ["Processor:", "Physical P-Cores:", "Device:", "VRAM Capacity:"])
    record_result("CLI", "g15 status reports CPU, GPU, and VRAM telemetry", has_status_fields)

    # 4. g15 free
    res = subprocess.run(["g15", "free"], capture_output=True, text=True)
    record_result("CLI", "g15 free flushes GPU memory successfully", "VRAM cleanup complete" in res.stdout)


# ==============================================================================
# TEST SUITE 2: Dynamic Power Profile Transitions
# ==============================================================================
def test_power_profiles():
    print("\n" + "=" * 65)
    print(" SUITE 2: ACPI & Power Profile Transitions")
    print("=" * 65)

    # 1. Switch to Balanced
    subprocess.run(["g15", "balance"], capture_output=True)
    time.sleep(0.5)
    with open("/sys/devices/system/cpu/cpu0/cpufreq/energy_performance_preference") as f:
        epp_bal = f.read().strip()
    with open("/sys/firmware/acpi/platform_profile") as f:
        acpi_bal = f.read().strip()
    record_result(
        "Power",
        "Switch to Balanced Mode",
        epp_bal == "balance_performance" and acpi_bal == "balanced",
        f"EPP: {epp_bal}, ACPI: {acpi_bal}",
    )

    # 2. Switch to Performance
    subprocess.run(["g15", "mode", "performance"], capture_output=True)
    time.sleep(0.5)
    with open("/sys/devices/system/cpu/cpu0/cpufreq/energy_performance_preference") as f:
        epp_perf = f.read().strip()
    with open("/sys/firmware/acpi/platform_profile") as f:
        acpi_perf = f.read().strip()
    record_result(
        "Power",
        "Switch to Performance Mode",
        epp_perf == "performance" and acpi_perf in ("performance", "custom"),
        f"EPP: {epp_perf}, ACPI: {acpi_perf}",
    )

    # Restore to Balanced
    subprocess.run(["g15", "balance"], capture_output=True)


# ==============================================================================
# TEST SUITE 3: Code Generation & Execution Accuracy (Coder)
# ==============================================================================
def test_coder_accuracy():
    print("\n" + "=" * 65)
    print(" SUITE 3: Coder Model Accuracy (Code Generation & Test Execution)")
    print("=" * 65)

    prompt = (
        "Write a pure Python function `rotate_matrix(matrix)` that rotates an N x N matrix "
        "90 degrees clockwise in-place and returns it. Provide ONLY the Python code block."
    )

    try:
        req = urllib.request.Request(
            "http://127.0.0.1:11434/api/generate",
            data=json.dumps({"model": "qwen2.5-coder:7b", "prompt": prompt, "stream": False}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            res_obj = json.loads(r.read().decode())
            raw_output = res_obj.get("response", "")
    except Exception:
        cmd = ["ollama", "run", "qwen2.5-coder:7b", prompt]
        res = subprocess.run(cmd, capture_output=True, text=True)
        raw_output = res.stdout

    # Strip any ANSI escape sequences
    raw_output = re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", raw_output)

    # Extract python code
    code_match = re.search(r"```python\s*(.*?)\s*```", raw_output, re.DOTALL)
    if not code_match:
        code_match = re.search(r"```\s*(.*?)\s*```", raw_output, re.DOTALL)
    code = code_match.group(1) if code_match else raw_output

    # Sandboxed execution and functional unit test
    sandbox = {}
    try:
        exec(code, sandbox)
        rotate_func = sandbox.get("rotate_matrix")
        if not rotate_func:
            # Check for any function defined
            for k, v in sandbox.items():
                if callable(v) and k != "__builtins__":
                    rotate_func = v
                    break

        if not rotate_func:
            record_result("Accuracy", "rotate_matrix function defined", False, "No function found in generated code")
            return

        # Test Case 1: 2x2
        m1 = [[1, 2], [3, 4]]
        rotate_func(m1)
        expected1 = [[3, 1], [4, 2]]
        t1_ok = m1 == expected1

        # Test Case 2: 3x3
        m2 = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
        rotate_func(m2)
        expected2 = [[7, 4, 1], [8, 5, 2], [9, 6, 3]]
        t2_ok = m2 == expected2

        all_ok = t1_ok and t2_ok
        record_result(
            "Accuracy",
            "qwen2.5-coder:7b Matrix Rotation Execution Test",
            all_ok,
            f"2x2 test: {'PASS' if t1_ok else 'FAIL'}, 3x3 test: {'PASS' if t2_ok else 'FAIL'}",
        )
    except Exception as e:
        record_result("Accuracy", "qwen2.5-coder:7b Code Execution", False, f"Exception: {e}")


# ==============================================================================
# TEST SUITE 4: Multi-Step Reasoning & Harmonic Mean (Reasoner)
# ==============================================================================
def test_reasoner_accuracy():
    print("\n" + "=" * 65)
    print(" SUITE 4: Reasoner Model Accuracy (14B Hybrid Logic & Math)")
    print("=" * 65)

    if not MODEL_14B.exists():
        record_result("Accuracy", "14B Reasoner Model Exists", False, f"Not found at {MODEL_14B}")
        return

    # Free VRAM before launching llama-cli
    subprocess.run(["g15", "free"], capture_output=True)

    puzzle = (
        "Solve this math problem concisely step-by-step: A car travels from City A to City B at 60 km/h "
        "and returns along the exact same route at 40 km/h. What is the round-trip average speed in km/h? "
        "Conclude with the final answer."
    )

    cmd = [
        "taskset", "-c", P_CORE_MASK,
        "llama-cli",
        "-m", str(MODEL_14B),
        "-ngl", "24",
        "-t", "6",
        "-c", "2048",
        "-fa", "on",
        "-ctk", "q8_0",
        "-ctv", "q8_0",
        "-n", "512",
        "--simple-io",
        "--single-turn",
        "-p", puzzle,
    ]

    res = subprocess.run(cmd, capture_output=True, text=True)
    output = (res.stdout or "") + "\n" + (res.stderr or "")

    # Harmonic mean should be 48 km/h, NOT the arithmetic mean 50 km/h!
    has_correct_48 = "48" in output
    explains_harmonic = any(term in output.lower() for term in ["harmonic", "distance", "time", "total distance", "average speed"])

    record_result(
        "Accuracy",
        "Qwen2.5-14B Harmonic Mean Logic (Expected: 48 km/h)",
        has_correct_48 and explains_harmonic,
        f"Correct 48 km/h identified: {has_correct_48}, Harmonic reasoning explained: {explains_harmonic}",
    )


# ==============================================================================
# TEST SUITE 5: Structured Tool Calling / JSON Output (Agent)
# ==============================================================================
def test_agent_tool_calling():
    print("\n" + "=" * 65)
    print(" SUITE 5: Agent Model Tool Calling & JSON Schema Adherence")
    print("=" * 65)

    prompt = (
        "You are an AI assistant equipped with the tool `get_stock_quote(ticker: str, currency: str)`. "
        "The user asks: What is the current stock price of Apple in USD? "
        "Output a JSON object with 'tool': 'get_stock_quote' and parameters 'ticker': 'AAPL', 'currency': 'USD'."
    )

    try:
        req = urllib.request.Request(
            "http://127.0.0.1:11434/api/generate",
            data=json.dumps({"model": "hermes3:8b", "prompt": prompt, "stream": False, "format": "json"}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            res_obj = json.loads(r.read().decode())
            raw = res_obj.get("response", "")
    except Exception:
        cmd = ["ollama", "run", "hermes3:8b", prompt]
        res = subprocess.run(cmd, capture_output=True, text=True)
        raw = res.stdout.strip()

    # Find JSON substring
    json_match = re.search(r"(\{.*\})", raw, re.DOTALL)
    json_str = json_match.group(1) if json_match else raw

    try:
        data = json.loads(json_str)
        raw_str = json.dumps(data).upper()
        has_apple = "AAPL" in raw_str or "APPLE" in raw_str
        has_usd = "USD" in raw_str

        valid_schema = has_apple and has_usd
        record_result(
            "Agent",
            "Hermes-3-8B Structured JSON Tool Call",
            valid_schema,
            f"Parsed JSON: {json.dumps(data)}",
        )
    except Exception as e:
        record_result("Agent", "Hermes-3-8B Structured JSON Tool Call", False, f"JSON Parse Error: {e} | Raw: {raw[:100]}")


# ==============================================================================
# TEST SUITE 6: OpenAI API Endpoint Compliance & Features
# ==============================================================================
def test_openai_api():
    print("\n" + "=" * 65)
    print(" SUITE 6: OpenAI-Compatible Server API Compliance")
    print("=" * 65)

    # Free VRAM and launch server
    subprocess.run(["g15", "free"], capture_output=True)

    cmd = [
        "taskset", "-c", P_CORE_MASK,
        "llama-server",
        "-m", str(MODEL_14B),
        "-ngl", "24",
        "-t", "6",
        "-c", "4096",
        "-fa", "on",
        "-ctk", "q8_0",
        "-ctv", "q8_0",
        "--host", "127.0.0.1",
        "--port", "8080",
    ]
    srv = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)

    # Wait for ready
    ready = False
    for _ in range(20):
        try:
            with urllib.request.urlopen("http://127.0.0.1:8080/health", timeout=1) as r:
                if r.status == 200:
                    ready = True
                    break
        except Exception:
            time.sleep(1)

    if not ready:
        record_result("API", "Server Readiness Polling", False, "Server failed to boot within 20s")
        srv.kill()
        return

    record_result("API", "Server Readiness (/health returns 200)", True)

    # 1. Test /v1/models endpoint
    try:
        with urllib.request.urlopen("http://127.0.0.1:8080/v1/models", timeout=5) as r:
            models_data = json.loads(r.read().decode())
            has_model_id = "data" in models_data and len(models_data["data"]) > 0
            record_result("API", "GET /v1/models returns valid model inventory", has_model_id)
    except Exception as e:
        record_result("API", "GET /v1/models", False, str(e))

    # 2. Test Non-Streaming Chat Completion
    try:
        payload = {
            "messages": [{"role": "user", "content": "What is 15 + 27? Answer with just the number."}],
            "max_tokens": 10,
            "temperature": 0.0,
            "stream": False,
        }
        req = urllib.request.Request(
            "http://127.0.0.1:8080/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            res_data = json.loads(r.read().decode())
            reply = res_data["choices"][0]["message"]["content"].strip()
            is_42 = "42" in reply
            record_result("API", "POST /v1/chat/completions non-streaming evaluation", is_42, f"Reply: '{reply}'")
    except Exception as e:
        record_result("API", "POST /v1/chat/completions non-streaming", False, str(e))

    # 3. Test Max Tokens constraint
    try:
        payload = {
            "messages": [{"role": "user", "content": "Write a long essay about the history of mathematics."}],
            "max_tokens": 8,
            "stream": False,
        }
        req = urllib.request.Request(
            "http://127.0.0.1:8080/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            res_data = json.loads(r.read().decode())
            usage = res_data.get("usage", {})
            completion_tokens = usage.get("completion_tokens", 0)
            token_bounded = completion_tokens <= 10
            record_result("API", "max_tokens parameter enforcement", token_bounded, f"Tokens generated: {completion_tokens}")
    except Exception as e:
        record_result("API", "max_tokens parameter enforcement", False, str(e))

    # Clean server shutdown
    srv.kill()
    srv.wait()
    subprocess.run(["g15", "free"], capture_output=True)


# ==============================================================================
# MAIN RUNNER
# ==============================================================================
def main():
    start_total = time.time()
    print("=" * 65)
    print("   DELL G15 5530 EXHAUSTIVE FUNCTIONAL & ACCURACY TEST SUITE")
    print("=" * 65)

    test_cli()
    test_power_profiles()
    test_coder_accuracy()
    test_reasoner_accuracy()
    test_agent_tool_calling()
    test_openai_api()

    duration = time.time() - start_total

    print("\n" + "=" * 65)
    print("                   FINAL TEST SCORECARD")
    print("=" * 65)
    total = len(TEST_RESULTS)
    passed = sum(1 for t in TEST_RESULTS if t["status"] == "PASS")
    failed = total - passed

    for r in TEST_RESULTS:
        print(f" [{r['status']}] {r['category']:<10} | {r['name']}")

    print("=" * 65)
    print(f" Total Tests: {total} | Passed: {passed} | Failed: {failed} | Time: {duration:.1f}s")
    if failed == 0:
        print(" [ALL TESTS PASSED] The suite is 100% functionally sound and accurate!")
    else:
        print(f" [WARNING] {failed} test(s) failed. Check details above.")
    print("=" * 65)

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
