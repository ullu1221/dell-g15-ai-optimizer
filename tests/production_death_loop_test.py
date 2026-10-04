#!/usr/bin/env python3
"""
DELL G15 5530 EXTREME PRODUCTION DEATH & LOOP TEST SUITE
=========================================================
Performs exhaustive, serious, and adversarial torture testing across:
1. Static syntax & bytecode compilation
2. High-velocity thermal mode churn loop (40 iterations)
3. Multi-threaded concurrent read/write hammer
4. Adversarial state file corruption & self-healing
5. Boundary & parameter fuzzing torture
6. Real-world hybrid LLM inference under dynamic thermal shifting
7. Systemd service lifecycle resilience
8. Hardware & NVMe endurance invariants
"""

import concurrent.futures
import json
import os
import random
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

# Paths
REPO_DIR = Path("/home/p/dell-g15-ai-optimizer")
THERMAL_DIR = Path("/home/p/dell-g15-thermal-control")
USER_STATE_FILE = Path.home() / ".config" / "dell-g15" / "state.json"
SYS_STATE_FILE = Path("/var/tmp/dell-g15-state.json")
WMAX_FILE = Path("/sys/class/platform-profile/platform-profile-0/profile")
EPP_FILE = Path("/sys/devices/system/cpu/cpu0/cpufreq/energy_performance_preference")

def log(tag: str, msg: str):
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] [{tag}] {msg}", flush=True)


def check(cond: bool, msg: str):
    status = "PASS" if cond else "FAIL"
    print(f"  [{status}] {msg}", flush=True)
    if not cond:
        raise AssertionError(f"Check failed: {msg}")


# ==============================================================================
# SUITE 1: Static Syntax & Compilation Validation
# ==============================================================================
def suite_1_compilation():
    log("SUITE 1", "Verifying all Python & Bash source files across both repositories...")
    py_files = [
        REPO_DIR / "g15",
        REPO_DIR / "diagnostics" / "inspect_hardware.py",
        REPO_DIR / "inference" / "download_gguf.py",
        REPO_DIR / "inference" / "torture_test.py",
        REPO_DIR / "tests" / "test_functional.py",
        THERMAL_DIR / "scripts" / "dell-g15-thermal",
    ]
    for pf in py_files:
        if pf.exists():
            res = subprocess.run(["python3", "-m", "py_compile", str(pf)], capture_output=True, text=True)
            check(res.returncode == 0, f"Python compile: {pf.name}")

    sh_files = [
        REPO_DIR / "setup.sh",
        REPO_DIR / "system" / "tune_system.sh",
        REPO_DIR / "inference" / "run_hybrid.sh",
        REPO_DIR / "inference" / "benchmark.sh",
        REPO_DIR / "tests" / "run_all_tests.sh",
        THERMAL_DIR / "install.sh",
    ]
    for sf in sh_files:
        if sf.exists():
            res = subprocess.run(["bash", "-n", str(sf)], capture_output=True, text=True)
            check(res.returncode == 0, f"Bash syntax: {sf.name}")


# ==============================================================================
# SUITE 2: High-Velocity Mode Churn Loop (40 Iterations)
# ==============================================================================
def suite_2_mode_churn_loop():
    log("SUITE 2", "Starting High-Velocity Mode Churn Loop (40 Rapid Transitions)...")
    modes = ["balanced", "performance", "quiet", "battery", "gmode"]
    expected_wmax = {
        "balanced": "balanced",
        "performance": "balanced-performance",
        "quiet": "quiet",
        "battery": "low-power",
        "gmode": "performance",
    }
    
    start_t = time.perf_counter()
    for i in range(1, 41):
        target = modes[(i - 1) % len(modes)]
        cmd = ["dell-g15-thermal", "mode", target]
        res = subprocess.run(cmd, capture_output=True, text=True)
        check(res.returncode == 0, f"Iteration {i}/40: Switched to {target}")

        # Verify WMAX register
        if WMAX_FILE.exists():
            actual_wmax = WMAX_FILE.read_text().strip()
            check(actual_wmax == expected_wmax[target], f"WMAX sysfs matches '{expected_wmax[target]}' (got '{actual_wmax}')")

        # Verify state.json
        check(USER_STATE_FILE.exists(), f"State file exists after iteration {i}")
        data = json.loads(USER_STATE_FILE.read_text())
        check(data.get("mode") == target, f"state.json records mode='{target}'")
        check(data.get("wmax") == expected_wmax[target], f"state.json records wmax='{expected_wmax[target]}'")

    total_time = time.perf_counter() - start_t
    log("SUITE 2", f"40 Mode Transitions completed successfully in {total_time:.2f}s ({total_time/40*1000:.1f}ms per transition).")


