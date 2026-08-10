# Sarembok_VE — Digital Human & Virtual Environment Platform

An advanced Unreal Engine 5.8 digital human orchestration architecture and AI runtime platform (`Sarembok_VE`).

## Architecture & Capabilities (v1.4 Embodied Interaction)

- **`SarembokBridge`**: Real-time WebSocket connection, message dispatcher, command routing, and developer execution trace HUD visualizer (`sarembok.DebugTrace`).
- **`SarembokAvatar`**: Digital human character manager, emotion controller, smooth facial expression pose interpolation, and MetaHuman ARKit morph target compatibility.
- **`SarembokVoice`**: Audio execution, TTS pipeline integration, phoneme-to-viseme curve calculation, and speech playback.
- **`SarembokVision`**: Real-time scene observation, actor classification (`Character`, `Pawn`, `StaticMesh`, `Light`), 3D spatial distance matrix, and user FOV tracking.
- **`SarembokAgent`**: Goal stack management, schema-validated LLM provider reasoning (`FSarembokLLMReasoner`), intent routing, multi-candidate planning, replanning, and deterministic safety fallback (`FSarembokDeterministicReasoner`).
- **`SarembokMemory`**: Working memory, episodic memory storage, and state retrieval.

## Requirements

- **Unreal Engine:** 5.8
- **Build Tools:** Visual Studio 2022 / .NET 10 x64 SDK / UBT
- **Backend:** Python 3.10+ (WebSockets / FastAPI)

## Quick Start & Verification Commands

### 1. Standalone Health Diagnostics (26/26 PASS)

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

### 4. Run End-to-End Real Runtime Acceptance Test (75/75 PASS)

```powershell
python Tools/Diagnostics/Test-SarembokRuntimeEndToEnd.py
```

## Documentation

Full runtime architecture, WebSocket JSON command schemas, hardware-adaptive rendering baselines, and building guidelines are documented in:

- [SarembokVE_Runtime.md](Docs/SarembokVE_Runtime.md)

## License

Distributed under the MIT License.