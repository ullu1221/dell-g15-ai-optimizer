#!/usr/bin/env python3
"""
GGUF Downloader with Resumption for Dell G15 5530
Safely downloads verified, high-accuracy quantized models from Hugging Face.
"""

import argparse
import os
import sys
from pathlib import Path
from urllib.request import Request, urlopen

PRESETS = {
    "qwen14b": {
        "repo": "Qwen/Qwen2.5-14B-Instruct-GGUF",
        "file": "qwen2.5-14b-instruct-q4_k_m.gguf",
        "description": "14B general reasoning & instruction hybrid champion (~8.5GB)",
    },
    "qwen7b-coder": {
        "repo": "Qwen/Qwen2.5-Coder-7B-Instruct-GGUF",
        "file": "qwen2.5-coder-7b-instruct-q5_k_m.gguf",
        "description": "7B coding specialist, full GPU fit with Q5_K_M (~5.4GB)",
    },
    "hermes8b": {
        "repo": "NousResearch/Hermes-3-Llama-3.1-8B-GGUF",
        "file": "Hermes-3-Llama-3.1-8B.Q4_K_M.gguf",
        "description": "8B multi-turn roleplay & autonomous agent model (~4.9GB)",
    },
}


def download_with_hf_hub(repo_id: str, filename: str, output_dir: Path):
    try:
        from huggingface_hub import hf_hub_download
        print(f"[+] Downloading using huggingface_hub: {repo_id}/{filename}")
        path = hf_hub_download(
            repo_id=repo_id,
            filename=filename,
            local_dir=str(output_dir),
            local_dir_use_symlinks=False,
            resume_download=True,
        )
        print(f"[✓] Successfully downloaded to: {path}")
        return path
    except ImportError:
        print("[!] huggingface_hub not installed, falling back to direct stream download...")
        url = f"https://huggingface.co/{repo_id}/resolve/main/{filename}"
        dest = output_dir / filename
        return download_direct_url(url, dest)


def download_direct_url(url: str, dest: Path):
    dest.parent.mkdir(parents=True, exist_ok=True)
    temp_file = dest.with_suffix(dest.suffix + ".part")
    
    headers = {"User-Agent": "dell-g15-ai-optimizer/1.0"}
    existing_bytes = 0
    if temp_file.exists():
        existing_bytes = temp_file.stat().st_size
        headers["Range"] = f"bytes={existing_bytes}-"
        print(f"[+] Resuming download from {existing_bytes / (1024**2):.1f} MB...")

    req = Request(url, headers=headers)
    try:
        with urlopen(req, timeout=30) as resp, open(temp_file, "ab" if existing_bytes else "wb") as f:
            total_size = resp.headers.get("Content-Length")
            total_bytes = int(total_size) + existing_bytes if total_size else None
            
            chunk_size = 1024 * 1024  # 1MB
            downloaded = existing_bytes
            print(f"[+] Streaming from {url}")
            
            while True:
                chunk = resp.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if total_bytes:
                    pct = (downloaded / total_bytes) * 100
                    mb = downloaded / (1024**2)
                    total_mb = total_bytes / (1024**2)
                    sys.stdout.write(f"\r[Progress] {mb:.1f}/{total_mb:.1f} MB ({pct:.1f}%)")
                    sys.stdout.flush()
                else:
                    sys.stdout.write(f"\r[Progress] {downloaded / (1024**2):.1f} MB")
                    sys.stdout.flush()

        print("\n[+] Finalizing download...")
        temp_file.rename(dest)
        print(f"[✓] Saved model to {dest}")
        return str(dest)
    except Exception as e:
        print(f"\n[ERROR] Download failed: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Download optimized GGUF models for Dell G15 5530.")
    parser.add_argument(
        "--preset",
        choices=list(PRESETS.keys()),
        default="qwen14b",
        help="Select preset model to download",
    )
    parser.add_argument("--repo", help="Custom Hugging Face repo ID")
    parser.add_argument("--file", help="Custom GGUF filename in repository")
    parser.add_argument(
        "--outdir",
        default=os.path.expanduser("~/models"),
        help="Destination directory for model weights (default: ~/models)",
    )
    args = parser.parse_args()

    out_dir = Path(args.outdir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.repo and args.file:
        repo = args.repo
        filename = args.file
    else:
        preset_info = PRESETS[args.preset]
        repo = preset_info["repo"]
        filename = preset_info["file"]
        print(f"[i] Preset: {args.preset} - {preset_info['description']}")

    download_with_hf_hub(repo, filename, out_dir)


if __name__ == "__main__":
    main()
