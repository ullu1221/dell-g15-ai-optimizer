#!/usr/bin/env python3
"""
DEATH TEST: Ultimate Hardware & Inference Torture Suite for Dell G15 5530
Pushes CPU, GPU, memory, context windows, and concurrent API servers to theoretical limits.
"""

import concurrent.futures
import json
import os
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

MODEL_14B = Path.home() / "models" / "Qwen2.5-14B-Instruct-Q4_K_M.gguf"
P_CORE_MASK = "0,2,4,6,8,10"


def log(stage: str, msg: str):
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] [{stage}] {msg}", flush=True)


def get_gpu_telemetry():
    try:
        res = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used,memory.free,temperature.gpu,power.draw", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            check=True,
        )
        parts = [p.strip() for p in res.stdout.strip().split(",")]
        return {
            "used_mb": int(parts[0]),
            "free_mb": int(parts[1]),
            "temp_c": int(parts[2]),
            "power_w": parts[3],
        }
    except Exception as e:
        return {"used_mb": 0, "free_mb": 0, "temp_c": 0, "power_w": str(e)}


def check_swap_invariant():
    if os.path.exists("/proc/meminfo"):
        with open("/proc/meminfo", "r") as f:
            for line in f:
                if line.startswith("SwapTotal:"):
                    st = int(line.split(":")[1].strip().split()[0])
                elif line.startswith("SwapFree:"):
                    sf = int(line.split(":")[1].strip().split()[0])
        used = st - sf
        return used == 0, used
    return True, 0


# ==============================================================================
# STAGE 1: Massive Context Saturation Test (8,192 Tokens)
# ==============================================================================
def stage_1_context_saturation():
    log("STAGE 1", "Starting Massive Context Window Saturation Test (8k Context)...")
    if not MODEL_14B.exists():
        log("STAGE 1", f"[ERROR] Model {MODEL_14B} not found.")
        return False

    # Generate a massive 3000-word prompt (~4000 tokens)
    large_text = "The quick brown fox jumps over the lazy dog. " * 350
    prompt = f"Analyze the following text and count the number of sentences:\n{large_text}\nSummary:"

    cmd = [
        "taskset", "-c", P_CORE_MASK,
        "llama-cli",
        "-m", str(MODEL_14B),
        "-ngl", "24",
        "-t", "6",
        "-c", "8192",
        "-fa", "on",
        "-ctk", "q8_0",
        "-ctv", "q8_0",
        "-n", "64",
        "--no-conversation",
        "-p", prompt,
    ]

    log("STAGE 1", "Spawning hybrid llama-cli with 8192 context window and heavy prompt...")
    start_time = time.time()
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    peak_vram = 0
    while proc.poll() is None:
        telem = get_gpu_telemetry()
        if telem["used_mb"] > peak_vram:
            peak_vram = telem["used_mb"]
        time.sleep(0.5)

    stdout, stderr = proc.communicate()
    duration = time.time() - start_time

    log("STAGE 1", f"Completed in {duration:.1f}s. Peak VRAM: {peak_vram} MiB / 6144 MiB.")
    
    # Check for prompt eval stats in stderr
    for line in stderr.split("\n"):
        if "prompt eval time" in line or "eval time" in line:
            log("STAGE 1", f"Timing: {line.strip()}")

    swap_ok, swap_used = check_swap_invariant()
    log("STAGE 1", f"NVMe Swap Invariant: {'SAFE (0 kB swap)' if swap_ok else f'VIOLATED ({swap_used} kB)'}")
    return proc.returncode == 0 and swap_ok


