# Sarembok Kernel Foundation — Architecture Decision

**Status:** FOUNDATIONAL / ACTIVE DEVELOPMENT  
**Date:** 2026-08-20  
**Decision:** Begin Sarembok-owned kernel engineering as a first-class technology track.

## Context

The Sarembok master blueprint already establishes the long-term destination as:

`Hardware -> Sarembok Kernel -> Sarembok Runtime -> Intelligence Fabric -> Agent Fabric -> AI-native GUI -> Digital Human / User`

The kernel therefore cannot remain only a future statement. It needs an implementation boundary now.

## Decision

Sarembok will develop its own kernel technology independently of the public client and independently of any model provider or rendering technology.

The initial kernel core is written to be architecture-neutral and `no_std` compatible. Architecture-specific code will be added behind explicit ports.

## Kernel-native concepts

The kernel roadmap treats these as first-class primitives:

- task
- agent execution resource
- capability
- permission
- risk level
- memory/resource ownership
- IPC channel
- compute resource
- device
- identity

Higher-level intelligence, memory, planning, embodiment, and provider integrations remain outside the kernel and communicate through stable OS/runtime contracts.

## Non-negotiable boundaries

- Unreal Engine is not a kernel dependency.
- MetaHuman is not a kernel dependency.
- OpenAI or any other model provider is not a kernel dependency.
- Public users do not install or manage the kernel.
- Existing Linux/Windows systems remain development/deployment foundations until Sarembok-native hardware/boot infrastructure is ready.

## Definition of done for the kernel track

A milestone is complete only when it has executable code, reproducible tests, documented interfaces, and evidence of behavior on the target architecture. Architectural documents alone do not count as implementation.
