# Sarembok_VE — Digital Human & Virtual Environment Platform

An advanced Unreal Engine 5.8 digital human orchestration architecture and AI runtime platform (`Sarembok_VE`).

## Subsystem Plugins

- **`SarembokBridge`**: Real-time WebSocket connection, message dispatcher, command routing, and world lookup.
- **`SarembokAvatar`**: Digital human character manager, emotion controller, and MetaHuman compatibility.
- **`SarembokVoice`**: Audio execution, TTS pipeline integration, and speech playback.
- **`SarembokVision`**: Real-time scene observation and perception.
- **`SarembokAgent`**: Task planning, intent routing, and autonomous loops.
- **`SarembokMemory`**: Key-value state persistence and memory retrieval.

## Requirements

* **Unreal Engine:** 5.8
* **Build Tools:** Visual Studio 2022 / .NET 10 x64 SDK / UBT
* **Backend:** Python 3.10+ (WebSockets / FastAPI)

## Quick Start & Verification Commands

### 1. Standalone Health Diagnostics
```powershell
powershell -ExecutionPolicy Bypass -File Tools/Diagnostics/Test-SarembokProject.ps1
```

### 2. Build SarembokVEEditor Target
```powershell
powershell -ExecutionPolicy Bypass -File Tools/Builder/SarembokBuilder.ps1 -Action Build
```

### 3. Run WebSocket Integration Tests
```powershell
python Tools/Diagnostics/Test-WebSocketIntegration.py
```

### 4. Run End-to-End Real Runtime Acceptance Test
```powershell
python Tools/Diagnostics/Test-SarembokRuntimeEndToEnd.py
```

## Documentation

Full runtime architecture, WebSocket JSON command schemas, hardware-adaptive rendering baselines, and building guidelines are documented in:
- [SarembokVE_Runtime.md](file:///C:/Sarembok_VE/Docs/SarembokVE_Runtime.md)

## License

Distributed under the MIT License.