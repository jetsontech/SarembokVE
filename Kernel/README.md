# Sarembok Kernel Foundation v1

This directory begins the **Sarembok-owned kernel technology track**.

It is not a mock kernel and it is not an Unreal subsystem. It is the first implementation boundary for a future Sarembok operating environment whose primitives are designed around autonomous computation.

## Current kernel-owned primitives

- fixed-capacity task descriptors
- deterministic priority scheduling
- capability-based authority
- explicit risk levels
- kernel-level task state
- architecture-independent kernel core
- `no_std` compatibility for future bare-metal targets

## Design direction

The kernel is being developed as a separate technology layer beneath the Sarembok Runtime:

```text
Hardware
   |
Sarembok Kernel
   |
Sarembok OS Services
   |
Sarembok Runtime
   |
Intelligence / Agent Fabric
   |
AI-native Environment
   |
Digital Human
   |
Human
```

The kernel must not depend on OpenAI, another model provider, Unreal Engine, MetaHuman, Linux user-space APIs, or a particular cloud vendor.

## What this first cut deliberately does not claim

This branch is **not yet a bootable general-purpose operating system**. The architecture-specific boot, interrupt, virtual-memory, process-isolation, device, storage, network, and SMP layers still need to be implemented. Those are subsequent kernel milestones, not hidden behind a demo.

## Next kernel milestones

1. x86_64 architecture bring-up and boot path.
2. Interrupt and timer subsystem.
3. Physical/virtual memory management.
4. Capability enforcement and isolation.
5. Kernel IPC primitives.
6. Scheduler/context switching.
7. Device abstraction and storage boundary.
8. Network boundary.
9. Sarembok OS service layer.
10. Agent/task execution binding.
11. GPU/NPU compute resource model.
12. Embodiment/runtime integration above the kernel boundary.

The implementation should remain portable enough to add ARM64 and other future targets without redefining Sarembok's core semantics.