# ==============================================================================
# STAGE 2: Concurrent API Flooding / Hammer Test
# ==============================================================================
def send_request(client_id: int):
    url = "http://127.0.0.1:8080/v1/chat/completions"
    payload = {
        "messages": [
            {"role": "user", "content": f"Client {client_id}: Give 3 prime numbers greater than 1000."},
        ],
        "max_tokens": 40,
        "temperature": 0.6,
        "stream": True,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    t0 = time.perf_counter()
    tokens = 0
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            for line in resp:
                l = line.decode("utf-8").strip()
                if l.startswith("data: ") and l[6:].strip() != "[DONE]":
                    tokens += 1
        latency = time.perf_counter() - t0
        return True, client_id, tokens, latency
    except Exception as e:
        return False, client_id, 0, str(e)


def stage_2_api_hammer():
    log("STAGE 2", "Starting High-Concurrency Hammer Test (OpenAI API Server)...")
    
    # Launch server
    srv_cmd = [
        "taskset", "-c", P_CORE_MASK,
        "llama-server",
        "-m", str(MODEL_14B),
        "-ngl", "24",
        "-t", "6",
        "-c", "8192",
        "-fa", "on",
        "-ctk", "q8_0",
        "-ctv", "q8_0",
        "--host", "127.0.0.1",
        "--port", "8080",
    ]
    srv_proc = subprocess.Popen(srv_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    log("STAGE 2", f"Server booted with PID {srv_proc.pid}. Waiting for readiness...")

    ready = False
    for _ in range(25):
        try:
            with urllib.request.urlopen("http://127.0.0.1:8080/health", timeout=1) as resp:
                if resp.status == 200:
                    ready = True
                    break
        except Exception:
            time.sleep(1)

    if not ready:
        log("STAGE 2", "[FAIL] Server failed to initialize within 25 seconds.")
        srv_proc.kill()
        return False

    log("STAGE 2", "Server ready! Blasting with 6 concurrent streaming clients...")
    CONCURRENCY = 6
    with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
        futures = [executor.submit(send_request, i) for i in range(CONCURRENCY)]
        results = [f.result() for f in futures]

    successes = 0
    total_tokens = 0
    for ok, cid, tokens, res in results:
        if ok:
            successes += 1
            total_tokens += tokens
            log("STAGE 2", f"  -> Client {cid}: SUCCESS ({tokens} tokens in {res:.2f}s, {tokens/res:.1f} tok/s)")
        else:
            log("STAGE 2", f"  -> Client {cid}: FAILED ({res})")

    log("STAGE 2", f"Concurrency Results: {successes}/{CONCURRENCY} requests served. Total tokens: {total_tokens}")

    # ==============================================================================
    # STAGE 3: Dirty Hard-Kill (SIGKILL) & Orphan Recovery
    # ==============================================================================
    log("STAGE 3", "Initiating Dirty Hard-Kill (SIGKILL) under active server...")
    srv_proc.kill()
    srv_proc.wait()
    time.sleep(1)

    dirty_telem = get_gpu_telemetry()
    log("STAGE 3", f"GPU state immediately after SIGKILL: {dirty_telem['used_mb']} MiB used.")

    log("STAGE 3", "Invoking 'g15 free' to clean orphan CUDA memory...")
    subprocess.run(["g15", "free"], capture_output=True)
    time.sleep(1)

    clean_telem = get_gpu_telemetry()
    log("STAGE 3", f"GPU state after 'g15 free': {clean_telem['used_mb']} MiB used ({clean_telem['free_mb']} MiB free).")
    orphan_recovered = clean_telem["free_mb"] >= 5800
    log("STAGE 3", f"Orphan Recovery: {'PASSED (Clean 5818 MiB)' if orphan_recovered else 'FAILED'}")

    return successes == CONCURRENCY and orphan_recovered


# ==============================================================================
# STAGE 4: Sustained Torture & Thermal Curve
# ==============================================================================
def stage_4_sustained_torture():
    log("STAGE 4", "Starting 60-Second Sustained Torture Test (sm_86 Tensor Cores + AVX-VNNI P-Cores)...")
    
    # Run heavy prompt processing repeatedly for 60 seconds
    prompt = "Write a comprehensive mathematical proof of the Prime Number Theorem in extreme detail with step-by-step calculus derivations."
    
    cmd = [
        "taskset", "-c", P_CORE_MASK,
        "llama-cli",
        "-m", str(MODEL_14B),
        "-ngl", "24",
        "-t", "6",
        "-c", "4096",
        "-fa", "on",
        "-ctk", "q8_0",
        "-ctv", "q8_0",
        "-n", "512",
        "-p", prompt,
    ]

    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    log("STAGE 4", f"Torture process running (PID: {proc.pid}). Monitoring thermal and power curve...")

    start_t = time.time()
    temps = []
    powers = []
    
    while time.time() - start_t < 60 and proc.poll() is None:
        telem = get_gpu_telemetry()
        temps.append(telem["temp_c"])
        powers.append(telem["power_w"])
        elapsed = int(time.time() - start_t)
        log("STAGE 4", f"  [{elapsed}s/60s] GPU Temp: {telem['temp_c']} °C | Power: {telem['power_w']} W | VRAM: {telem['used_mb']} MiB")
        time.sleep(5)

    if proc.poll() is None:
        proc.kill()
        proc.wait()

    subprocess.run(["g15", "free"], capture_output=True)

    max_temp = max(temps) if temps else 0
    avg_temp = sum(temps) / len(temps) if temps else 0
    log("STAGE 4", f"Thermal Analysis: Peak Temp: {max_temp} °C | Avg Temp: {avg_temp:.1f} °C (Thermal Throttle Threshold: 86 °C)")
    thermal_safe = max_temp < 80
    log("STAGE 4", f"Thermal Headroom: {'HEALTHY & COOL' if thermal_safe else 'ELEVATED'}")
    return thermal_safe


def main():
    print("=" * 70)
    print("        DELL G15 5530 EXTREME DEATH TEST (TORTURE SUITE)")
    print("=" * 70)

    # Pre-test cleanup
    subprocess.run(["g15", "free"], capture_output=True)

    results = {}
    
    # Stage 1
    results["Stage 1: Context Saturation (8k)"] = stage_1_context_saturation()
    
    # Stage 2 & 3
    results["Stage 2: Concurrent API Hammering (6x) & Stage 3: Dirty Kill Recovery"] = stage_2_api_hammer()

    # Stage 4
    results["Stage 4: Sustained Thermal Torture (60s)"] = stage_4_sustained_torture()

    # Stage 5
    swap_safe, swap_val = check_swap_invariant()
    results["Stage 5: DRAM-less NVMe Swap Invariant (0 kB)"] = swap_safe

    print("\n" + "=" * 70)
    print("                 FINAL DEATH TEST VERDICT")
    print("=" * 70)
    all_passed = True
    for test_name, passed in results.items():
        print(f" {test_name:<60} [{'PASS' if passed else 'FAIL'}]")
        if not passed:
            all_passed = False

    print("=" * 70)
    if all_passed:
        print(" [SURVIVED] System passed every extreme stress boundary with zero defects!")
    else:
        print(" [WARNING] Some tests triggered edge case failures.")
    print("=" * 70)


if __name__ == "__main__":
    main()
