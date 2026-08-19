# Sarembok MetaHuman / Human Avatar Contract v1

## Purpose

Define the platform contract for Sarembok's human-facing avatar layer without coupling Sarembok Core, agent intelligence, memory, or cloud runtime to a specific character asset or rendering engine.

## Architectural rule

**MetaHuman is a presentation implementation, not the intelligence layer.**

Sarembok Core owns identity, session state, agent state, memory references, permissions, and interaction events. The avatar layer consumes those contracts and renders a human representation.

## Required capabilities

1. **Persistent identity** — an avatar is associated with a Sarembok user/agent identity, not with a level asset.
2. **Session continuity** — avatar sessions can reconnect without losing the authoritative agent/session state.
3. **Expression interface** — emotion, gaze, gesture, speech state, and attention are represented as platform-neutral events.
4. **Voice interface** — speech input/output remains independent from facial rendering.
5. **Vision interface** — computer-vision events can influence attention and interaction without being hard-wired to MetaHuman.
6. **Mobile compatibility** — the contract must support lightweight clients that cannot run Unreal Engine.
7. **Cloud compatibility** — authoritative state remains server/runtime controlled where required; rendering is a client responsibility.
8. **Asset substitution** — a MetaHuman, optimized 3D avatar, 2D avatar, or future representation may implement the same contract.
9. **Offline tolerance** — temporary loss of network connectivity must not destroy local presentation state.
10. **Accessibility** — avatar presentation must never be the only way to access Sarembok functionality.

## Canonical flow

```text
User
  -> Sarembok Client
  -> Session / Interaction Contract
  -> Sarembok Runtime / Agent System
  -> Response + Presentation Events
  -> Avatar Adapter
  -> MetaHuman / optimized avatar / mobile representation
```

## Separation boundaries

### Sarembok Core owns

- identity
- agent lifecycle
- memory
- task state
- permissions
- tool/action results
- conversation state
- authoritative session state

### Avatar layer owns

- skeletal/visual representation
- facial animation
- lip synchronization
- gaze
- gestures
- camera/presentation
- local rendering optimization

### Bridge owns

- transport
- serialization
- connection lifecycle
- platform adaptation
- event delivery

## MetaHuman rule

MetaHuman assets must never be required for Sarembok Core to boot, authenticate, execute an agent, retain memory, or perform non-visual work.

This permits the same Sarembok identity to appear through Unreal/MetaHuman on a high-end system and through a mobile-optimized representation on a phone or tablet.

## Future implementation targets

- `AvatarIdentity`
- `AvatarSession`
- `AvatarPresentationEvent`
- `AvatarAdapter`
- `SpeechPresentationEvent`
- `ExpressionState`
- `GazeState`
- `GestureRequest`
- `AvatarCapabilityProfile`

These names define the architectural vocabulary; concrete APIs should be introduced only when their owning subsystem is implemented.

## Status

**Architecture defined — implementation pending.**

This document intentionally does not claim that MetaHuman runtime integration is complete.
