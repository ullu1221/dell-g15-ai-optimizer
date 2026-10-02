#!/usr/bin/env python3
"""
High-Precision Benchmark & Inference Test Client
Connects to vLLM (port 8000) or llama-server (port 8080) via OpenAI API standard.
Measures Time-To-First-Token (TTFT), token generation speed, and response latency.
"""

import argparse
import json
import sys
import time
import urllib.request


def test_endpoint(base_url: str, prompt: str, max_tokens: int = 128, temperature: float = 0.6):
    endpoint = f"{base_url.rstrip('/')}/chat/completions"
    payload = {
        "messages": [
            {"role": "system", "content": "You are a concise, helpful programming assistant."},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": True,
    }

    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    print(f"[+] Connecting to {endpoint}...")
    start_time = time.perf_counter()
    first_token_time = None
    token_count = 0
    full_response = []

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            for line in resp:
                line_str = line.decode("utf-8").strip()
                if not line_str.startswith("data: "):
                    continue
                data_str = line_str[6:].strip()
                if data_str == "[DONE]":
                    break
                try:
                    data = json.loads(data_str)
                    delta = data["choices"][0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        if first_token_time is None:
                            first_token_time = time.perf_counter()
                        token_count += 1
                        full_response.append(content)
                        sys.stdout.write(content)
                        sys.stdout.flush()
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        print(f"\n[ERROR] Connection failed: {e}")
        sys.exit(1)

    end_time = time.perf_counter()
    print("\n" + "=" * 50)
    
    total_latency = end_time - start_time
    ttft = (first_token_time - start_time) if first_token_time else 0.0
    gen_time = (end_time - first_token_time) if first_token_time else 0.0
    tps = token_count / gen_time if gen_time > 0 else 0.0

    print(f"Tokens Generated:      {token_count}")
    print(f"Time To First Token:   {ttft * 1000:.2f} ms")
    print(f"Generation Speed:      {tps:.2f} tokens/sec")
    print(f"Total Turnaround:      {total_latency:.2f} s")
    print("=" * 50)


def main():
    parser = argparse.ArgumentParser(description="Test and benchmark local OpenAI-compatible inference servers.")
    parser.add_argument(
        "--url",
        default="http://localhost:8000/v1",
        help="Server API base URL (default: http://localhost:8000/v1 for vLLM, use http://localhost:8080/v1 for llama-server)",
    )
    parser.add_argument(
        "--prompt",
        default="Explain the mathematical principle behind FlashAttention in 3 concise bullet points.",
        help="Prompt text for benchmarking",
    )
    parser.add_argument("--tokens", type=int, default=150, help="Maximum tokens to generate")
    args = parser.parse_args()

    test_endpoint(args.url, args.prompt, args.tokens)


if __name__ == "__main__":
    main()
