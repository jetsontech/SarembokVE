# Architecture

    USERSIDE: Console ? Embodiment (WebGPU) ? SDK ? Apps
    ---------------------------------------------------------------
    SYSTEM LAYER
      Agent runtime ? Memory arena manager ? Scheduler policy
      Provider router ? Distribution coordinator ? Capability bus
    ---------------------------------------------------------------
    SAREMBOK KERNEL SERVICES
      Agent-Process Table | Memory Arena Manager | Capability Broker
      Intent Scheduler    | Distribution Mediator | Identity Store
    ---------------------------------------------------------------
    seL4 MICROKERNEL (formally verified)   <-- port target (kernel/)
    ---------------------------------------------------------------
    Linux VM component (POSIX compatibility, drivers)
    ---------------------------------------------------------------
    HARDWARE

## Two implementations, one model
- `sim/` implements the kernel services as a **runnable simulation**.
  It is the semantic reference and the demo. It is NOT the OS.
- `kernel/` is the **seL4 port target**. Antigravity ports sim semantics
  onto seL4 components in M0-M2. Same syscall surface, same acceptance
  tests, real kernel space.

## The three structural bets
1. Memory is a kernel primitive, not a database.
2. The scheduler is intent-aware (CPU / remote workers / model calls).
3. The syscall surface is agent-native (spawn_agent, recall, remember,
   delegate, embody), with POSIX preserved underneath via the Linux VM.
