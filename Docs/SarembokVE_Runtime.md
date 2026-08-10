# Sarembok_VE — Digital Human Runtime Documentation

## Overview

**Sarembok_VE** is an Unreal Engine 5.8 virtual environment and digital human platform. It provides real-time bidirectional communication between external AI core services (such as Gemini Live / Sarembok AI backend) and in-engine digital human avatars.

---

## Architecture & Subsystems

The Unreal project is modularized into 6 core plugins located in `C:\Sarembok_VE\Plugins`:

| Subsystem Plugin | Primary Purpose | Key Classes & Headers |
| :--- | :--- | :--- |
| **`SarembokBridge`** | WebSocket runtime communication, message dispatching, ticker-based world/avatar discovery, command constants | `FSarembokMessageDispatcher`, `USarembokWebSocketClient`, `SarembokCommandConstants.h` |
| **`SarembokAvatar`** | Digital human character management, emotion control, state machine, and MetaHuman compatibility | `USarembokAvatarComponent`, `USarembokAvatarController`, `USarembokAvatarManager` |
| **`SarembokVoice`** | Audio execution, TTS pipeline integration, speech playback, and voice execution status | `USarembokVoiceManager`, `ESarembokVoiceStatus` |
| **`SarembokVision`** | Real-time scene observation and camera frame processing | `USarembokVisionManager`, `FSarembokObservation` |
| **`SarembokAgent`** | Task planning, autonomous loops, and intent routing | `USarembokAgentManager`, `FSarembokTask` |
| **`SarembokMemory`** | Key-value state persistence and memory retrieval | `ISarembokMemoryInterface` |

---

## Command Lifecycle & Dispatch Architecture

```
[External AI Backend] 
        │
        ▼ (WebSocket JSON on ws://127.0.0.1:9000)
[SarembokBridge :: WS Client]
        │
        ▼
[FSarembokMessageDispatcher]
        │
  ├── Parse JSON via SarembokCommandConstants (command, target, payload)
  ├── Search Runtime World (Game/PIE context)
  ├── If Avatar Missing ──► Spawns Deterministic Fallback Avatar (SarembokRuntimeAvatarActor)
  ├── If World Unavailable ──► Queue in PendingCommands & Retry on Core Ticker (0.1s)
  └── Execute Command:
        ├── "Emotion" ──► USarembokAvatarController::SetEmotion()
        └── "Speak"   ──► USarembokAvatarComponent::Speak() ──► USarembokVoiceManager::SpeakWithResult()
```

---

## Centralized Command Protocol (`SarembokCommandConstants.h`)

Authoritative string constants declared in `SarembokCommandConstants.h`:

- **Commands**: `Emotion`, `Speak`, `Chat`, `Facial`, `Gesture`
- **Targets**: `Avatar`, `Voice`, `System`
- **JSON Field Keys**: `command`, `target`, `payload`, `state`, `text`, `emotion`
- **Default WebSocket Endpoint**: `ws://127.0.0.1:9000`

---

## Voice Execution Status (`ESarembokVoiceStatus`)

`USarembokVoiceManager` exposes `SpeakWithResult(Text)` returning:

- `ESarembokVoiceStatus::Executed` — Speech command accepted and executed.
- `ESarembokVoiceStatus::Queued` — Speech command queued.
- `ESarembokVoiceStatus::Unavailable` — Voice executor/audio subsystem currently unavailable.
- `ESarembokVoiceStatus::Failed` — Payload validation or execution fault.

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
- **Generate VS Solution**:
  ```powershell
  powershell -ExecutionPolicy Bypass -File Tools/Builder/SarembokBuilder.ps1 -Action Generate
  ```
- **Clean Generated Binaries**:
  ```powershell
  powershell -ExecutionPolicy Bypass -File Tools/Builder/SarembokBuilder.ps1 -Action Clean
  ```

### 2. Standalone Health Diagnostics (`Tools/Diagnostics/Test-SarembokProject.ps1`)

Audits git status, UE 5.8 installation, `.uproject` plugins, `Build.cs` configurations, missing headers, duplicate source files, and backend scripts:
```powershell
powershell -ExecutionPolicy Bypass -File Tools/Diagnostics/Test-SarembokProject.ps1
```

---

## WebSocket Integration Test Suite

The integration test suite (`Tools/Diagnostics/Test-WebSocketIntegration.py`) validates:

1. Connection & Valid `Emotion` command lifecycle
2. Valid `Speak` command lifecycle
3. Malformed JSON protocol resilience
4. Unknown command routing
5. Missing payload handling
6. Disconnect & Reconnect cycle

Run tests via:
```powershell
python Tools/Diagnostics/Test-WebSocketIntegration.py
```
