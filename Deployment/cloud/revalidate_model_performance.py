#!/usr/bin/env python3
"""
SarembokVE — Rigorous Model Performance Revalidation
Direct Ollama API (/api/chat) Benchmark + Runtime WebSocket Comparison
Captures exact Ollama duration metrics and calculates eval_count / (eval_duration / 1e9).
"""

import asyncio
import json
import os
import statistics
import time
import urllib.request
import websockets

OLLAMA_URL = os.getenv("SAREMBOK_LOCAL_URL", "http://172.18.0.1:11434/api/chat")
WS_URL = "ws://127.0.0.1:9000"
AUTH_TOKEN = os.getenv("SAREMBOK_AUTH_TOKEN", "SqExWVt8fZF67e5azVC5f429cClU6Yje7zqZYya-hAtbme7MlonOgqU-Vd31PCd_")

MODELS = ["gemma2:2b", "qwen2.5:3b"]
TEST_PROMPT = "Write a 3-sentence summary of artificial intelligence."
SYSTEM_PROMPT = "You are Sarembok VE sovereign intelligence. Be concise and precise."
NUM_PREDICT = 512


def query_ollama_direct(model: str, prompt: str, stream: bool = False):
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        "stream": stream,
        "options": {
            "num_predict": NUM_PREDICT,
            "temperature": 0.2
        }
    }
    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=60) as resp:
        if not stream:
            data = json.loads(resp.read().decode("utf-8"))
            elapsed = time.time() - t0
            data["_client_total_latency_sec"] = elapsed
            return data
        else:
            first_token_time = None
            chunks = []
            for line in resp:
                if not line.strip():
                    continue
                chunk = json.loads(line.decode("utf-8"))
                if first_token_time is None:
                    first_token_time = time.time() - t0
                chunks.append(chunk)
                if chunk.get("done"):
                    break
            total_time = time.time() - t0
            return {
                "ttft_sec": first_token_time or total_time,
                "total_sec": total_time,
                "chunks_count": len(chunks),
                "last_chunk": chunks[-1] if chunks else {}
            }


async def query_runtime_websocket(model: str, prompt: str):
    async with websockets.connect(WS_URL, max_size=1048576) as ws:
        req = {
            "jsonrpc": "2.0",
            "id": f"ws-bench-{int(time.time()*1000)}",
            "method": "SarembokChat",
            "params": {
                "prompt": prompt,
                "model": model,
                "stream": True,
                "authToken": AUTH_TOKEN,
                "sessionId": f"bench-ws-{int(time.time())}"
            }
        }
        t0 = time.time()
        await ws.send(json.dumps(req))
        ttft = None
        chunks = []
        while True:
            raw = await ws.recv()
            msg = json.loads(raw)
            if msg.get("method") == "SarembokChat.delta":
                if ttft is None:
                    ttft = time.time() - t0
                chunks.append(msg.get("params", {}).get("text", ""))
            elif "result" in msg:
                break
        total = time.time() - t0
        return {
            "ws_ttft_sec": ttft or total,
            "ws_total_sec": total,
            "ws_chunks": len(chunks),
            "output": "".join(chunks).strip()
        }


def p95(data: list[float]) -> float:
    if not data:
        return 0.0
    s = sorted(data)
    idx = int(0.95 * len(s))
    return s[min(idx, len(s) - 1)]


