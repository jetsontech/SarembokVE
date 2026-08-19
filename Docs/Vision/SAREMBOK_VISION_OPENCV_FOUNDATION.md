# Sarembok Vision + OpenCV Foundation

## Purpose

Sarembok Vision converts device sensor input into normalized perception events that can be consumed by agents, memory, governance, and the avatar layer.

OpenCV is the first portable computer-vision backend. It is a backend, not the Sarembok vision contract itself. This prevents the architecture from being locked to one CV library, model provider, GPU vendor, operating system, or device class.

## Pipeline

```text
Camera / image / video
        |
        v
+---------------------+
| Vision Input Adapter |
+---------------------+
        |
        v
+---------------------+
| OpenCV / CV Backend  |
+---------------------+
        |
        v
+---------------------+
| Normalized Detection |
+---------------------+
        |
        v
+---------------------+
| Sarembok Vision Event|
+---------------------+
        |
        +----> Memory
        +----> Agents
        +----> Governance
        +----> Avatar / UX
        +----> Automation
```

## Backend contract

The Unreal plugin exposes `ISarembokVisionBackend` and `FSarembokVisionEvent` / `FSarembokVisionDetection`.

Backends are replaceable. Planned implementations include:

- OpenCV CPU backend
- OpenCV CUDA backend where available
- Unreal-native capture/perception backend
- Apple Vision adapter
- Android ML/CV adapter
- NVIDIA accelerated vision backend
- Future Sarembok-native perception models

## OpenCV rule

OpenCV must remain an implementation dependency at the edge. Core Sarembok code consumes normalized events and must never require OpenCV headers or APIs.

This allows the same Sarembok perception architecture to run on:

- phones and tablets
- Windows PCs
- Linux systems
- cloud workers
- NVIDIA systems
- future Sarembok hardware

## Privacy and security

Raw camera frames are sensitive input. The default architecture is event-first: process locally when possible and transmit only the minimum structured perception data required by an authorized agent or workflow.

Any remote frame transfer requires explicit capability authorization, transport authentication, audit logging, and a defined retention policy.
