# SAREMBOK VE — ARCHITECTURE v1.1 CODEBASE AUDIT
## Architecture-to-Code Baseline
**Date:** 2026-08-18
**Repository:** `jetsontech/SarembokVE`
**Base:** `main`
**Status:** AUDIT BASELINE — implementation changes intentionally excluded

## 1. Executive Assessment

The repository already contains meaningful Sarembok platform foundations: a cloud runtime, production deployment, worker lifecycle tooling, JSON-RPC infrastructure, and an Unreal plugin family spanning core, agent, avatar, memory, vision, voice, governance, and bridge concerns. The architecture is therefore beyond a blank prototype.

However, the current codebase is best described as **a functioning runtime/integration foundation plus multiple capability modules**, not yet the complete AI-native computing platform described by the Master Blueprint.

The most important architectural finding is that the Unreal bridge currently initializes the WebSocket connection during module startup. The code path is:

`FSarembokBridgeModule::StartupModule()` → `USarembokRuntimeManager::InitializeRuntime()` → `FSarembokBridgeService::Initialize()` → `FSarembokWebSocketClient::Connect()`.

This creates a startup-coupling problem: editor/module startup depends on a network client being initialized immediately. The bridge should eventually become lifecycle-safe, asynchronous, and non-blocking.

A second important finding is that the production authentication contract exists in Docker Compose, while the Unreal client currently defaults to an empty token and a local development URL. Production configuration is therefore an explicit deployment/client concern and should be moved behind a secure configuration provider rather than hard-coded or manually injected into gameplay code.

A third finding is security-related: `Config/DefaultEngine.ini` currently contains an `AndroidFileServerEditor` `SecurityToken` value in the public repository. Treat this value as exposed and rotate it before production distribution if it is still active.

## 2. Repository Reality vs Master Architecture

| Domain | Current Assessment | Status | Evidence / Gap |
|---|---|---:|---|
| Sarembok Core / Runtime | Cloud runtime and RPC server exist | 🟢 Foundation operational | `Deployment/cloud/server.py` |
| Production Deployment | Docker + Caddy production configuration exists | 🟢 Operational foundation | `Deployment/cloud/compose.production.yaml` |
| Authentication | Server-side production token contract exists | 🟢 Foundation operational | Compose requires `SAREMBOK_AUTH_TOKEN` |
| Worker Fabric | Worker client and lifecycle tests exist | 🟢 Foundation operational | `worker_client.py`, `test_worker_lifecycle.py` |
| JSON-RPC | Runtime RPC surface exists | 🟢 Foundation operational | `server.py`, smoke tests |
| Unreal Bridge | Substantial C++ bridge exists | 🟡 Development | Multiple bridge services/routers/dispatchers |
| Agent | Dedicated Unreal agent plugin exists | 🟡 Development | `Plugins/SarembokAgent` |
| Memory | Dedicated Unreal memory plugin exists | 🟡 Development | `Plugins/SarembokMemory` |
| Vision | Dedicated Unreal vision plugin exists | 🟡 Development | `Plugins/SarembokVision` |
| Voice | Dedicated Unreal voice plugin exists | 🟡 Development | `Plugins/SarembokVoice` |
| Avatar / MetaHuman | Avatar plugin and MetaHuman metadata exist | 🟡 Development | `Plugins/SarembokAvatar`, `Content/MetaHuman` |
| Governance | Governance plugin + repository governance docs exist | 🟡 Development | `SarembokGovernance`, `Governance/` |
| Computer Vision / OpenCV | Architectural target; implementation needs explicit capability validation | 🔵 Planned | No repository evidence in this audit proving an end-to-end OpenCV pipeline |
| Long-Horizon Execution | Roadmap target; runtime primitives exist but no benchmark evidence in this audit | 🔵 Planned | Need checkpoint/recovery/horizon benchmark |
| Computer Control | Not yet established as a safe, auditable subsystem | 🔵 Planned | Requires permissioned tool/action layer |
| Software Engineering Agents | Architectural target | 🔵 Planned | Requires sandbox, repository tools, test/repair loop |
| AI-native GUI | Architectural target | 🔵 Planned | Not yet the primary product surface |
| Mobile Client | Architectural target | 🔵 Planned | Not yet established as a production client |
| Sarembok Computing Environment | Long-term target | 🔴 Future | Not implemented |
| Sarembok Kernel | Long-term research objective | 🔴 Future research | Not implemented |

## 3. Unreal Startup Dependency Audit

### Observed path

`SarembokBridgeModule.cpp` creates and initializes the runtime manager during `StartupModule()`.

`SarembokRuntimeManager.cpp` immediately calls `FSarembokBridgeService::Get().Initialize()`.

`SarembokBridgeService.cpp` immediately creates `FSarembokWebSocketClient` and calls `Connect()`.

`SarembokBridgeRuntime.cpp` contains the same direct `Client->Connect()` pattern.

### Architectural conclusion

This is **not a compile problem**. It is a lifecycle/design problem.

The bridge should not require a reachable runtime to allow Unreal Editor startup. The correct target architecture is:

`UE Startup` → `Bridge Ready` → `Connection Attempt Scheduled Asynchronously` → `Connected/Offline State` → `Runtime Available`.

