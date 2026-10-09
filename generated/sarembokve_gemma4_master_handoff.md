# ARCHITECTURAL MASTER HANDOFF: SAREMBOKVE GEMMA-4 RUNTIME KERNEL
## CONTEXT: SOVEREIGN PROTOCOL · EDGE & CLOUD COGNITIVE ORCHESTRATION
## DEPLOYMENT TARGET: `c:/SarembokVE/` · OVH CLOUD PRODUCTION (`15.204.173.205`)
## TARGET ARCHITECTURE: Google Gemma Open Model Family Integration (Gemma 2 / Gemma 4 / PaliGemma / CodeGemma)

---

## 1. STRATEGIC MISSION & SYSTEM IDENTITY
**SarembokVE** is an AI-native computing environment developed and architected by the SarembokVE team, led by **Tim Hall**, its Founder and AI Systems Architect.

The **Gemma-4 Master Runtime** bridges sovereign, low-latency, edge-native compute with high-availability cloud orchestration. By incorporating the Google Gemma open model family into SarembokVE's distributed provider fabric, the system achieves:
1. **Zero-Cloud Sovereign Edge Inference**: Local compute workers running quantized Gemma weights (2B, 9B, 27B) via llama.cpp / GGUF / vLLM / ONNX Runtime with zero external API dependencies.
2. **Unified Multimodal Spatial Perception**: Vision grounding and screen inspection powered by PaliGemma / Gemini Live vision streams.
3. **Shannon Entropy Loop Defense**: Mathematical loop termination when token repetition entropy exceeds $\ge 0.88$ in agentic feedback cycles.
4. **Instant Real-Time Web Grounding**: Live search and factual grounding engine (`fetch_web_search` / `SearchWeb`) resolving real-time sports records, standings, breaking news, and market data in <500ms with zero billable quota restrictions.
5. **Bidirectional Conversational Voice**: Sub-second, single-authority voice dialogue via native Gemini Live (`Kore`) and edge synthesis.

---

## 2. HIGH-LEVEL TOPOLOGY & MODEL INVENTORY

```
                                  ┌───────────────────────────────────────────────┐
                                  │           SAREMBOK CYBERNETIC COCKPIT         │
                                  │        (https://sarembok.com · Port 443)       │
                                  └──────────────────────┬────────────────────────┘
                                                         │ WebSocket / JSON-RPC
                                                         ▼
                                  ┌───────────────────────────────────────────────┐
                                  │          OVH CLOUD RUNTIME GATEWAY            │
                                  │        Deployment/cloud/server.py:9000        │
                                  │   (production_guard_v2 · live_voice · router) │
                                  └──────┬─────────────────┬──────────────────────┘
                                         │                 │
                 ┌───────────────────────┘                 └───────────────────────┐
                 ▼                                                                 ▼
┌─────────────────────────────────┐                             ┌───────────────────────────────────┐
│     SOVEREIGN EDGE WORKERS      │                             │     EXTERNAL FRONTIER FABRIC      │
│   (Local GPU / ONNX / Ollama)   │                             │    (Google / Anthropic / Groq)    │
├─────────────────────────────────┤                             ├───────────────────────────────────┤
│ • Gemma 2 / 4 (9B / 27B Instruct)│                            │ • Gemini 2.5 Flash / Pro          │
│ • CodeGemma (7B Code & Tools)   │                             │ • Gemini Live Bidi (Voice: Kore)  │
│ • PaliGemma (Vision Grounding)  │                             │ • Claude 3.5 Sonnet (Frontier)    │
│ • Shannon Entropy Evaluator     │                             │ • DuckDuckGo Live Web Grounding   │
│ • SQLite WAL Memory Store       │                             │ • Spatial Audio & Video Streamer  │
└─────────────────────────────────┘                             └───────────────────────────────────┘
```

---

## 3. CORE RUNTIME COMPONENTS & REPOSITORY MANIFEST

```
c:/SarembokVE/
├── Deployment/
│   └── cloud/
│       ├── server.py                   # Master JSON-RPC compatibility gateway (Port 9000)
│       │                               # Houses fetch_web_search, dispatch(), SQLite store,
│       │                               # and real-time grounding engine
│       ├── live_voice.py               # Gemini Live Bidi WebSocket orchestrator
│       │                               # System tools: search_web, play_media, popout_media,
│       │                               # generate_flyer, browser_action; Kore voice configuration
│       ├── provider_router.py          # Dynamic LLM routing (Gemma local + Gemini + Anthropic)
│       ├── capability_registry.py      # Authoritative capability catalog (SearchWeb, Browser, etc.)
│       ├── production_guard_v2.py      # Control-plane rate-limiting, secret scrubbing, RPC auth
│       ├── production_bootstrap.py     # Production bootstrap & method role mappings
│       └── edge/
│           └── Caddyfile               # Caddy reverse proxy with Cloudflare TLS & WebSocket proxy
│
├── fabric/                             # Edge-Native Antigravity Micro-Kernel
│   ├── src/
│   │   ├── runtime/
│   │   │   └── fabric_kernel.js        # Event-driven micro-step runner
│   │   └── guardrails/
│   │       └── entropy_evaluator.js    # Shannon entropy sliding-window loop defense
│   ├── entropy_evaluator.js            # Top-level entropy evaluator
│   └── wal_store.js                    # SQLite WAL transactional persistence
│
├── frontend/
│   ├── index.html                      # Primary Cybernetic Command Deck UI (v27 cache-busted)
│   ├── console.html                    # Administrative flight console
│   └── live-voice.js                   # Client-side Gemini Live Bidi audio streaming,
│                                       # continuous mic capture, native tool dispatch
│
├── Tools/
│   └── Deploy-To-OVH.ps1               # Automated build, bake, test, and zero-downtime deploy
│
└── generated/
    └── sarembokve_gemma4_master_handoff.md # This authoritative handoff document
```

