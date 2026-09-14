# SarembokVE

## AI-Native Computing Environment

**SarembokVE is an independent AI-native computing environment and control plane for persistent intelligence, agent execution, orchestration, memory, research, tools, and distributed compute.**

SarembokVE is being developed as a real technology platform rather than a conventional AI chat frontend or a thin model wrapper. Its purpose is to make intelligence a native computing capability: the platform maintains runtime state, routes work, coordinates agents and workers, preserves memory, exposes controlled tools, and presents a coherent interactive environment to the user.

## What SarembokVE Is Today

The active platform combines a production cloud runtime, browser edge, persistent state, real-time control, model/provider abstraction, and an interactive command environment.

### Core platform

- **AI runtime and control plane** for conversations, agents, tasks, events, memory, providers, and execution state.
- **Real-time WebSocket and JSON-RPC transport** for authenticated browser/runtime control and low-latency interaction.
- **Persistent SQLite/WAL state** for memory, tasks, conversations, and runtime continuity.
- **Agent lifecycle and orchestration** supporting agent creation, task execution, planning-oriented workflows, and multi-agent coordination.
- **Provider-independent model routing** so frontier and specialized models can be selected as computational components without making a single vendor the platform itself.
- **Research and live-information pathways** for evidence retrieval, current information, and synthesized responses.
- **Distributed worker architecture** for external compute workers and future GPU-backed workloads.
- **Browser-first access** through the production edge so users can interact with the environment without installing the underlying infrastructure.
- **Multimodal interaction surfaces** for text, voice, visual media, documents, code, and other structured response types supported by the runtime.

## The SarembokVE Difference

A conventional AI chatbot generally centers the interaction around a model response. SarembokVE centers the interaction around the **computing environment** surrounding intelligence.

| Capability | SarembokVE | Conventional AI chat application |
|---|---|---|
| Runtime | Controlled AI runtime and execution plane | Primarily a chat service |
| State | Persistent SQLite/WAL state and session continuity | Often session-centric |
| Agents | Agent lifecycle and orchestration architecture | Usually a single assistant abstraction |
| Tasks | Background tasks, scheduling, and execution visibility | Limited or hidden execution model |
| Models | Provider/model abstraction and routing | Often centered on one provider |
| Workers | Distributed worker registration and compute coordination | Usually external to the chat product |
| Interaction | Text plus structured multimodal response surfaces | Primarily conversational text |
| Research | Retrieval/evidence pathways plus synthesis | Typically model-centric retrieval |
| System direction | AI-native computing environment | Application layer over conventional computing |

## Sovereignty and Interoperability

SarembokVE is designed to remain independent of any single AI provider or infrastructure vendor.

External models and systems can be integrated where they provide useful capabilities. They are components inside the SarembokVE architecture rather than the definition of the platform.

This separation is intentional. Models can change, providers can change, and compute resources can change without requiring SarembokVE to become a rebranded interface for any one company.

## Production Foundation

The public SarembokVE environment is deployed at:

**https://sarembok.com**

The production foundation currently includes:

- Containerized cloud runtime and edge deployment.
- Caddy-based public HTTPS edge routing.
- Authenticated browser session issuance.
- WebSocket control and JSON-RPC execution.
- Runtime health and operational telemetry.
- Persistent SQLite/WAL storage.
- Agent and task management.
- Chat/session continuity through the runtime control plane.
- Provider routing and model abstraction.
- Research/intelligence integration paths.
- External worker registration and compute scheduling architecture.
- Browser control surfaces for runtime, workers, agents, tasks, memory, research, and multimodal interaction.

The repository and public deployment are intended to represent the same engineering system; production changes are validated against the active runtime rather than simulated with disposable mock infrastructure.

## Multimodal Computing Surface

SarembokVE is designed for more than plain text responses. The frontend contains structured response surfaces for supported capabilities such as:

- Video and media playback.
- Audio streams.
- Images and visual synthesis.
- Research documents and PDFs.
- Code blocks and developer output.
- Structured task matrices.
- Flashcards and interactive content.
- Persistent dialogue and session continuity.

These are interface and execution surfaces around the underlying runtime, not independent products.

## Digital-Human and System Architecture Direction

SarembokVE is also being developed toward a deeper AI-native system architecture in which intelligence, identity, memory, execution, and high-fidelity embodiment can operate as one computing environment.

High-fidelity digital-human technology and Unreal Engine integration are part of that direction. They are platform and development capabilities, not prerequisites for a public browser user.

The longer-term architecture extends toward a dedicated system/OS and kernel layer capable of managing intelligent agents, resource boundaries, device integration, security, persistent state, and machine-level execution as native system functions.

These are active architectural development directions, not claims that every future layer is already complete in the current public deployment.

## Engineering Principles

### Build the system, not the demo

SarembokVE is designed around durable runtime capabilities, explicit protocols, persistence, observability, security boundaries, and real deployment validation.

### Intelligence is a system capability

The objective is not simply to provide better model answers. The objective is to build a computing environment in which intelligence can reason about objectives, retain continuity, coordinate work, use tools, interact with compute resources, and execute controlled actions.

### Provider independence

A model provider should be replaceable. SarembokVE owns the orchestration and execution environment around those models.

### Real infrastructure over simulated infrastructure

Development targets the actual cloud runtime, browser edge, persistent state, worker fabric, and production deployment rather than placeholder demonstrations.

## Development Direction

The platform is advancing along several connected layers:

**Runtime → agents → memory → orchestration → research → tools → workers → distributed compute → multimodal interaction → digital-human embodiment → AI-native system architecture.**

The central engineering challenge is integrating these layers into one coherent environment while maintaining security, reliability, interoperability, and operational control.

## Project Status

SarembokVE is under active development.

The cloud/runtime foundation, authenticated browser sessions, agent and task architecture, persistent memory, WebSocket control plane, provider abstraction, research pathways, distributed-worker foundation, and public production edge are already implemented and being validated.

The project is continuing toward deeper system integration, expanded compute, richer multimodal operation, high-fidelity digital-human embodiment, and the longer-term AI-native operating-system/kernel architecture.

## Authoritative Repository

**https://github.com/jetsontech/SarembokVE**

SarembokVE is being built as an independent computing platform in which **intelligence is a native capability of the environment**.