# ==============================================================================
# SUITE 3: Multi-Threaded Concurrent Read/Write Hammer
# ==============================================================================
def worker_writer(thread_id: int, cycles: int):
    modes = ["balanced", "performance", "quiet", "battery", "gmode"]
    for c in range(cycles):
        m = random.choice(modes)
        res = subprocess.run(["dell-g15-thermal", "mode", m], capture_output=True, text=True)
        if res.returncode != 0:
            return False, f"Writer {thread_id} failed on cycle {c} with returncode {res.returncode}"
        time.sleep(random.uniform(0.01, 0.05))
    return True, f"Writer {thread_id} completed {cycles} cycles"


def worker_reader(thread_id: int, cycles: int):
    for c in range(cycles):
        # 1. Check status
        res = subprocess.run(["dell-g15-thermal", "status"], capture_output=True, text=True)
        if res.returncode != 0:
            return False, f"Reader {thread_id} failed status query on cycle {c}"
        
        # 2. Check state.json atomic read
        try:
            if USER_STATE_FILE.exists():
                content = USER_STATE_FILE.read_text()
                if content:
                    data = json.loads(content)
                    if not isinstance(data, dict) or "mode" not in data:
                        return False, f"Corrupted state dictionary on cycle {c}"
        except json.JSONDecodeError as e:
            return False, f"Atomic read violation: JSONDecodeError ({e}) on cycle {c}"
        time.sleep(random.uniform(0.01, 0.04))
    return True, f"Reader {thread_id} completed {cycles} cycles"


def suite_3_concurrency_hammer():
    log("SUITE 3", "Launching Multi-Threaded Concurrent Read/Write Hammer (10 Workers)...")
    NUM_WORKERS = 10
    CYCLES_PER_WORKER = 8
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
        futures = []
        for i in range(5):
            futures.append(executor.submit(worker_writer, i, CYCLES_PER_WORKER))
        for i in range(5, 10):
            futures.append(executor.submit(worker_reader, i, CYCLES_PER_WORKER))

        for f in concurrent.futures.as_completed(futures):
            ok, msg = f.result()
            check(ok, msg)
            
    log("SUITE 3", "Multi-Threaded Hammer passed: Zero atomic corruption or race conditions detected.")


# ==============================================================================
# SUITE 4: Adversarial State File Corruption & Self-Healing
# ==============================================================================
def suite_4_adversarial_self_healing():
    log("SUITE 4", "Starting Adversarial State File Corruption & Self-Healing Stress Test...")
    
    # 4A. Truncated JSON
    log("SUITE 4", "Test 4A: Injecting truncated JSON...")
    USER_STATE_FILE.write_text('{"mode": "perf", "wmax": "balanced-per')
    res = subprocess.run(["dell-g15-thermal", "restore"], capture_output=True, text=True)
    check(res.returncode == 0, "Handled truncated JSON without crash")
    check("balanced" in res.stdout.lower(), "Self-healed back to default balanced profile")

    # 4B. Empty File (0 bytes)
    log("SUITE 4", "Test 4B: Injecting 0-byte file...")
    USER_STATE_FILE.write_text('')
    res = subprocess.run(["dell-g15-thermal", "restore"], capture_output=True, text=True)
    check(res.returncode == 0, "Handled 0-byte file without crash")
    check("balanced" in res.stdout.lower(), "Self-healed 0-byte file back to balanced profile")

    # 4C. Random Binary Garbage
    log("SUITE 4", "Test 4C: Injecting random binary garbage...")
    with open(USER_STATE_FILE, "wb") as f:
        f.write(os.urandom(256))
    res = subprocess.run(["dell-g15-thermal", "restore"], capture_output=True, text=True)
    check(res.returncode == 0, "Handled binary garbage without crash")
    check("balanced" in res.stdout.lower(), "Self-healed binary garbage back to balanced profile")

    # 4D. Invalid Mode Injected
    log("SUITE 4", "Test 4D: Injecting illegal mode name...")
    USER_STATE_FILE.write_text(json.dumps({"mode": "SUPER_HYPER_DRIVE", "wmax": "unknown"}))
    res = subprocess.run(["dell-g15-thermal", "restore"], capture_output=True, text=True)
    check(res.returncode == 0, "Handled illegal mode without crash")
    check("balanced" in res.stdout.lower(), "Fell back safely to balanced profile")

    log("SUITE 4", "Adversarial self-healing passed: 100% resilient to corrupted/tampered state files.")


