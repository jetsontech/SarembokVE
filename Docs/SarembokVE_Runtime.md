# Sarembok_VE — Digital Human Runtime Documentation

## Overview

**Sarembok_VE** is an Unreal Engine 5.8 virtual environment and digital human platform. It provides real-time bidirectional communication between external AI core services (such as Gemini Live / Sarembok AI backend) and in-engine digital human avatars.

---

## Architecture & Subsystems

The Unreal project is modularized into 6 core plugins located in `C:\Sarembok_VE\Plugins`:

| Subsystem Plugin | Primary Purpose | Key Classes & Headers |
| :--- | :--- | :--- |
| **`SarembokBridge`** | WebSocket runtime communication, message dispatching, ticker-based world/avatar discovery, command constants | `FSarembokMessageDispatcher`, `USarembokWebSocketClient`, `SarembokCommandConstants.h` |
| **`SarembokAvatar`** | Digital human character management, emotion control, MetaHuman ARKit morph targets | `USarembokAvatarComponent`, `USarembokAvatarController`, `USarembokAvatarManager` |
| **`SarembokVoice`** | Audio execution, TTS pipeline integration, viseme calculation, speech queue tracking | `USarembokVoiceManager`, `ESarembokVoiceStatus` |
| **`SarembokVision`** | Real-time UWorld scene actor observation, spatial location tracking, and frame capture | `USarembokVisionManager`, `FSarembokObservation` |
| **`SarembokAgent`** | Task planning, autonomous closed-loop execution (`RunAutonomousLoop`), state machine | `USarembokAgentManager`, `FSarembokTask` |
| **`SarembokMemory`** | Thread-safe key-value state persistence (`StoreMemory`, `RecallMemory`) | `USarembokMemorySubsystem`, `ISarembokMemoryInterface` |

---

## Canonical Command Protocol (`sarembok.v1`)

Authoritative versioned JSON command envelope schema:

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
    "agent": "default",
    "task": "greeting"
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

## Perception-Reasoning-Action Closed Loop

```
VISION (Observe scene actors & location vectors)
  │
  ▼
MEMORY (Thread-safe key-value store / recall)
  │
  ▼
AGENT (Reasoning state machine & intent synthesis)
  │
  ▼
BRIDGE (Dispatches versioned sarembok.v1 JSON envelope with correlation ID)
  │
  ├── Emotion ──► AVATAR (MetaHuman morph targets: Happy/Sad/Angry/Surprised/Calm)
  └── Speak ────► VOICE  (Viseme open weight & speech queue)
  │
  ▼
DIGITAL HUMAN (Character expression & speech update world state)
  │
  └──────────────► VISION (Feedback loop)
```

---

## Hardware-Adaptive Rendering Baseline

The hardware configuration in `Config/DefaultEngine.ini` guarantees compatibility with **Intel Iris Xe integrated graphics**:

- Target Shader Format: `PCD3D_SM5`
- Dynamic GI Method: 0 (Disabled / Baseline)
- Reflection Method: 0 (Disabled / Baseline)
- Nanite: Disabled (`r.Nanite.ProjectEnabled=False`)
- Virtual Shadow Maps: Disabled (`r.Shadow.Virtual.Enable=0`)
- Hardware Ray Tracing: Disabled (`r.RayTracing=0`)

*Note: Future high-end hardware profiles (SM6/Lumen/Nanite) can be enabled per-device profile without breaking default iGPU compatibility.*

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

Executes the 22-step deterministic acceptance test pyramid:
```powershell
python Tools/Diagnostics/Test-SarembokRuntimeEndToEnd.py
```
