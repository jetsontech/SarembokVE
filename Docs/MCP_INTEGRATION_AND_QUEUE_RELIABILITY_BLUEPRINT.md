# Architectural Blueprint: MCP Integration & Queue Reliability Remediation
**Sarembok VE AI-Native Computing Environment**  
*Document Version: 1.0.0 · Classification: Frontier Systems Architecture*

---

## Executive Summary

Sarembok VE is an AI-native sovereign computing runtime governed by the **Runtime Authority**, orchestrating 25 specialized agents, multi-model LLM fabrics (Gemini, OpenRouter, Groq), real-time duplex voice, and a SQLite-WAL state ledger. 

This document defines two strategic engineering directives:
1. **Model Context Protocol (MCP) Integration**: Establishing standardized, bleeding-edge connectivity to external databases, enterprise data lakes, and developer APIs to transform Sarembok from an isolated control plane into an expansive autonomous operational nexus.
2. **Heterogeneous Queue Reliability & Fault Remediation**: Diagnosing and resolving the sporadic failure modes observed across the 53-task queue (mixing Web Automation, Token-Bound Inference, and Meta-Human/GPU Rendering) to eliminate head-of-line blocking, lock contention, and worker capacity starvation.

---

# SECTION 1: Strategic Value of Model Context Protocol (MCP) at the Frontier

```
+-----------------------------------------------------------------------------------+
|                            SAREMBOK VE RUNTIME PLANE                              |
|   [Runtime Authority] <---> [Agent Bus: Scout / ARIA / Architect] <---> [WAL DB]   |
+-----------------------------------------------------------------------------------+
                                         │
                    Model Context Protocol (JSON-RPC / SSE)
                                         │
     ┌───────────────────┬───────────────┴───────────────┬───────────────────┐
     ▼                   ▼                               ▼                   ▼
┌──────────────┐  ┌──────────────┐               ┌──────────────┐     ┌──────────────┐
│ Database MCP │  │ DevOps / K8s │               │  Vector/KG   │     │  Engine MCP  │
│  PostgreSQL  │  │  Telemetry   │               │   Neo4j /    │     │ Unreal 5.x / │
│  ClickHouse  │  │ OpenTelemetry│               │   pgvector   │     │  Blender API │
└──────────────┘  └──────────────┘               └──────────────┘     └──────────────┘
```

### 1. Unified Context & Tooling Standardization
* **Protocol Uniformity**: Replaces disparate, custom HTTP wrappers and proprietary function-calling schemas with standard MCP (JSON-RPC over `stdio` or HTTP/SSE). Agents interact with any external system through identical primitives (`tools/list`, `tools/call`, `resources/read`, `prompts/get`).
* **Dynamic Resource & Tool Discovery**: Agents introspect attached servers at runtime rather than relying on hardcoded system prompts. This prevents prompt token bloat while giving models access to hundreds of enterprise tools on demand.
* **Stateful vs. Stateless Boundary**: MCP provides structured sessions, allowing agents to maintain persistent query contexts (e.g., active database transactions, ongoing SSH debug sessions, or stateful browser targets) without polluting the conversational dialogue state.

### 2. High-Dimensional Data & Graph Grounding
* **Hybrid Search & Knowledge Graphs**: Connecting MCP servers for graph databases (e.g., Neo4j) and vector databases (e.g., pgvector, Qdrant) enables Sarembok agents to perform multi-hop semantic traversal—combining structured relational tables with unstructured vector embeddings.
* **Live Observability & Log Telemetry**: Through MCP servers for ClickHouse, Datadog, or OpenTelemetry, Sarembok agents can pull production traces, correlate system anomalies, and verify deployment metrics autonomously during conversation.
* **Codebase & Repository Indexing**: Connecting an AST/Git MCP server allows agents to search syntax trees, track git blame graphs, and reason across large codebases with zero manual context-pasting.

### 3. Frontier & Bleeding-Edge Capabilities
* **Dynamic Tool Synthesis & Code-Mode Execution**: Rather than invoking pre-defined tools one by one, frontier models can generate and execute unified TypeScript or Python scripts that orchestrate multiple MCP tools in an isolated execution sandbox, reducing round-trip latency by up to 80%.
* **Zero-Trust Security Boundaries**: MCP servers run as isolated child processes or sidecar containers with explicit capability grants. Sensitive credentials (database passwords, cloud tokens) reside exclusively within the MCP process and are never injected into LLM prompt contexts.
* **Closed-Loop Autonomous Feedback**: MCP servers connected to compilers, headless render verifiers, and unit test suites allow agents to dispatch a change, run automated verification, parse errors, and self-correct prior to surfacing results to the user.

---

# SECTION 2: Queue Diagnostic & Remediation Playbook
**Incident Scope**: 53 tasks in active queue across three heterogeneous workloads:
* **Web Automation**: I/O-bound, headless Chromium/Playwright sessions, DOM querying, network timeouts.
* **Inference**: Token-bound, LLM provider latency, concurrency limits, API rate limiting.
* **Meta-Human Rendering**: VRAM/Compute-heavy, 3D rendering pipelines, GPU hardware dependencies.

---