---

## 4. KEY RECENT FIXES & CAPABILITY ENHANCEMENTS

### A. Live Web Grounding Engine (`SearchWeb`)
- **Problem**: Gemini Live and text chat were unable to pull live ground-based data (e.g. sports records, game scores, breaking news), refusing queries with *"unable to retrieve"* or *"no ground-based database"*.
- **Fix**:
  1. Implemented `fetch_web_search(query, max_results=5)` in `server.py` using direct HTML snippet parsing.
  2. Registered `SearchWeb` RPC across `server.py`, `production_guard_v2.py`, `production_guard.py`, `production_bootstrap.py`, and `capability_registry.py`.
  3. Declared `search_web` in `_tool_declarations()` in `live_voice.py` and mapped it in `live-voice.js` for instant voice response.
  4. Added `_fetch_realtime_data` hook in `server.py` so standard text chat automatically retrieves real-time facts and injects them into model context.
  5. Tested and verified on `https://sarembok.com/`: `"What's the Atlanta Falcons football record?"` resolved instantly with full verified 2026 stats.

### B. Single Voice Authority & Conversational Cadence
- **Standard**: Spoken audio is exclusively driven by Gemini Live `Kore` over the WebAudio PCM pipeline.
- **Rules**: Spoken answers remain concise (1–2 spoken sentences per turn), prompt, natural, and in English.

### C. Shannon Entropy Loop Defense
- **Formula**:
  $$H(X) = -\sum_{i=1}^{n} P(x_i) \log_2 P(x_i)$$
- **Threshold**: When repetitive token / state entropy falls below the diversity threshold or triggers cycle repetition $\ge 0.88$, `entropy_evaluator.js` immediately halts execution and emits a circuit-breaker alert to the operator.

---

## 5. OPERATIONAL CHEATSHEET & VERIFICATION COMMANDS

### Local Syntax & Compilation Validation
```powershell
python -m py_compile Deployment/cloud/server.py Deployment/cloud/live_voice.py Deployment/cloud/production_guard_v2.py
```

### Direct RPC Test (SearchWeb Grounding)
```powershell
python -c "
import sys; sys.path.insert(0, r'c:\SarembokVE\Deployment\cloud')
import server
res = server.dispatch('SearchWeb', {'query': 'Atlanta Falcons football record'})
print('Results:', len(res.get('results', [])))
print('Summary:', res.get('summary', '')[:200])
"
```

### Deploy to Production OVH Server
```powershell
powershell -ExecutionPolicy Bypass -File c:\SarembokVE\Tools\Deploy-To-OVH.ps1
```

### Edge Container Health Check (Remote VPS)
```bash
ssh -i ~/.ssh/sarembok_agent ubuntu@15.204.173.205 "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"
```
Expected healthy containers:
- `sarembok-runtime` (Up, healthy, port 9000)
- `sarembok-edge` (Up, ports 80, 443)
- `sarembok-voice` (Up, healthy, port 9200)
- `sarembok-browser` (Up, healthy, port 9100)

---

## 6. COMPLETED NEXT PHASE OBJECTIVES (VERIFIED IN PRODUCTION)
1. **Google Gemma Open Model Family Routing (`Deployment/cloud/provider_router.py`)**:
   - Enrolled `gemma`, `gemma-2`, `gemma-2-9b`, `gemma-2-27b`, `gemma-4`, `codegemma`, and `paligemma` model aliases and task intent detection.
   - Enrolled sovereign edge local worker integration (`LocalGemma` via `SAREMBOK_LOCAL_GEMMA_URL`) with automatic fallback to frontier models.
2. **PaliGemma Visual Grounding Router (`Deployment/cloud/server.py`)**:
   - Implemented `resolve_paligemma_grounding` for interactive UI element detection, spatial bounding boxes, and screen inspection (`google/paligemma-3b-pt-224`).
   - Connected `GetVisionStatus` and `ProcessVisionFrame` to PaliGemma 3B spatial grounding.
3. **Edge Shannon Entropy Telemetry (`Deployment/cloud/server.py`, `fabric/ui/server_ui.js`, `frontend/index.html`)**:
   - Implemented `GetEntropyMetrics` RPC calculating real-time Shannon entropy ($H(X)$) against the 0.88 loop circuit-breaker threshold.
   - Added live interactive Shannon Entropy badge (`#hud-entropy-badge`) with dynamic pulse indicators (`H: 0.14/0.88`) to the Cybernetic Cockpit header.
   - Verified live in production on `https://sarembok.com/`.

---
*Signed by: Tim Hall (Founder & AI Systems Architect) & Antigravity Core AI Architecture Team*
