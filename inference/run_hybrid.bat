@echo off
REM ==============================================================================
REM Minimal-Loss Hybrid Inference Launcher for Dell G15 5530 (Windows 11 / 10)
REM Hardware: NVIDIA RTX 3050 (6GB VRAM) + Intel i5-13450HX (6 P-cores)
REM
REM Processor Affinity:
REM   Affinity mask 0x555 (hex) = Binary 0000 0101 0101 0101
REM   Pins process exclusively to physical P-cores (CPU 0, 2, 4, 6, 8, 10).
REM   Prevents Windows thread scheduler from dumping tokens on efficiency cores.
REM ==============================================================================

setlocal enabledelayedexpansion

set "MODEL=%~1"
if "%MODEL%"=="" (
    set "MODEL=%USERPROFILE%\models\Qwen2.5-14B-Instruct-Q4_K_M.gguf"
)

if not exist "!MODEL!" (
    echo [ERROR] Model file not found: !MODEL!
    echo Usage: %~nx0 ^<path-to-model.gguf^> [cli^|server]
    exit /b 1
)

set "MODE=%~2"
if "%MODE%"=="" set "MODE=cli"

set "NGL=24"
set "THREADS=6"
set "CTX=8192"

echo ==========================================================
echo  Starting Minimal-Loss Hybrid Inference (Windows)
echo  Model:       !MODEL!
echo  GPU Layers:  %NGL% layers offloaded to VRAM
echo  CPU Threads: %THREADS% threads (Pinned to P-cores: Affinity 0x555)
echo  Context:     %CTX% tokens (Q8_0 KV Cache + FlashAttention)
echo  Sampling:    Min-P 0.05 ^| Temp 0.6 ^| Repeat-Penalty 1.05
echo  Mode:        %MODE%
echo ==========================================================

if /i "%MODE%"=="server" (
    start /affinity 0x555 /b /wait llama-server.exe ^
        -m "!MODEL!" ^
        -ngl %NGL% ^
        -t %THREADS% ^
        -c %CTX% ^
        -fa on ^
        -ctk q8_0 ^
        -ctv q8_0 ^
        --host 0.0.0.0 ^
        --port 8080
) else (
    start /affinity 0x555 /b /wait llama-cli.exe ^
        -m "!MODEL!" ^
        -ngl %NGL% ^
        -t %THREADS% ^
        -c %CTX% ^
        -fa on ^
        -ctk q8_0 ^
        -ctv q8_0 ^
        --temp 0.6 ^
        --min-p 0.05 ^
        --repeat-penalty 1.05
)

endlocal
