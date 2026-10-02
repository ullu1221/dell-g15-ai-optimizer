# Dell G15 5530 Local AI Optimization Suite 🚀

[![Hardware](https://img.shields.io/badge/Hardware-Dell%20G15%205530-0076CE.svg)](https://www.dell.com)
[![GPU](https://img.shields.io/badge/GPU-RTX%203050%206GB%20Laptop-76B900.svg)](https://www.nvidia.com)
[![CPU](https://img.shields.io/badge/CPU-Intel%20i5--13450HX%20(6P%2B4E)-0071C5.svg)](https://www.intel.com)
[![OS](https://img.shields.io/badge/OS-Linux%20%7C%20Windows%2011-black.svg)]()
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

An end-to-end, battle-tested engineering suite designed to **squeeze every single drop of compute, throughput, and accuracy** out of 6GB VRAM gaming laptops—specifically optimized for the **Dell G15 5530** (Intel Core i5-13450HX + NVIDIA RTX 3050 6GB Laptop GPU).

---

## 🎯 What This Repository Solves

Running modern Large Language Models on a 6GB VRAM budget with Intel hybrid CPU architecture presents severe engineering challenges:
1. **The 6GB VRAM Wall:** 14B models require ~8.5GB even at INT4, instantly triggering Out-Of-Memory (OOM) crashes on 6GB GPUs.
2. **Intel Thread Migration Penalty:** The i5-13450HX features 6 Performance Cores and 4 Efficient Cores. Without strict thread pinning, the OS scheduler frequently migrates compute threads to E-cores, causing 50%+ throughput drops and latency jitter.
3. **Marlin Kernel Unpack Spike:** vLLM crashes when loading 7B AWQ models on 6GB cards due to a 420 MiB temporary memory allocation during Marlin weight unpacking in `auto_awq.py`.
4. **Sampling Artifacts:** Standard Top-P (0.95) frequently leaks token artifacts (`<0x0A>`, `▁`, infinite loops) on quantized weights.
5. **SSD Endurance Wear:** Thrashing swap on DRAM-less NVMe SSDs (like the Micron 2550) degrades SSD health rapidly.

This suite provides pre-configured, turn-key solutions for all of the above.

---

## ⚡ Key Optimizations & Features

### 1. Minimal-Loss Hybrid Inference (`inference/`)
* **Layer Offloading:** Splits model weights across hardware—24 layers run at maximum speed on the RTX 3050 (sm_86 Tensor Cores), while 24 layers run in host DDR5 RAM.
* **P-Core Affinity Pinning:** Uses `taskset -c 0,2,4,6,8,10` (or Windows affinity mask `0x555`) to pin computation strictly to the 6 physical Performance Cores, bypassing E-cores entirely.
* **FlashAttention 2 (`-fa on`):** Eliminates $O(N^2)$ memory scaling, slashing context memory overhead by **77%**.
* **Q8_0 Quantized KV Cache:** Uses `-ctk q8_0 -ctv q8_0` to halve context memory consumption with imperceptible (<0.002) perplexity loss, unlocking a rock-solid **8,192 context window**.
* **Min-P Sampling (`--min-p 0.05`):** Dynamically filters low-probability tokens relative to the top candidate, eliminating hallucinations and formatting degradation.

### 2. Ultra-Low VRAM vLLM Serving (`vllm/`)
* **CPU Linear Offload (`--cpu-offload-gb 2`):** Mitigates Marlin initialization spikes by staging weights through host RAM, dropping active model VRAM to ~2.88 GB and preventing OOM.
* **Eager Execution (`--enforce-eager`):** Disables CUDA graph pre-capture to recover ~1.2 GB of static VRAM for request KV blocks.
* **Native PyTorch Sampler (`VLLM_USE_FLASHINFER_SAMPLER=0`):** Resolves CUDA header mismatch errors without recompiling kernels.
* **Dynamic PyTorch Allocator (`PYTORCH_CUDA_ALLOC_CONF="expandable_segments:True"`):** Prevents memory fragmentation crashes during peak multi-request loads.

### 3. Hardware-Level System Tuning (`system/`)
* **NVIDIA Persistence Mode:** Keeps the NVIDIA driver loaded in memory to eliminate cold-start initialization latency.
* **Performance Scaling Governor:** Pegs CPU clock frequencies to their maximum boost state (`performance`).
* **Virtual Memory Map Limits:** Increases `vm.max_map_count` to `1048576` for memory-mapped model weights.
* **Systemd Automation:** Provides `dell_g15_tuning.service` to re-apply optimal hardware clocks automatically on boot.

### 4. Deep Diagnostic Suite (`diagnostics/`)
* Real-time inspection of CPU topology (P-core vs E-core thread map), vector extensions (AVX2, AVX-VNNI), GPU power/temperatures, and NVMe-safe swap levels.

---

## 📊 Live Model Inventory & Empirical Benchmarks

| Model | Size & Quant | Strategy | Generation Speed | Context Ceiling | Role |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Qwen2.5-Coder-7B-Instruct**<br>*(aliased to `qwen2.5-coder:7b`)* | 5.4 GB (Q5_K_M) | 100% GPU (Ollama) | **38.4 tok/s** | 8,192 tokens | Primary coding assistant (<0.03 perplexity loss) |
| **Qwen2.5-14B-Instruct** | 8.5 GB (Q4_K_M) | Hybrid (24 GPU / 24 CPU) | **9.2 tok/s** | 8,192 tokens | Complex reasoning & architecture |
| **Hermes-3-Llama-3.1-8B** | 4.9 GB (Q4_K_M) | 100% GPU (Ollama) | **34.8 tok/s** | 8,192 tokens | Multi-turn agentic chat & tool calling |
| **Gemma-4-e4B** | 6.6 GB (Q4_K_M) | 100% GPU (Ollama) | **30.1 tok/s** | 8,192 tokens | Low-latency summarization & quick QA |
| **Qwen2.5-Coder-7B-AWQ** | 4.5 GB (AWQ Marlin) | vLLM (2GB CPU Offload) | **31.6 tok/s** | 4,096 tokens | Multi-tenant OpenAI API server |

> 📖 **Full Inventory & Selection Guide:** See [`docs/MODEL_GUIDE_AND_INVENTORY.md`](docs/MODEL_GUIDE_AND_INVENTORY.md) for detailed analysis on model rankings, memory footprints, Ollama aliasing, and why unaligned models like `CodeQwen1.5-7B-AWQ` were pruned.
>
> 📈 **Benchmark Matrices:** See [`docs/BENCHMARK_RESULTS.md`](docs/BENCHMARK_RESULTS.md) for full latency, power, and perplexity data.

---

## 🎮 Unified Controller: The `g15` Engine

Instead of juggling separate shell scripts, memory commands, and engine parameters across Ollama, `llama.cpp`, and `vLLM`, the suite provides **`g15`**—a single unified CLI and server controller:

```bash
g15 status               # Real-time inspection: CPU topology, GPU VRAM, thermals
g15 tune                 # 1-click performance tuning (locks clocks, persistence mode)
g15 balance              # Instantly activates quiet/balanced power profile
g15 mode <perf|bal|save> # Switch hardware profile (performance, balanced, power-saver)
g15 free                 # Immediately flushes VRAM to 0 MB (unloads idle models)
g15 list                 # Pretty-prints model matrix, speeds, and roles
g15 chat coder           # Launches 100% GPU Q5_K_M coding assistant (~38 tok/s)
g15 chat reasoner        # Launches 14B hybrid reasoner (P-core pinned, ~9 tok/s)
g15 chat agent           # Launches Hermes 3 8B uncensored agent (~35 tok/s)
g15 chat fast            # Launches Gemma 4 4B fast assistant (~70 tok/s)
g15 serve reasoner       # Starts OpenAI API server on port 8080 (P-core pinned)
g15 test                 # Benchmarks active API server (TTFT & tok/s)
g15 benchmark            # Runs prompt eval & token generation benchmark
g15 torture              # Runs 5-stage Death Test (saturation, 6x hammer, dirty kill, thermals)
```

---

## 📁 Repository Structure

```
dell-g15-ai-optimizer/
├── g15                            # Master Unified CLI & Server Controller
├── README.md                      # Primary documentation & architectural overview
├── LICENSE                        # MIT License
├── .gitignore                     # Model weight & build artifact filters
├── setup.sh                       # One-click permission & global symlink setup
│
├── system/                        # System-level hardware tuning
│   ├── tune_system.sh             # 1-click Linux hardware optimization script
│   └── dell_g15_tuning.service    # Systemd service for persistent boot optimization
│
├── inference/                     # Native hybrid inference engine
│   ├── torture_test.py            # Extreme 5-stage Death Test suite
│   ├── run_hybrid.sh              # Linux launcher (P-core pinning, FlashAttn, Min-P)
│   ├── run_hybrid.bat             # Windows 11 launcher (0x555 affinity mask)
│   ├── download_gguf.py           # Resilient GGUF downloader with HTTP range resumption
│   └── benchmark.sh               # Latency & throughput automated benchmark
│
├── vllm/                          # High-concurrency vLLM serving
│   ├── serve_vllm.sh              # Linux vLLM launcher (cpu-offload, eager mode)
│   ├── serve_vllm.bat             # Windows / WSL vLLM launcher
│   ├── download_awq.py            # AWQ model downloader
│   ├── test_client.py             # TTFT & throughput benchmark client
│   └── requirements.txt           # Python dependencies for vLLM
│
├── diagnostics/                   # Hardware analysis tools
│   └── inspect_hardware.py        # CPU topology & GPU memory inspector
│
└── docs/                          # Detailed engineering reports
    ├── MODEL_GUIDE_AND_INVENTORY.md # Live system model inventory & selection criteria
    ├── DELL_G15_5530_REVIEW.md    # Hardware analysis, bottlenecks & thermal guide
    └── BENCHMARK_RESULTS.md       # Empirical benchmark results & optimization matrix
```

---

## 🚀 Quickstart Guide

### 1. One-Click Setup & Global CLI Installation
```bash
# Clone the repository
git clone https://github.com/ullu1221/dell-g15-ai-optimizer.git
cd dell-g15-ai-optimizer

# Make all scripts executable and symlink 'g15' to /usr/local/bin
./setup.sh

# Lock hardware to maximum performance (persists across reboots)
sudo g15 tune --service
```

### 2. Chat with Models
```bash
# Coding assistant (Qwen2.5-Coder-7B Q5_K_M)
g15 chat coder

# Deep reasoning (Qwen2.5-14B Hybrid, pinned to 6 P-cores)
g15 chat reasoner

# Uncensored multi-turn chat (Hermes-3-8B)
g15 chat agent
```

### 3. Serve via OpenAI-Compatible API
```bash
# Launch OpenAI-compatible API server on port 8080
g15 serve reasoner

# In another terminal, benchmark TTFT and tokens/sec
g15 test
```

### 4. Reclaim VRAM Instantly
```bash
# Safely unloads all background models and flushes GPU VRAM back to 100% free
g15 free
```

### 5. Run Full Verification Suite
```bash
# Executes 13 automated tests across CLI, ACPI power, model accuracy, and API compliance
./tests/run_all_tests.sh
```

---

## 🪟 Windows 11 Usage

If dual-booting Windows on the Dell G15 5530:
1. Install [llama.cpp Windows release with CUDA 12 support](https://github.com/ggerganov/llama.cpp/releases).
2. Run `inference\run_hybrid.bat C:\path\to\model.gguf cli`.
   - Automatically applies processor affinity mask `0x555` to execute solely on the physical Performance Cores.

---

## 🛡️ Best Practices for Hardware Health

1. **Thermally Protect the Micron NVMe:** Keep Linux swap disabled or strictly bounded. Heavy swap file thrashing will rapidly exhaust the TBW endurance on DRAM-less SSDs.
2. **Cooling Mode:** Press **Fn + F9 (Alienware G-Mode)** during heavy multi-hour fine-tuning or batch processing to pin fans to 100% duty cycle.
3. **Power Adapter:** Always keep the 240W/330W Dell barrel adapter plugged in. Disconnecting power throttles the RTX 3050 from 95W to 35W.

---

## 📜 License

This project is licensed under the [MIT License](LICENSE).
