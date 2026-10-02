#!/usr/bin/env python3
"""
AWQ Model Downloader for Dell G15 5530
Downloads 4-bit AWQ models optimized for Marlin tensor-core acceleration in vLLM.
"""

import argparse
import os
import sys

RECOMMENDED_AWQ_MODELS = {
    "qwen7b-coder": {
        "repo_id": "Qwen/Qwen2.5-Coder-7B-Instruct-AWQ",
        "description": "Best 7B coding model, Marlin accelerated on RTX 3050 (~4.5GB)",
    },
    "qwen7b": {
        "repo_id": "Qwen/Qwen2.5-7B-Instruct-AWQ",
        "description": "General instruction 7B model, 4-bit AWQ (~4.4GB)",
    },
    "llama8b": {
        "repo_id": "hugging-quants/Meta-Llama-3.1-8B-Instruct-AWQ-INT4",
        "description": "Llama 3.1 8B Instruct INT4 AWQ (~5.4GB)",
    },
}


def download_awq(repo_id: str, local_dir: str):
    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        print("[ERROR] huggingface_hub is required. Install with: pip install huggingface_hub")
        sys.exit(1)

    print(f"[+] Starting download of {repo_id}...")
    print(f"[+] Destination: {local_dir}")
    os.makedirs(local_dir, exist_ok=True)

    path = snapshot_download(
        repo_id=repo_id,
        local_dir=local_dir,
        local_dir_use_symlinks=False,
        resume_download=True,
        ignore_patterns=["*.msgpack", "*.h5", "optimizer.pt"],
    )
    print(f"[✓] Model successfully downloaded to: {path}")
    print("\nTo serve with vLLM run:")
    print(f"  ./serve_vllm.sh {path}")
    return path


def main():
    parser = argparse.ArgumentParser(description="Download AWQ models for vLLM serving.")
    parser.add_argument(
        "--preset",
        choices=list(RECOMMENDED_AWQ_MODELS.keys()),
        default="qwen7b-coder",
        help="Select recommended preset AWQ model",
    )
    parser.add_argument("--repo", help="Custom Hugging Face AWQ repository ID")
    parser.add_argument(
        "--outdir",
        default=None,
        help="Custom output directory (default: ~/models/<model-name>)",
    )
    args = parser.parse_args()

    if args.repo:
        repo_id = args.repo
        model_name = repo_id.split("/")[-1]
    else:
        preset_info = RECOMMENDED_AWQ_MODELS[args.preset]
        repo_id = preset_info["repo_id"]
        model_name = repo_id.split("/")[-1]
        print(f"[i] Preset: {args.preset} - {preset_info['description']}")

    target_dir = args.outdir or os.path.expanduser(f"~/models/{model_name}")
    download_awq(repo_id, target_dir)


if __name__ == "__main__":
    main()
