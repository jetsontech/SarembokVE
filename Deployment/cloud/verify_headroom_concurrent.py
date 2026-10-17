#!/usr/bin/env python3
"""
SarembokVE — Live Workload Resource Headroom Verification
Tests concurrent Kokoro TTS + Qwen 2.5 3B Chat while logging memory, swap, and CPU.
"""

import json
import subprocess
import threading
import time
import urllib.request

print("==================================================================")
print(" LIVE CONCURRENT LOAD & HEADROOM VERIFICATION")
print("==================================================================")

p1 = subprocess.check_output(["free", "-h"]).decode()
print("\n[1] HOST MEMORY BEFORE LOAD:\n" + p1)

t0 = time.time()
tts_res = {}
qwen_res = {}


def call_tts():
    try:
        t_start = time.time()
        payload = json.dumps({
            "text": "The sovereign voice synthesizer is synthesizing continuous audio for the Sarembok interface while the local neural reasoning model processes text concurrently on CPU.",
            "voice": "af_heart"
        }).encode()
        req = urllib.request.Request("http://172.18.0.2:9200/tts/stream", data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read()
            tts_res["bytes"] = len(data)
            tts_res["time"] = time.time() - t_start
    except Exception as e:
        tts_res["err"] = str(e)


def call_qwen():
    try:
        t_start = time.time()
        payload = json.dumps({
            "model": "qwen2.5:3b",
            "messages": [{"role": "user", "content": "Analyze the impact of CPU caching on sovereign language model inference. Provide three concise points."}],
            "stream": False
        }).encode()
        req = urllib.request.Request("http://172.18.0.1:11434/api/chat", data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode())
            qwen_res["tokens"] = data.get("eval_count")
            qwen_res["time"] = time.time() - t_start
            qwen_res["tok_s"] = data.get("eval_count", 0) / (data.get("eval_duration", 1) / 1e9)
    except Exception as e:
        qwen_res["err"] = str(e)


t_tts = threading.Thread(target=call_tts)
t_qwen = threading.Thread(target=call_qwen)

print("[2] Dispatching concurrent requests (Kokoro TTS + Qwen 2.5 3B)...")
t_tts.start()
t_qwen.start()
t_tts.join()
t_qwen.join()

tts_elapsed = tts_res.get("time", 0)
tts_bytes = tts_res.get("bytes", 0)
tts_err = tts_res.get("err", None)
qwen_elapsed = qwen_res.get("time", 0)
qwen_tokens = qwen_res.get("tokens", 0)
qwen_toks = qwen_res.get("tok_s", 0)
qwen_err = qwen_res.get("err", None)

print(f"\n[3] EXECUTION RESULTS:")
print(f"    - Kokoro TTS Duration: {tts_elapsed:.2f}s | Output: {tts_bytes} bytes audio PCM (Error: {tts_err})")
print(f"    - Qwen Chat Duration:  {qwen_elapsed:.2f}s | Output: {qwen_tokens} tokens ({qwen_toks:.2f} tok/s, Error: {qwen_err})")

p2 = subprocess.check_output(["free", "-h"]).decode()
print("\n[4] HOST MEMORY AFTER LOAD:\n" + p2)

p3 = subprocess.check_output(["ollama", "ps"], env={"HOME": "/home/ubuntu", "OLLAMA_HOST": "http://172.18.0.1:11434", "PATH": "/usr/local/bin:/usr/bin:/bin"}).decode()
print("[5] OLLAMA MODEL RESIDENCY:\n" + p3)

p4 = subprocess.check_output(["docker", "stats", "--no-stream"]).decode()
print("[6] DOCKER CONTAINER HEALTH & USAGE:\n" + p4)
