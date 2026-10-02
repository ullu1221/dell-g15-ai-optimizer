# Dell G15 5530 Hardware Review & AI Architecture Guide

A comprehensive engineering review and optimization guide for running local Large Language Models (LLMs) on the **Dell G15 5530** gaming laptop.

---

## 1. Hardware Specifications

| Component | Specification | AI Workload Implications |
| :--- | :--- | :--- |
| **CPU** | Intel Core i5-13450HX (Raptor Lake-HX) | 6 Performance cores (12 threads) up to 4.6 GHz, 4 Efficient cores up to 3.4 GHz. 20MB L3 Cache. Supports **AVX2**, **FMA**, and **AVX-VNNI** for INT8 dot-product acceleration. |
| **GPU** | NVIDIA GeForce RTX 3050 Laptop GPU (6GB GDDR6) | Ampere architecture (sm_86, GA107). 2560 CUDA cores, 80 3rd-gen Tensor Cores, 95W maximum TGP. 96-bit memory bus @ 12 Gbps (~144 GB/s bandwidth). |
| **System RAM** | 16 GB DDR5-4800 (Dual Channel) | ~76.8 GB/s bandwidth. Essential for offloading model layers exceeding 6GB VRAM. |
| **Storage** | 512 GB Micron 2550 NVMe SSD (PCIe 4.0 x4) | DRAM-less Host Memory Buffer (HMB) architecture. Sequential read: 5,000 MB/s, write: 4,000 MB/s. |
| **Display** | 15.6" FHD (1920x1080) 120Hz | Driven via hybrid MUX switch or NVIDIA Optimus. |
| **Cooling** | Alienware-inspired Dual Fan / Quad Exhaust | G-Mode (F9 key) boosts fan curves to 100% duty cycle for sustained compute. |

---

## 2. Core Architectural Bottlenecks & Solutions

### Bottleneck A: The 6GB VRAM Ceiling
* **The Problem:** Modern 7B models in FP16 require 14 GB of VRAM. Even INT4 quantized 14B models require ~8.5 GB just for weights, exceeding the 6 GB physical VRAM capacity. Furthermore, allocating context KV caches for multi-thousand token windows consumes hundreds of additional megabytes.
* **The Solution:**
  1. **Hybrid Execution (Layer Splitting):** Offload 24 layers to the RTX 3050 (consuming ~4.9 GB VRAM) and keep the remaining 24 layers in system DDR5 RAM via AVX-VNNI CPU execution.
  2. **Q8_0 KV Cache:** Halves KV memory consumption (`-ctk q8_0 -ctv q8_0`) with negligible (<0.1%) perplexity loss.
  3. **FlashAttention 2 (`-fa on`):** Eliminates the $O(N^2)$ memory footprint of self-attention matrices by computing attention in tiles, preventing OOM crashes on 8k+ context windows.

### Bottleneck B: Intel Hybrid Architecture (P-Cores vs. E-Cores)
* **The Problem:** The i5-13450HX has 6 Performance Cores (with Hyper-Threading, logical IDs 0–11) and 4 Efficient Cores (no Hyper-Threading, logical IDs 12–15). If the OS scheduler migrates matrix multiplication threads to E-cores, generation speed plummets by 40–60% due to reduced IPC and lack of thermal headroom.
* **The Solution:**
  - Pin inference threads strictly to the 6 primary physical Performance Cores using Linux CPU affinity:
    ```bash
    taskset -c 0,2,4,6,8,10 llama-cli ... -t 6
    ```
  - On Windows, apply the affinity bitmask `0x555` (binary `0000 0101 0101 0101`).

### Bottleneck C: DRAM-Less NVMe Wear & Swap Thrashing
* **The Problem:** The internal Micron 2550 is a DRAM-less SSD relying on Host Memory Buffer (HMB). If system memory runs out during heavy model loading and Linux begins aggressive swap file thrashing, two things happen:
  1. Inference speed drops to zero (<0.2 tok/s).
  2. SSD write endurance wears down rapidly (accelerating TBW exhaustion).
* **The Solution:**
  - Keep Linux swap space disabled or set `vm.swappiness=1`.
  - Enforce strict layer bounds so system RAM usage never exceeds 14.5 GB.

### Bottleneck D: vLLM Marlin Temporary Memory Spikes
* **The Problem:** Serving 4-bit AWQ models with vLLM using the ultra-fast Marlin kernel triggers a 420 MiB temporary buffer allocation in `auto_awq.py` to unpack weights during startup. On 6GB VRAM, this causes `torch.cuda.OutOfMemoryError` even if the weights fit.
* **The Solution:**
  - Launch with `--cpu-offload-gb 2`, `--enforce-eager`, and `PYTORCH_CUDA_ALLOC_CONF="expandable_segments:True"`. Model weights drop to 2.88 GB VRAM, allowing the Marlin initialization to succeed safely.

---

## 3. Recommended Engine Matrix

| Workload | Recommended Tool | Model Configuration | Performance |
| :--- | :--- | :--- | :--- |
| **Interactive Coding & Chat** | Ollama | `qwen2.5-coder:7b-instruct-q5_K_M` (100% GPU) | ~38 tokens/sec |
| **Complex Reasoning & Planning** | Native `llama.cpp` | `Qwen2.5-14B-Instruct-Q4_K_M.gguf` (Hybrid: 24 GPU layers, 6 P-cores) | ~9.2 tokens/sec |
| **Roleplay & Multi-Turn Agents** | Ollama | `hermes3:8b` (100% GPU) | ~35 tokens/sec |
| **High-Concurrency API Serving** | vLLM | `Qwen2.5-Coder-7B-Instruct-AWQ` (`--cpu-offload-gb 2`) | ~32 tokens/sec |

---

## 4. Hardware Longevity Best Practices

1. **Monitor Thermals:** Under continuous hybrid generation, the CPU package stabilizes around 75–82°C and the GPU around 68–74°C. Press **Fn + F9 (Alienware G-Mode)** during extended batch runs to spin fans up to 100%.
2. **Elevate the Chassis:** The dual bottom intake vents benefit from a 1-inch elevation, lowering operating temps by 4–6°C.
3. **Power Profile:** Always operate connected to the 240W / 330W Dell barrel charger. Battery power throttles the 3050 TGP from 95W down to 35W.