# ==============================================================================
# SUITE 5: Boundary & Parameter Fuzzing Torture
# ==============================================================================
def suite_5_parameter_fuzzing():
    log("SUITE 5", "Testing Parameter Boundaries and Input Fuzzing...")

    # Out of range fan boost (negative & >100)
    res_neg = subprocess.run(["dell-g15-thermal", "fan", "-20", "-20"], capture_output=True, text=True)
    check("[ERROR]" in res_neg.stdout, "Rejects negative fan boost (-20%)")

    res_huge = subprocess.run(["dell-g15-thermal", "fan", "150", "200"], capture_output=True, text=True)
    check("[ERROR]" in res_huge.stdout, "Rejects excessive fan boost (>100%)")

    # Valid boundary limits (0% and 100%)
    res_zero = subprocess.run(["dell-g15-thermal", "fan", "0", "0"], capture_output=True, text=True)
    check(res_zero.returncode == 0, "Accepts minimum boundary fan offset (0%)")

    res_max = subprocess.run(["dell-g15-thermal", "fan", "100", "100"], capture_output=True, text=True)
    check(res_max.returncode == 0, "Accepts maximum boundary fan offset (100%)")

    # Reset fan back to 0
    subprocess.run(["dell-g15-thermal", "fan", "0", "0"], capture_output=True)

    # Invalid mode strings
    res_inv = subprocess.run(["dell-g15-thermal", "mode", "invalid_random_string"], capture_output=True, text=True)
    check(res_inv.returncode != 0, "Rejects unknown mode string with error code")

    log("SUITE 5", "Parameter fuzzing passed: Hardware register boundaries strictly enforced.")


# ==============================================================================
# SUITE 6: Real-World Inference Under Dynamic Thermal Shift
# ==============================================================================
def suite_6_inference_thermal_shift():
    log("SUITE 6", "Testing Real-World LLM Generation Under Dynamic Thermal Shifting...")
    
    # Pre-clean
    subprocess.run(["g15", "free"], capture_output=True)
    time.sleep(1)

    # Send prompt to local Ollama (qwen2.5-coder:7b)
    url = "http://127.0.0.1:11434/api/generate"
    payload = {
        "model": "qwen2.5-coder:7b",
        "prompt": "Write a fast Python quicksort algorithm with comments and time complexity analysis.",
        "stream": True,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )

    t0 = time.perf_counter()
    tokens = 0
    with urllib.request.urlopen(req, timeout=30) as resp:
        for line in resp:
            data = json.loads(line.decode("utf-8"))
            tokens += 1
            # Dynamic thermal shifting during active streaming
            if tokens == 15:
                log("SUITE 6", "Shifting to G-Mode mid-generation...")
                subprocess.run(["g15", "gmode"], capture_output=True)
            elif tokens == 35:
                log("SUITE 6", "Shifting to Performance mode mid-generation...")
                subprocess.run(["dell-g15-thermal", "performance"], capture_output=True)
            elif tokens == 55:
                log("SUITE 6", "Shifting back to Balanced mode mid-generation...")
                subprocess.run(["g15", "balance"], capture_output=True)

            if data.get("done", False):
                break

    duration = time.perf_counter() - t0
    check(tokens > 50, f"Streaming completed with {tokens} tokens in {duration:.2f}s ({tokens/duration:.1f} tok/s)")
    
    # Reclaim GPU memory after inference
    subprocess.run(["g15", "free"], capture_output=True)
    time.sleep(1)
    log("SUITE 6", f"Inference during active thermal shift succeeded! Stream speed: {tokens/duration:.1f} tok/s.")


# ==============================================================================
# SUITE 7: Systemd Service Resilience & Lifecycle Test
# ==============================================================================
def suite_7_systemd_lifecycle():
    log("SUITE 7", "Testing systemd user restore service lifecycle...")
    
    # Save performance mode
    subprocess.run(["dell-g15-thermal", "performance"], capture_output=True)
    
    # Restart the service 5 times in rapid succession
    for i in range(1, 6):
        res = subprocess.run(["systemctl", "--user", "restart", "dell-g15-thermal-restore.service"], capture_output=True, text=True)
        check(res.returncode == 0, f"Service restart {i}/5 succeeded")
        
        status = subprocess.run(["systemctl", "--user", "is-active", "dell-g15-thermal-restore.service"], capture_output=True, text=True)
        # Type=oneshot with RemainAfterExit=yes -> active
        check("active" in status.stdout.strip(), f"Service is active after restart {i}")

    # Verify WMAX profile restored correctly
    if WMAX_FILE.exists():
        check(WMAX_FILE.read_text().strip() == "balanced-performance", "Service restored balanced-performance (0xa1)")

    log("SUITE 7", "Systemd service lifecycle passed: 100% stable under rapid restarts.")