### A. Root Cause Analysis (RCA)

#### 1. Heterogeneous Workload Contention & Head-of-Line Blocking
* **Symptom**: Fast inference tasks or lightweight web scripts wait behind heavy rendering jobs, or time out prematurely.
* **Root Cause**: All 53 tasks share a monolithic sequential or under-partitioned FIFO queue. When an Unreal Engine or Meta-Human render job is scheduled without dedicated worker affinity, it locks worker threads or exhausts system resources, starving concurrent I/O and inference tasks.

#### 2. Worker Capacity Mismatch (0 Online GPU Workers)
* **Symptom**: Rendering tasks fail with `worker_unavailable` or hang indefinitely in `pending` state.
* **Root Cause**: The Runtime Authority reports: `Workers: 0 online / 0 registered`, `GPU workers: 0 recognized`. Tasks requiring GPU acceleration or Unreal Engine RPC endpoints have no registered workers with matching capability tags. Without early rejection or task parking, the queue attempts repeated execution on general CPU containers where rendering libraries fail.

#### 3. SQLite-WAL Write-Lock Contention Under Rapid Transitions
* **Symptom**: Sporadic database busy errors (`sqlite3.OperationalError: database is locked`) during bursty dispatch cycles.
* **Root Cause**: With 25 agents emitting status events and 53 tasks updating state (queued → running → progress delta → completed/failed) concurrently, write transactions in SQLite collide if `busy_timeout` is set too low or long-running read transactions overlap without proper WAL checkpointing.

#### 4. Unbounded Retries & Cascading Timeouts
* **Symptom**: Sporadic failures trigger immediate retries, amplifying server load and cascading failures across adjacent jobs.
* **Root Cause**: Absence of exponential backoff with jitter and missing Dead-Letter Queue (DLQ) isolation.

---

### B. Architecture Remediation: Segregated Multi-Lane Queue

```
                     [DISPATCHER / RUNTIME AUTHORITY]
                                    │
           ┌────────────────────────┼────────────────────────┐
           ▼                        ▼                        ▼
    [LANE 1: REALTIME]       [LANE 2: WEB I/O]      [LANE 3: HEAVY COMPUTE]
    • Dialogue & Voice       • Playwright Scripts   • Meta-Human Rendering
    • Fast LLM Inference     • Browser Sessions     • Unreal Engine Jobs
    • Low Latency (<1s)      • Concurrency: 8-16    • Affinity: GPU Worker Only
           │                        │                        │
           ▼                        ▼                        ▼
   [Inference Pool]         [Browser Containers]    [Registered GPU Workers]
```

#### 1. Lane Segregation by Capability Tag
Divide the task ledger into three isolated queues:
* **Lane A (`inference`)**: Handled by lightweight asynchronous worker threads with provider failover.
* **Lane B (`browser_automation`)**: Handled by the sandboxed `sarembok-browser` container pool with strict memory boundaries (768MB limit, auto-recycle per session).
* **Lane C (`render_gpu`)**: Requires explicit worker tag `worker_tags CONTAINS "gpu-metal"` or `"gpu-cuda"`. If 0 GPU workers are online, tasks enter `PARKED_AWAITING_WORKER` state rather than failing or blocking general lanes.

#### 2. SQLite-WAL Concurrency Hardening
Configure the task ledger connection pool with resilient pragma parameters:
```sql
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA busy_timeout = 15000;      -- 15s wait on lock contention before fail
PRAGMA wal_autocheckpoint = 1000;
PRAGMA cache_size = -64000;       -- 64MB memory cache
```
* Separate the high-velocity task ledger tables into a dedicated database file (`sarembok_queue.db`) distinct from long-term conversational memory (`sarembok_memory.db`) to eliminate lock competition between live voice turns and batch background tasks.

#### 3. Dead-Letter Queue (DLQ) & Circuit Breaking
* **Max Retries**: Set strict retry ceilings (max 3 retries for transient HTTP errors; 0 retries for deterministic schema/argument validation failures).
* **Backoff Policy**: Apply exponential backoff with full jitter:
  $$\text{Delay} = \min(300, 2^{\text{attempt}} \times 2) \pm \text{jitter}(0, 1)$$
* **DLQ Auto-Quarantine**: Any task failing 3 times moves to `task_dlq` for manual inspection, freeing the active runner loop immediately.

---

### C. Implementation Roadmap

| Phase | Milestone | Expected Outcome |
| :--- | :--- | :--- |
| **Phase 1** | **Queue Partitioning & DLQ Migration** | Evacuate failed/hung tasks from the active 53-task queue into DLQ; introduce Lane A/B/C tagging. |
| **Phase 2** | **Capability Pre-Flight Check** | Reject or park Meta-Human render jobs immediately when `gpu_workers == 0`, preventing queue congestion. |
| **Phase 3** | **SQLite Ledger Separation** | Split queue processing from memory storage with tuned WAL pragmas and 15s busy timeouts. |
| **Phase 4** | **MCP Gateway Deployment** | Stand up MCP client within Runtime Authority; register Database & Observability servers. |

---

*Authored by Antigravity Systems Agent · Sarembok VE Core Architecture*
