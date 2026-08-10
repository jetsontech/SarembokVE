# Sarembok_VE — Digital Human Runtime Documentation

## Overview

**Sarembok_VE** is an Unreal Engine 5.8 virtual environment and digital human platform. It provides real-time bidirectional communication between external AI core services (such as Gemini Live / Sarembok AI backend) and in-engine digital human avatars.

---

## Architecture & Subsystems (v1.2.0-alpha Autonomous Baseline)

The Unreal project is modularized into 6 core plugins located in `C:\Sarembok_VE\Plugins`:

| Subsystem Plugin | Primary Purpose | Key Classes & Headers |
| :--- | :--- | :--- |
| **`SarembokBridge`** | WebSocket runtime communication, message dispatching, execution tracing (`FSarembokExecutionTrace`), ticker-based world/avatar discovery, command constants | `FSarembokMessageDispatcher`, `USarembokWebSocketClient`, `SarembokCommandConstants.h` |
| **`SarembokAvatar`** | Digital human character management, emotion control, MetaHuman ARKit morph targets | `USarembokAvatarComponent`, `USarembokAvatarController`, `USarembokAvatarManager` |
| **`SarembokVoice`** | Audio execution, TTS pipeline integration, viseme calculation, speech queue tracking | `USarembokVoiceManager`, `ESarembokVoiceStatus` |
| **`SarembokVision`** | Structured world state model (`FSarembokWorldState`), actor distance/type classification, and change detection (`DetectChanges()`) | `USarembokVisionManager`, `FSarembokObservation`, `FSarembokWorldDelta` |
| **`SarembokAgent`** | Embodied autonomous state machine (`PERCEIVE`→`INTERPRET`→`RECALL`→`PLAN`→`SELECT_ACTION`→`EXECUTE`→`OBSERVE_RESULT`→`EVALUATE`), pluggable reasoning provider | `USarembokAgentManager`, `ISarembokReasoningProvider`, `FSarembokDeterministicReasoner` |
| **`SarembokMemory`** | Multi-tiered memory subsystem: Semantic store, Working memory (per-cycle context), and Episodic memory (`FSarembokEpisode`) | `USarembokMemorySubsystem`, `ISarembokMemoryInterface`, `FSarembokEpisode` |

---

## Canonical Command Protocol (`sarembok.v1`)

Authoritative versioned JSON command envelope schema with trace correlation support:

```json
{
  "protocol": "sarembok.v1",
  "id": "cmd-000001",
  "timestamp": "2026-08-09T23:39:00Z",
  "command": "Speak",
  "target": "Avatar",
  "payload": {
    "text": "Hello from Sarembok",
    "emotion": "Joyful"
  },
  "context": {
    "agent": "DeterministicReasoner",
    "trace": "trace-000001",
    "reason": "New actor detected: PlayerCharacter"
  }
}
```

Corresponding command result response:

```json
{
  "protocol": "sarembok.v1",
  "id": "cmd-000001",
  "type": "command_result",
  "status": "completed",
  "command": "Speak",
  "target": "Avatar",
  "result": {
    "voice": "executed",
    "duration_ms": 1840
  }
}
```

---

## Embodied Autonomous Perception-Reasoning-Action Loop (v1.2)

```
       ┌────────────────────────────────────────────────────────┐
       │                                                        │
       ▼                                                        │
┌──────────────┐     FSarembokWorldState     ┌──────────────────┴─────────┐
│VISION MANAGER├────────────────────────────►│  WORKING / EPISODIC MEMORY │
└──────┬───────┘                             └──────────────┬─────────────┘
       │ DetectChanges()                                    │ RecallRecentEpisodes()
       ▼                                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                              SAREMBOK AGENT                            │
│  PERCEIVE ──► INTERPRET ──► RECALL ──► PLAN ──► SELECT_ACTION ──► EXEC │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    │ sarembok.v1 envelope + trace ID
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                            MESSAGE DISPATCHER                          │
│          (Generates FSarembokExecutionTrace / Routes commands)         │
└──────┬────────────────────────────────────────────────────┬────────────┘
       │ Emotion                                            │ Speak
       ▼                                                    ▼
┌──────────────────┐                                ┌─────────────────────┐
│ AVATAR CONTROLLER│                                │    VOICE MANAGER    │
└──────┬───────────┘                                └───────┬─────────────┘
       │                                                    │
       └─────────────────────────┬──────────────────────────┘
                                 ▼
                    ┌─────────────────────────┐
                    │ DIGITAL HUMAN IN UWORLD │
                    └─────────────────────────┘
```

---

## Multi-Tiered Memory Architecture

1. **Working Memory**: Short-lived contextual state (`world_actor_count`, `world_timestamp`, active task parameters). Reset or overwritten each perception-action cycle.
2. **Episodic Memory**: Sequential history of timestamped event records (`FSarembokEpisode`) containing `Timestamp`, `EventType`, `ActorId`, `Description`, `ActionTaken`, `Outcome`, and `TraceId`. Managed via FIFO eviction (capacity: 256).
3. **Semantic Memory**: Persistent key-value fact store (`StoreMemory`, `RecallMemory`) protected by critical sections (`FCriticalSection`).

---

## Hardware-Adaptive Rendering Baseline

The hardware configuration in `Config/DefaultEngine.ini` guarantees compatibility with **Intel Iris Xe integrated graphics**:

- Target Shader Format: `PCD3D_SM5`
- Dynamic GI Method: 0 (Disabled / Baseline)
- Reflection Method: 0 (Disabled / Baseline)
- Nanite: Disabled (`r.Nanite.ProjectEnabled=False`)
- Virtual Shadow Maps: Disabled (`r.Shadow.Virtual.Enable=0`)
- Hardware Ray Tracing: Disabled (`r.RayTracing=0`)

---

## Building & Automation Tools

Project operations are managed through unified PowerShell tools in `Tools/`:

### 1. Project Builder (`Tools/Builder/SarembokBuilder.ps1`)

- **Build Project**:
  ```powershell
  powershell -ExecutionPolicy Bypass -File Tools/Builder/SarembokBuilder.ps1 -Action Build
  ```
- **Run Diagnostics**:
  ```powershell
  powershell -ExecutionPolicy Bypass -File Tools/Builder/SarembokBuilder.ps1 -Action Diagnose
  ```

### 2. Standalone Health Diagnostics (`Tools/Diagnostics/Test-SarembokProject.ps1`)

Audits git status, UE 5.8 installation, `.uproject` plugins, `Build.cs` configurations, missing headers, duplicate source files, and backend scripts:
```powershell
powershell -ExecutionPolicy Bypass -File Tools/Diagnostics/Test-SarembokProject.ps1
```

### 3. End-to-End Runtime Test Pyramid (`Tools/Diagnostics/Test-SarembokRuntimeEndToEnd.py`)

Executes the 30-step deterministic acceptance test pyramid covering runtime startup, message routing, voice/avatar control, world model change detection, multi-tiered memory, agent state machine transitions, intent generation, and trace logging:
```powershell
python Tools/Diagnostics/Test-SarembokRuntimeEndToEnd.py
```
