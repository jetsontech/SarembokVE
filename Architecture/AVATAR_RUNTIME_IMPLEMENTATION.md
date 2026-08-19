# Sarembok Avatar Runtime Implementation

## Purpose

Define the implementation boundary between Sarembok's authoritative digital-human state and its presentation runtime.

## Architecture

```text
Sarembok Core
  ├── Identity
  ├── Session
  ├── Memory
  ├── Agent state
  ├── Permissions
  └── Interaction state
          │
          ▼
   Avatar Runtime Contract
          │
     ┌────┴────┐
     │         │
 MetaHuman   Mobile/Other
 Presentation Presentation
```

The avatar is a client of Sarembok state. It is never the system of record for identity, memory, authorization, or agent state.

## MetaHuman path

The Unreal implementation uses a MetaHuman adapter that resolves a presentation asset from an avatar profile. The adapter must tolerate missing or delayed assets and expose lifecycle states:

- `Unresolved`
- `Loading`
- `Ready`
- `Degraded`
- `Failed`

A missing MetaHuman must not prevent Sarembok Core, session management, or other agents from operating.

## Mobile path

Mobile clients use the same avatar profile and authoritative interaction APIs. The presentation implementation may be a reduced-fidelity 3D avatar, streamed render, or another client representation. No Unreal dependency is permitted in the core protocol.

## Identity model

An avatar profile should contain stable identifiers and presentation preferences, not private model state:

```text
avatarId
userId
displayName
presentationType
appearanceProfile
voiceProfile
animationProfile
locale
accessibilityProfile
```

Authentication credentials, long-term memory, agent permissions, and sensitive user data remain outside the presentation profile.

## Performance contract

The runtime must support quality tiers so the same Sarembok identity can be presented on:

1. high-end desktop/workstation,
2. ordinary PC,
3. mobile device,
4. low-bandwidth client.

Quality adaptation belongs to the presentation layer and must not change the authoritative agent/session state.

## MetaHuman technology note

Epic documents MetaHuman as a real-time digital-human framework and documents mobile deployment and mobile facial-performance capture. Sarembok therefore integrates MetaHuman where appropriate while preserving its own platform-neutral avatar contract.

## Non-goals

This document does not commit a specific MetaHuman asset, `.uasset`, `.umap`, facial rig, or renderer configuration. Those assets belong in the Unreal presentation implementation and are validated independently.
