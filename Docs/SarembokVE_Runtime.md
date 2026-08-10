# Sarembok_VE — Digital Human Runtime Documentation

## Overview

**Sarembok_VE** is an Unreal Engine 5.8 virtual environment and digital human platform. It provides real-time bidirectional communication between external AI core services (such as Gemini Live / Sarembok AI backend) and in-engine digital human avatars.

---

## Architecture & Subsystems (v1.3.0-alpha Baseline)

The Unreal project is modularized into 6 core plugins located in `C:\Sarembok_VE\Plugins`:

| Subsystem Plugin | Primary Purpose | Key Classes & Headers |
| :--- | :--- | :--- |
| **`SarembokBridge`** | WebSocket runtime communication, message dispatching, execution tracing (`FSarembokExecutionTrace`), ticker-based world/avatar discovery, command constants | `FSarembokMessageDispatcher`, `USarembokWebSocketClient`, `SarembokCommandConstants.h` |
| **`SarembokAvatar`** | Digital human character management, emotion control, MetaHuman ARKit morph targets | `USarembokAvatarComponent`, `USarembokAvatarController`, `USarembokAvatarManager` |
| **`SarembokVoice`** | Audio execution, TTS pipeline integration, viseme calculation, speech queue tracking | `USarembokVoiceManager`, `ESarembokVoiceStatus` |
| **`SarembokVision`** | Structured world state model (`FSarembokWorldState`), actor distance/type classification, and change detection (`DetectChanges()`) | `USarembokVisionManager`, `FSarembokObservation`, `FSarembokWorldDelta` |
| **`SarembokAgent`** | Embodied autonomous state machine with goal management (`FSarembokGoal`), replanning (`REPLAN`), confidence scoring, pluggable LLM/deterministic reasoners | `USarembokAgentManager`, `ISarembokReasoningProvider`, `FSarembokLLMReasoner`, `FSarembokDeterministicReasoner` |
| **`SarembokMemory`** | Multi-tiered memory subsystem: Semantic store, Working memory (per-cycle context + active goal), and Episodic memory (`FSarembokEpisode`) | `USarembokMemorySubsystem`, `ISarembokMemoryInterface`, `FSarembokEpisode` |

---

## Canonical Command Protocol (`sarembok.v1`)

Authoritative versioned JSON command envelope schema with trace correlation and confidence scoring:

```json
{
  "protocol": "sarembok.v1",
  "id": "cmd-000001",
  "timestamp": "2026-08-10T05:38:00Z",
  "command": "Speak",
  "target": "Avatar",
  "payload": {
    "text": "Hello from Sarembok",
    "emotion": "Joyful"
  },
  "context": {
    "agent": "DeterministicReasoner",
    "trace": "trace-000001",
    "confidence": 0.95,
    "goal_id": "goal-000001",
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

## Embodied Autonomous Perception-Reasoning-Action Loop (v1.3)

```text
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
│                                 ▲                                      │
│                                 │ REPLAN (Action Outcome Mismatch)     │
│                                 └────────────── EVALUATE ◄─────────────┤
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    │ sarembok.v1 envelope + trace + confidence
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

1. **Working Memory**: Short-lived contextual state (`world_actor_count`, `world_timestamp`, `active_goal_id`, `active_goal_desc`). Reset or overwritten each perception-action cycle.
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

Executes the 60-step deterministic acceptance test pyramid covering runtime startup, message routing, voice/avatar control, world model change detection, multi-tiered memory, agent goal management, confidence scoring, replanning transitions, AI reasoner fallback, execution tracing, and the autonomous demo harness:
```powershell
python Tools/Diagnostics/Test-SarembokRuntimeEndToEnd.py
```

---

## Running the Autonomous Digital Human Demo (`v1.3.0-demo`)

The v1.3 Autonomous Digital Human Demo allows testers to run an embodied perception-memory-reasoning-action loop in Unreal Engine.

```text
       USER / TEST INPUT
               │
               ▼
      ┌─────────────────┐
      │   Goal Manager  │
      │ PushGoal(...)   │
      └────────┬────────┘
               │
               ▼
      ┌─────────────────┐
      │ Autonomous Loop │
      └────────┬────────┘
               │
  ┌────────────┼────────────┐
  ▼            ▼            ▼
VISION       MEMORY       REASONER
  │            │            │
  └────────────┼────────────┘
               ▼
         INTENT + SCORE
               │
               ▼
         ACTION SELECT
               │
      ┌────────┴────────┐
      ▼                 ▼
   AVATAR             VOICE
  Emotion             Speak
      │                 │
      └────────┬────────┘
               ▼
         WORLD CHANGE
               │
               ▼
            VISION
               │
               ▼
         EVALUATION
          │         │
        SUCCESS   FAILURE
          │         │
          ▼         ▼
      COMPLETE    REPLAN
```

### Steps to Run in Unreal Editor:

1. Open `SarembokVE.uproject` in Unreal Editor 5.8.
2. Open any level or default map.
3. Place an `ASarembokDemoController` actor into the world (or use Blueprint `Get Subsystem -> SarembokAgentManager`).
4. Press **Play in Editor (PIE)**.
5. Open **Output Log** (`Window -> Output Log`).
6. Execute `StartAutonomousDemo()` or send WebSocket command `StartDemo`.
7. Observe the complete event cascade in the log output:
   - `[SAREMBOK][DEMO] GOAL_CREATED Id=demo.observe.respond`
   - `[SAREMBOK][DEMO] STIMULUS_SPAWNED Actor=SarembokDemoStimulusActor`
   - `[SAREMBOK][VISION] ACTOR_ADDED Actor=SarembokDemoStimulusActor`
   - `[SAREMBOK][MEMORY] WORKING_STORED Key=world_actor_count`
   - `[SAREMBOK][MEMORY] EPISODE_STORED EventType=ActorDetected`
   - `[SAREMBOK][AGENT] INTENT Goal=demo.observe.respond Action=Speak Confidence=0.95`
   - `[SAREMBOK][BRIDGE] ROUTED Protocol=sarembok.v1`
   - `[SAREMBOK][AVATAR] EMOTION_EXECUTED Emotion=Surprised`
   - `[SAREMBOK][VOICE] EXECUTED Text="I notice something new: SarembokDemoStimulusActor"`
   - `[SAREMBOK][AGENT] STATE From=Evaluate To=Completed`

### Failure Injection & Replanning Demo:
Calling `InjectDemoFailure()` (or WebSocket command `InjectFailure`) causes the evaluation phase to fail, triggering replanning:
- `[SAREMBOK][AGENT] REPLAN Goal=demo.observe.respond FailedAction=Speak Alternative=Emotion:Surprised Trace=trace-000002`
- `[SAREMBOK][MEMORY] EPISODE_STORED EventType=Speak ActorId=SarembokDemoStimulusActor Outcome=replanned_failure`

