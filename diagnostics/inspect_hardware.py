#!/usr/bin/env python3
"""
Dell G15 5530 Deep Hardware & Topology Inspector
Analyzes CPU core topology (P-cores vs E-cores), GPU VRAM budgets,
kernel memory limits, and hardware vector instruction sets.
"""

import os
import platform
import subprocess
import sys


def print_header(title: str):
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)


def inspect_cpu():
    print_header("CPU & TOPOLOGY ANALYSIS")
    print(f"Processor: {platform.processor()}")

    p_cores = []
    e_cores = []
    flags = set()

    if os.path.exists("/proc/cpuinfo"):
        current_processor = None
        current_core_id = None
        core_map = {}

        with open("/proc/cpuinfo", "r") as f:
            for line in f:
                if line.startswith("processor"):
                    current_processor = int(line.split(":")[1].strip())
                elif line.startswith("core id"):
                    current_core_id = int(line.split(":")[1].strip())
                    if current_processor is not None:
                        core_map.setdefault(current_core_id, []).append(current_processor)
                elif line.startswith("flags"):
                    for flag in line.split(":")[1].strip().split():
                        flags.add(flag.lower())

        # For i5-13450HX: 6 P-cores have hyperthreading (2 threads per core: 0-5 -> threads 0-11).
        # 4 E-cores have no hyperthreading (1 thread per core: 6-9 -> threads 12-15).
        for core_id, threads in sorted(core_map.items()):
            if len(threads) > 1:
                p_cores.extend(threads)
            else:
                e_cores.extend(threads)

        print(f"Total Logical Threads: {len(p_cores) + len(e_cores)}")
        print(f"Performance Cores (P-Cores): Threads {p_cores} (Physical primary: 0,2,4,6,8,10)")
        print(f"Efficient Cores (E-Cores):   Threads {e_cores}")
    else:
        print("(/proc/cpuinfo unavailable)")

    # Vector Extensions
    vector_exts = []
    for ext in ["avx", "avx2", "avx512f", "avx_vnni", "fma", "f16c"]:
        if ext in flags:
            vector_exts.append(ext.upper())
    print(f"Vector Acceleration: {', '.join(vector_exts) if vector_exts else 'Standard x86_64'}")

    # Scaling Governor
    gov_file = "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"
    if os.path.exists(gov_file):
        try:
            with open(gov_file, "r") as f:
                gov = f.read().strip()
            print(f"Active CPU Governor: {gov} {'[OPTIMAL]' if gov == 'performance' else '[SUBOPTIMAL - Run tune_system.sh]'}")
        except Exception:
            pass


def inspect_gpu():
    print_header("NVIDIA GPU & VRAM BUDGET")
    try:
        res = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,driver_version,memory.total,memory.free,power.draw,temperature.gpu,persistence_mode", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            check=True,
        )
        line = res.stdout.strip()
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 7:
            name, driver, total, free, power, temp, persist = parts[:7]
            print(f"Device:           {name}")
            print(f"Driver Version:   {driver}")
            print(f"VRAM Capacity:    {total} MiB (Free: {free} MiB)")
            print(f"Power Draw:       {power} W")
            print(f"Temperature:      {temp} °C")
            print(f"Persistence Mode: {persist} {'[ENABLED]' if persist.lower() == 'enabled' else '[DISABLED - Run tune_system.sh]'}")
    except (subprocess.SubprocessError, FileNotFoundError):
        print("[!] nvidia-smi failed or not present. Running on integrated GPU / non-NVIDIA?")


def inspect_memory():
    print_header("HOST MEMORY & VIRTUAL MEMORY")
    if os.path.exists("/proc/meminfo"):
        meminfo = {}
        with open("/proc/meminfo", "r") as f:
            for line in f:
                parts = line.split(":")
                if len(parts) == 2:
                    meminfo[parts[0].strip()] = parts[1].strip()

        mem_total = meminfo.get("MemTotal", "N/A")
        mem_avail = meminfo.get("MemAvailable", "N/A")
        swap_total = meminfo.get("SwapTotal", "N/A")
        swap_free = meminfo.get("SwapFree", "N/A")

        print(f"Host RAM:   Total {mem_total} | Available {mem_avail}")
        print(f"Swap Space: Total {swap_total} | Free {swap_free}")
        
        # Check swap usage
        try:
            st = int(swap_total.split()[0])
            sf = int(swap_free.split()[0])
            used_swap = st - sf
            if used_swap > 100 * 1024:
                print("[WARNING] Active swap usage detected! Swap thrashing will degrade SSD endurance.")
            else:
                print("[✓] Swap usage is zero / near-zero. NVMe DRAM-less storage protected.")
        except Exception:
            pass

    max_map_file = "/proc/sys/vm/max_map_count"
    if os.path.exists(max_map_file):
        with open(max_map_file, "r") as f:
            val = f.read().strip()
        print(f"vm.max_map_count: {val} {'[OPTIMAL]' if int(val) >= 1048576 else '[SUBOPTIMAL - Run tune_system.sh]'}")


def main():
    print("=" * 60)
    print(" Dell G15 5530 AI Environment Diagnostic Suite")
    print(f" OS: {platform.system()} {platform.release()} ({platform.machine()})")
    print("=" * 60)
    
    inspect_cpu()
    inspect_gpu()
    inspect_memory()
    print("\n" + "=" * 60)
    print(" Diagnostic Complete")
    print("=" * 60)


if __name__ == "__main__":
    main()
