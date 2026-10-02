@echo off
REM ==============================================================================
REM Ultra-Low VRAM vLLM Launcher for NVIDIA RTX 3050 6GB (Windows / WSL)
REM ==============================================================================

setlocal enabledelayedexpansion

set "MODEL=%~1"
if "%MODEL%"=="" set "MODEL=Qwen/Qwen2.5-Coder-7B-Instruct-AWQ"

set "PORT=8000"
set "HOST=0.0.0.0"
set "MAX_MODEL_LEN=4096"
set "GPU_UTIL=0.90"
set "CPU_OFFLOAD=2"

set "CUDA_VISIBLE_DEVICES=0"
set "PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True"
set "VLLM_USE_FLASHINFER_SAMPLER=0"

echo ==========================================================
echo  Starting vLLM Engine (6GB VRAM Budget Profile - Windows)
echo  Model:             %MODEL%
echo  Quantization:      awq_marlin
echo  CPU Offload:       %CPU_OFFLOAD% GB
echo  Execution Mode:    --enforce-eager
echo  GPU Memory Util:   %GPU_UTIL%
echo  Max Context Len:   %MAX_MODEL_LEN%
echo  Endpoint:          http://%HOST%:%PORT%/v1
echo ==========================================================

python -m vllm.entrypoints.openai.api_server ^
    --model "%MODEL%" ^
    --quantization awq_marlin ^
    --cpu-offload-gb %CPU_OFFLOAD% ^
    --enforce-eager ^
    --gpu-memory-utilization %GPU_UTIL% ^
    --max-model-len %MAX_MODEL_LEN% ^
    --host %HOST% ^
    --port %PORT%

endlocal