def benchmark_model(model: str):
    print(f"\n=========================================================")
    print(f" BENCHMARKING MODEL: {model}")
    print(f"=========================================================")

    # 1. Warm-up run to ensure resident in memory
    print("  [0/5] Warming up model...")
    warm_resp = query_ollama_direct(model, "Warm up.")
    print(f"        Warmup load_duration: {warm_resp.get('load_duration', 0) / 1e6:.1f}ms")

    raw_runs = []
    tok_per_sec_list = []
    prompt_eval_sec_list = []
    eval_sec_list = []
    total_sec_list = []
    eval_count_list = []

    # 2. Five Repeated Warm Runs
    for run_idx in range(1, 6):
        resp = query_ollama_direct(model, TEST_PROMPT, stream=False)
        raw_runs.append(resp)

        eval_count = resp.get("eval_count", 0)
        eval_duration_ns = resp.get("eval_duration", 0)
        prompt_eval_duration_ns = resp.get("prompt_eval_duration", 0)
        total_duration_ns = resp.get("total_duration", 0)
        load_duration_ns = resp.get("load_duration", 0)

        eval_sec = eval_duration_ns / 1e9 if eval_duration_ns > 0 else 0
        prompt_eval_sec = prompt_eval_duration_ns / 1e9 if prompt_eval_duration_ns > 0 else 0
        total_sec = total_duration_ns / 1e9 if total_duration_ns > 0 else 0

        # Official Ollama tok/s formula: eval_count / (eval_duration / 1e9)
        tok_s = (eval_count / eval_sec) if eval_sec > 0 else 0.0

        tok_per_sec_list.append(tok_s)
        prompt_eval_sec_list.append(prompt_eval_sec)
        eval_sec_list.append(eval_sec)
        total_sec_list.append(total_sec)
        eval_count_list.append(eval_count)

        print(f"  [Run {run_idx}] Eval Tokens: {eval_count:3d} | Prompt Eval: {prompt_eval_sec*1000:6.1f}ms | Eval Dur: {eval_sec*1000:7.1f}ms | Total Dur: {total_sec*1000:7.1f}ms | Tok/s: {tok_s:5.2f}")

    # 3. Direct Ollama Streaming Runs (for native TTFT)
    direct_ttft_list = []
    for _ in range(3):
        stream_res = query_ollama_direct(model, TEST_PROMPT, stream=True)
        direct_ttft_list.append(stream_res["ttft_sec"])

    # 4. Runtime WebSocket Streaming Runs (for full stack TTFT)
    ws_ttft_list = []
    ws_total_list = []
    for _ in range(3):
        ws_res = asyncio.run(query_runtime_websocket(model, TEST_PROMPT))
        ws_ttft_list.append(ws_res["ws_ttft_sec"])
        ws_total_list.append(ws_res["ws_total_sec"])

    summary = {
        "model": model,
        "runs_count": len(raw_runs),
        "tokens_per_sec_median": statistics.median(tok_per_sec_list),
        "tokens_per_sec_p95": p95(tok_per_sec_list),
        "prompt_eval_ms_median": statistics.median(prompt_eval_sec_list) * 1000,
        "prompt_eval_ms_p95": p95(prompt_eval_sec_list) * 1000,
        "eval_duration_ms_median": statistics.median(eval_sec_list) * 1000,
        "eval_duration_ms_p95": p95(eval_sec_list) * 1000,
        "total_duration_ms_median": statistics.median(total_sec_list) * 1000,
        "total_duration_ms_p95": p95(total_sec_list) * 1000,
        "eval_count_median": statistics.median(eval_count_list),
        "native_ollama_ttft_ms_median": statistics.median(direct_ttft_list) * 1000,
        "native_ollama_ttft_ms_p95": p95(direct_ttft_list) * 1000,
        "runtime_ws_ttft_ms_median": statistics.median(ws_ttft_list) * 1000,
        "runtime_ws_ttft_ms_p95": p95(ws_ttft_list) * 1000,
        "raw_runs": raw_runs
    }

    print(f"\n  --- Summary for {model} ---")
    print(f"  Native Tok/s:         Median = {summary['tokens_per_sec_median']:.2f} tok/s  |  P95 = {summary['tokens_per_sec_p95']:.2f} tok/s")
    print(f"  Total Duration:       Median = {summary['total_duration_ms_median']:.1f} ms    |  P95 = {summary['total_duration_ms_p95']:.1f} ms")
    print(f"  Prompt Eval Latency:  Median = {summary['prompt_eval_ms_median']:.1f} ms     |  P95 = {summary['prompt_eval_ms_p95']:.1f} ms")
    print(f"  Direct Ollama TTFT:   Median = {summary['native_ollama_ttft_ms_median']:.1f} ms     |  P95 = {summary['native_ollama_ttft_ms_p95']:.1f} ms")
    print(f"  Runtime WS TTFT:      Median = {summary['runtime_ws_ttft_ms_median']:.1f} ms    |  P95 = {summary['runtime_ws_ttft_ms_p95']:.1f} ms")

    return summary


def main():
    print("==================================================================")
    print(" SAREMBOK VE — OFFICIAL MODEL REVALIDATION BENCHMARK")
    print(" Endpoint: " + OLLAMA_URL)
    print(" Formula:  eval_count / (eval_duration / 1e9)")
    print("==================================================================")

    all_results = {}
    for m in MODELS:
        all_results[m] = benchmark_model(m)

    output_path = "/data/raw_ollama_benchmark_evidence.json"
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(all_results, f, indent=2)
        print(f"\n[OK] Raw Ollama benchmark evidence saved to {output_path}")
    except Exception as e:
        print(f"Warning: could not write {output_path}: {e}")

    return all_results


if __name__ == "__main__":
    main()
