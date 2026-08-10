# Sarembok_VE — Digital Human Runtime Documentation

## Overview

**Sarembok_VE** is an Unreal Engine 5.8 virtual environment and digital human platform. It provides real-time bidirectional communication between external AI core services (such as Gemini Live / Sarembok AI backend) and in-engine digital human avatars.

---

## Architecture & Subsystems

The Unreal project is modularized into 6 core plugins located in `C:\Sarembok_VE\Plugins`:

| Subsystem Plugin | Primary Purpose | Key Classes |
| :--- | :--- | :--- |
| **`SarembokBridge`** | WebSocket runtime communication, message dispatching, ticker-based world/avatar discovery | `FSarembokMessageDispatcher`, `USarembokWebSocketClient`, `USarembokBridgeActorComponent` |
| **`SarembokAvatar`** | Digital human character management, emotion control, state machine, and MetaHuman compatibility | `USarembokAvatarComponent`, `USarembokAvatarController`, `USarembokAvatarManager` |
| **`SarembokVoice`** | Audio execution, TTS pipeline integration, and speech playback | `USarembokVoiceManager` |
| **`SarembokVision`** | Real-time scene observation and camera frame processing | `USarembokVisionManager`, `FSarembokObservation` |
| **`SarembokAgent`** | Task planning, autonomous loops, and intent routing | `USarembokAgentManager`, `FSarembokTask` |
| **`SarembokMemory`** | Key-value state persistence and memory retrieval | `ISarembokMemoryInterface` |

---

## Command Lifecycle & Dispatch Architecture

```
[External AI Backend] 
        │
        ▼ (WebSocket JSON)
[SarembokBridge :: WS Client]
        │
        ▼
[FSarembokMessageDispatcher]
        │
  ├── Parse JSON (command, target, payload)
  ├── Search Runtime World (Game/PIE context)
  ├── If Avatar or World Unavailable ──► Queue in PendingCommands & Retry on Ticker (0.1s)
  └── Execute Command:
        ├── "Emotion" ──► USarembokAvatarController::SetEmotion()
        └── "Speak"   ──► USarembokAvatarComponent::Speak() ──► USarembokVoiceManager::Speak()
```

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

## WebSocket JSON Protocol

The bridge listens on `ws://127.0.0.1:9000` (or `ws://127.0.0.1:8765`).

### 1. Emotion Command
```json
{
  "command": "Emotion",
  "target": "Avatar",
  "payload": {
    "state": "Happy"
  }
}
```

### 2. Speak Command
```json
{
  "command": "Speak",
  "target": "Avatar",
  "payload": {
    "text": "Hello from Sarembok Digital Human runtime!",
    "emotion": "Joyful"
  }
}
```

---

## Integration Testing

Validate the Python WebSocket backend and message schema lifecycle:
```powershell
python Tools/Diagnostics/Test-WebSocketIntegration.py
```
