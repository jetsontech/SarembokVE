#!/usr/bin/env python3
"""Comparative Evaluation: gemma2:2b vs qwen2.5:3b on SarembokVE Runtime."""

import asyncio
import json
import os
import time
import urllib.request
import websockets

AUTH_TOKEN = os.getenv("SAREMBOK_AUTH_TOKEN", "SqExWVt8fZF67e5azVC5f429cClU6Yje7zqZYya-hAtbme7MlonOgqU-Vd31PCd_")
WS_URL = "ws://127.0.0.1:9000"
VOICE_URL = os.getenv("SAREMBOK_VOICE_URL", "http://sarembok-voice:9200")


async def benchmark_model(model_name: str) -> dict:
    print(f"\n========================================================")
    print(f" BENCHMARKING: {model_name}")
    print(f"========================================================")
    
    metrics = {"model": model_name}

    async with websockets.connect(WS_URL, max_size=1048576) as ws:
        # 1. Normal Chat Response & Latency
        req1 = {
            "jsonrpc": "2.0",
            "id": f"bench-norm-{model_name}",
            "method": "SarembokChat",
            "params": {
                "prompt": "What is the capital city of France? Answer in one complete sentence.",
                "model": model_name,
                "authToken": AUTH_TOKEN,
                "sessionId": f"bench-session-{model_name}-1",
            }
        }
        t0 = time.time()
        await ws.send(json.dumps(req1))
        res1 = json.loads(await ws.recv())["result"]
        t1 = (time.time() - t0) * 1000
        metrics["normal_latency_ms"] = t1
        metrics["normal_reply"] = res1.get("response", "").strip()
        print(f"  [1] Normal Latency: {t1:.1f}ms | Reply: {metrics['normal_reply'][:60]}")

        # 2. Streaming Inference (TTFT & Throughput)
        req2 = {
            "jsonrpc": "2.0",
            "id": f"bench-stream-{model_name}",
            "method": "SarembokChat",
            "params": {
                "prompt": "Write a 3-sentence summary of artificial intelligence.",
                "model": model_name,
                "stream": True,
                "authToken": AUTH_TOKEN,
                "sessionId": f"bench-session-{model_name}-2",
            }
        }
        t0 = time.time()
        await ws.send(json.dumps(req2))
        chunks = []
        ttft = None
        while True:
            raw = await ws.recv()
            msg = json.loads(raw)
            if msg.get("method") == "SarembokChat.delta":
                if ttft is None:
                    ttft = (time.time() - t0) * 1000
                chunks.append(msg.get("params", {}).get("text", ""))
            elif "result" in msg:
                break
        total_stream_time = (time.time() - t0) * 1000
        total_tokens = len(chunks)
        gen_duration_sec = (total_stream_time - (ttft or 0)) / 1000.0
        tok_per_sec = (total_tokens / gen_duration_sec) if gen_duration_sec > 0 else 0

        metrics["stream_ttft_ms"] = ttft or 0
        metrics["stream_total_ms"] = total_stream_time
        metrics["stream_chunks"] = total_tokens
        metrics["tokens_per_sec"] = tok_per_sec
        print(f"  [2] Streaming TTFT: {ttft:.1f}ms | Total: {total_stream_time:.1f}ms | Tok/s: {tok_per_sec:.2f}")

        # 3. Agent Tool Call / Structured Intent Resolution
        req3 = {
            "jsonrpc": "2.0",
            "id": f"bench-tool-{model_name}",
            "method": "SarembokChat",
            "params": {
                "prompt": "Remember that cluster worker 4 is scheduled for maintenance tonight",
                "model": model_name,
                "authToken": AUTH_TOKEN,
                "sessionId": f"bench-session-{model_name}-3",
            }
        }
        await ws.send(json.dumps(req3))
        res3 = json.loads(await ws.recv())["result"]
        metrics["tool_action"] = res3.get("action")
        print(f"  [3] Tool Intent: {metrics['tool_action']}")

        # 4. Complex Reasoning / Code Generation
        req4 = {
            "jsonrpc": "2.0",
            "id": f"bench-code-{model_name}",
            "method": "SarembokChat",
            "params": {
                "prompt": "Write a Python function to compute the Fibonacci sequence up to n terms.",
                "model": model_name,
                "authToken": AUTH_TOKEN,
                "sessionId": f"bench-session-{model_name}-4",
            }
        }
        t0 = time.time()
        await ws.send(json.dumps(req4))
        res4 = json.loads(await ws.recv())["result"]
        code_time = (time.time() - t0) * 1000
        code_text = res4.get("response", "").strip()
        metrics["code_latency_ms"] = code_time
        metrics["code_has_def"] = "def fibonacci" in code_text.lower() or "def fib" in code_text.lower()
        print(f"  [4] Code Generation: {code_time:.1f}ms | Valid Python Def: {metrics['code_has_def']}")

        # 5. Concurrent Kokoro TTS Load
        async def call_tts():
            t_tts = time.time()
            payload = json.dumps({"text": "Benchmarking parallel neural voice synthesis.", "voice": "af_heart"}).encode("utf-8")
            req = urllib.request.Request(f"{VOICE_URL}/tts/stream", data=payload, headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = resp.read()
            return (time.time() - t_tts) * 1000, len(data)

        async def call_chat():
            t_chat = time.time()
            req_c = {
                "jsonrpc": "2.0",
                "id": f"bench-conc-{model_name}",
                "method": "SarembokChat",
                "params": {
                    "prompt": "What is 15 multiplied by 4? Answer in a complete sentence.",
                    "model": model_name,
                    "authToken": AUTH_TOKEN,
                    "sessionId": f"bench-session-{model_name}-5",
                }
            }
            await ws.send(json.dumps(req_c))
            r = json.loads(await ws.recv())["result"]
            return (time.time() - t_chat) * 1000, r.get("response", "").strip()

        (tts_ms, tts_bytes), (chat_conc_ms, chat_reply) = await asyncio.gather(call_tts(), call_chat())
        metrics["concurrent_tts_ms"] = tts_ms
        metrics["concurrent_chat_ms"] = chat_conc_ms
        metrics["concurrent_chat_reply"] = chat_reply
        print(f"  [5] Concurrent Test: TTS {tts_ms:.1f}ms | Chat {chat_conc_ms:.1f}ms (Reply: {chat_reply[:60]})")

    return metrics


async def main():
    print("==================================================================")
    print(" SAREMBOK VE — COMPARATIVE LOCAL MODEL EVALUATION")
    print(" Candidate 1: gemma2:2b (2.6B, Q4_0, 1.6 GB)")
    print(" Candidate 2: qwen2.5:3b (3.1B, Q4_K_M, 1.9 GB)")
    print("==================================================================")
    
    gemma_results = await benchmark_model("gemma2:2b")
    # Brief pause to allow CPU threads to settle
    await asyncio.sleep(2)
    qwen_results = await benchmark_model("qwen2.5:3b")

    print("\n\n==================================================================")
    print(" COMPARATIVE SUMMARY MATRIX")
    print("==================================================================")
    print(f"{'Metric':<30} | {'gemma2:2b':<22} | {'qwen2.5:3b':<22}")
    print("-" * 80)
    print(f"{'Weight Size on Disk':<30} | {'1.63 GB':<22} | {'1.91 GB':<22}")
    print(f"{'Normal Latency (ms)':<30} | {gemma_results['normal_latency_ms']:<22.1f} | {qwen_results['normal_latency_ms']:<22.1f}")
    print(f"{'Streaming TTFT (ms)':<30} | {gemma_results['stream_ttft_ms']:<22.1f} | {qwen_results['stream_ttft_ms']:<22.1f}")
    print(f"{'Streaming Total (ms)':<30} | {gemma_results['stream_total_ms']:<22.1f} | {qwen_results['stream_total_ms']:<22.1f}")
    print(f"{'Generation Tok/s':<30} | {gemma_results['tokens_per_sec']:<22.2f} | {qwen_results['tokens_per_sec']:<22.2f}")
    print(f"{'Code Gen Latency (ms)':<30} | {gemma_results['code_latency_ms']:<22.1f} | {qwen_results['code_latency_ms']:<22.1f}")
    print(f"{'Code Syntactically Valid':<30} | {str(gemma_results['code_has_def']):<22} | {str(qwen_results['code_has_def']):<22}")
    print(f"{'Concurrent Chat (ms)':<30} | {gemma_results['concurrent_chat_ms']:<22.1f} | {qwen_results['concurrent_chat_ms']:<22.1f}")
    print(f"{'Concurrent Kokoro (ms)':<30} | {gemma_results['concurrent_tts_ms']:<22.1f} | {qwen_results['concurrent_tts_ms']:<22.1f}")

    with open("/app/benchmark_results.json", "w") as f:
        json.dump({"gemma": gemma_results, "qwen": qwen_results}, f, indent=2)


if __name__ == "__main__":
    asyncio.run(main())
