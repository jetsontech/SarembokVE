# Sarembok VE Unreal Engine 5.8 Integration Guide

## Overview

The Unreal Engine 5.8 project integrates with Sarembok VE via 6 specialized C++ plugins located in `Plugins/`:

- **`SarembokBridge`**: Handles WebSocket networking, message dispatching, execution tracing, and RPC commands.
- **`SarembokAvatar`**: Manages MetaHuman ARKit morph target emotions and gestures.
- **`SarembokVoice`**: Handles audio playback, TTS voice manager, and viseme calculation.
- **`SarembokVision`**: Handles spatial actor perception and change detection.
- **`SarembokAgent`**: Manages autonomous goal trees, reasoning providers, and replanning transitions.
- **`SarembokMemory`**: Provides multi-tiered working, episodic, and semantic memory stores.

---

## C++ Quick Start

```cpp
#include "SarembokWebSocketClient.h"

// Instantiate WebSocket Client
FSarembokWebSocketClient Client;

// Connect to Production Cloud Endpoint
FString ProductionURL = TEXT("wss://sarembok.com");
FString AuthToken = TEXT("YOUR_SAREMBOK_AUTH_TOKEN");

Client.Connect(ProductionURL, AuthToken);
```

---

## PIE Demo Execution

1. Open `SarembokVE.uproject` in Unreal Editor 5.8.
2. Drag `ASarembokDemoController` into the level.
3. Press **Play in Editor (PIE)**.
4. Execute `StartAutonomousDemo()` or send RPC method `StartDemo`.
5. Check output log for full perception-memory-reasoning-action cascade.