Unreal should remain usable when Sarembok Runtime is unavailable.

### Required future remediation

1. Make bridge initialization non-blocking.
2. Move connection attempts onto an appropriate async/task lifecycle.
3. Add explicit connection states: `Disabled`, `Connecting`, `Connected`, `Offline`, `Backoff`, `Stopping`.
4. Bound retry/backoff behavior.
5. Do not treat a failed network connection as an engine startup failure.
6. Make editor-only and packaged-runtime behavior explicit.
7. Add an automated bridge startup test that runs with no runtime available.

## 4. Authentication Boundary Audit

Production Compose requires:

`SAREMBOK_AUTH_TOKEN: ${SAREMBOK_AUTH_TOKEN:?Set SAREMBOK_AUTH_TOKEN before starting production}`

This is correct as a deployment guard: production should not silently start without authentication configuration.

The Unreal WebSocket client currently initializes:

`ServerURL = DefaultWebSocketURL`

`AuthToken = ""`

The production endpoint exists as a constant:

`wss://sarembok.com`

but the client does not automatically obtain production credentials. This is appropriate from a security standpoint; credentials should not be compiled into the client.

### Required future architecture

Use a secure runtime configuration chain:

`User / Device Identity` → `Sarembok Auth` → `Short-Lived Credential` → `Runtime Session` → `Authorized RPC`.

Do not ship a universal production bearer token inside the public Unreal application.

## 5. Renderer / Local Hardware Audit

The repository's `DefaultEngine.ini` is already attempting to accommodate Intel Iris Xe hardware by disabling Nanite, virtual shadow maps, Lumen features and ray tracing renderer settings, and by targeting SM5 formats.

However, the file still contains:

`RayTracingMode=Full`

under Windows target settings while renderer ray tracing is separately disabled.

This is an architectural/configuration inconsistency and should be removed or explicitly disabled for the current hardware baseline. The audit does not claim that this line alone is the proven cause of the observed startup freeze; that requires runtime logs and controlled A/B testing.

The current default maps also point to:

`/Engine/Maps/Entry`

which explains why the project can launch into an engine/default environment rather than a Sarembok-authored world. The repository currently contains only `Content/MetaHuman/metahuman.json` under the visible Content tree; there is no repository evidence here of a custom `.umap` startup world.

## 6. Security Finding — Public Repository Credential Exposure

`Config/DefaultEngine.ini` contains an `AndroidFileServerEditor` `SecurityToken` value.

Because this repository is public, the value must be treated as exposed.

### Required action

- Determine whether the token is active.
- If active, rotate/revoke it.
- Replace committed secrets with generated/local-only configuration.
- Add secret scanning to CI.
- Audit repository history if the value was ever security-sensitive.

This is a **high-priority hygiene item** independent of the Unreal rendering issue.

## 7. Architecture Gaps to Close

### Priority P0
- Secure configuration and credential lifecycle.
- Remove startup/network coupling from Unreal bridge.
- Resolve public repository secret exposure.

### Priority P1
- Formal Sarembok client/session identity model.
- Provider-neutral model adapter contract.
- Agent orchestration contract.
- Durable task state and checkpoint/recovery model.
- Permissioned computer-control subsystem.
- Automated integration test matrix.

### Priority P2
- OpenCV/perception pipeline.
- Voice pipeline hardening.
- MetaHuman runtime session integration.
- AI-native GUI prototype.
- Mobile client architecture.

### Priority P3
- Sarembok Computing Environment.
- Hardware abstraction strategy.
- Sarembok OS research.
- Kernel research program.

## 8. What We Should NOT Do Yet

- Do not make Unreal the center of Sarembok architecture.
- Do not embed production bearer tokens into the UE client.
- Do not build the kernel before the runtime, security, device model and capability model are sufficiently mature.
- Do not claim long-horizon autonomy without reproducible benchmark evidence.
- Do not equate a compiled plugin with a validated capability.
- Do not add more UI features until the underlying task/agent/session contracts are stable.

## 9. Immediate Engineering Sequence

1. Secure the repository/configuration boundary.
2. Make the UE bridge lifecycle-safe and offline-tolerant.
3. Formalize client identity and session authentication.
4. Formalize agent/task/memory contracts.
5. Implement durable long-horizon task state and checkpoints.
6. Establish the computer-control permission model.
7. Build the vision/OpenCV pipeline.
8. Integrate voice + MetaHuman as client/embodiment layers.
9. Build the AI-native GUI and mobile clients against the same platform APIs.
10. Only then accelerate the Sarembok Computing Environment / OS track.

## 10. Audit Limitations

This is a repository architecture audit based on the current GitHub `main` tree and selected source/configuration files. It does **not** constitute a local UE build verification, GPU driver test, production VPS inspection, or complete line-by-line audit of every source file. Claims about current production health should continue to be backed by live deployment tests.

## 11. Bottom Line

Sarembok already has a credible technical foundation. The next leap is not adding more disconnected features. It is turning the existing runtime, plugins and cloud infrastructure into a coherent platform with explicit contracts, secure identity, durable execution, measurable autonomy, and device-independent user experience.

**The architecture is now ready to move from integration foundation toward platform engineering.**