# ==============================================================================
# SUITE 8: Hardware Invariants & Memory Safety Audit
# ==============================================================================
def suite_8_hardware_invariants():
    log("SUITE 8", "Auditing Hardware & Memory Safety Invariants...")
    
    # 1. Swap Invariant
    swap_used = 0
    if os.path.exists("/proc/meminfo"):
        with open("/proc/meminfo", "r") as f:
            for line in f:
                if line.startswith("SwapTotal:"):
                    st = int(line.split(":")[1].strip().split()[0])
                elif line.startswith("SwapFree:"):
                    sf = int(line.split(":")[1].strip().split()[0])
            swap_used = st - sf
    check(swap_used == 0, f"NVMe Protection Invariant: 0 kB swap used (got {swap_used} kB)")

    # 2. NVIDIA Persistence Mode
    res_pm = subprocess.run(["nvidia-smi", "--query-gpu=persistence_mode", "--format=csv,noheader"], capture_output=True, text=True)
    check("enabled" in res_pm.stdout.lower(), "NVIDIA Persistence Mode is ENABLED")

    # 3. Kernel Memory Map Limit
    res_vm = subprocess.run(["sysctl", "-n", "vm.max_map_count"], capture_output=True, text=True)
    check(int(res_vm.stdout.strip()) >= 1048576, f"vm.max_map_count >= 1048576 (got {res_vm.stdout.strip()})")

    # 4. Available VRAM Headroom (after flush)
    subprocess.run(["g15", "free"], capture_output=True)
    time.sleep(1)
    res_vram = subprocess.run(["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"], capture_output=True, text=True)
    free_vram = int(res_vram.stdout.strip().split("\n")[0])
    check(free_vram >= 5700, f"VRAM Headroom: {free_vram} MiB free (>= 5700 MiB expected)")

    log("SUITE 8", "Hardware invariants audit passed: NVMe safe, CUDA ready, memory maps optimal.")


# ==============================================================================
# Main Orchestrator
# ==============================================================================
def main():
    print("=" * 70)
    print("   DELL G15 5530 EXTREME PRODUCTION DEATH & LOOP TEST SUITE")
    print("=" * 70)

    suites = [
        ("Suite 1: Static Syntax & Compilation Validation", suite_1_compilation),
        ("Suite 2: High-Velocity Mode Churn Loop (40 Iterations)", suite_2_mode_churn_loop),
        ("Suite 3: Multi-Threaded Concurrent Read/Write Hammer", suite_3_concurrency_hammer),
        ("Suite 4: Adversarial State File Corruption & Self-Healing", suite_4_adversarial_self_healing),
        ("Suite 5: Boundary & Parameter Fuzzing Torture", suite_5_parameter_fuzzing),
        ("Suite 6: Real-World Inference Under Dynamic Thermal Shift", suite_6_inference_thermal_shift),
        ("Suite 7: Systemd Service Lifecycle Resilience", suite_7_systemd_lifecycle),
        ("Suite 8: Hardware Invariants & Memory Safety Audit", suite_8_hardware_invariants),
    ]

    scorecard = {}
    for name, fn in suites:
        print("\n" + "-" * 70)
        log("RUN", f"Starting {name}...")
        try:
            fn()
            scorecard[name] = True
            log("RUN", f"RESULT: {name} -> [PASSED]")
        except Exception as e:
            scorecard[name] = False
            log("RUN", f"RESULT: {name} -> [FAILED]: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 70)
    print("                      PRODUCTION SCORECARD")
    print("=" * 70)
    all_passed = True
    for name, passed in scorecard.items():
        print(f" {name:<60} [{'PASS' if passed else 'FAIL'}]")
        if not passed:
            all_passed = False

    print("=" * 70)
    if all_passed:
        print(" [ALL 8 SUITES PASSED] Production grade: Zero defects, 100% resilient.")
        # Leave system in desired performance mode
        subprocess.run(["dell-g15-thermal", "performance"], capture_output=True)
    else:
        print(" [DEFECTS DETECTED] Immediate fix required.")
    print("=" * 70)
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
