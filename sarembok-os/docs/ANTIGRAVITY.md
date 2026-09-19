# Antigravity Execution Contract

PROJECT: Sarembok OS
BASE:    seL4 microkernel + Linux VM component
LANGUAGE: C (kernel), Python (sim reference), TypeScript (console/embodiment)
BUILD:   reproducible, Make, bootable QEMU image per milestone

RULES (non-negotiable):
1. No stubs in kernel/. If it's in kernel/, it runs in kernel space.
2. Every milestone has a falsifiable acceptance test. No milestone is "done"
   without passing it and producing an artifact (log, screenshot, benchmark).
3. Every performance claim must be measured and published. No adjectives.
4. If a component cannot be built honestly in the timebox, mark it PLANNED
   and remove it from the claim surface. Do not fake it.
5. docs/CLAIMS.md maps every public claim to a passing test. CI fails if any
   claim lacks a passing test. README cannot claim an unimplemented syscall.

ORDER OF EXECUTION (sequential):
M0 Foundation -> M1 Kernel Core -> M2 Persistent Memory -> M3 Scheduler
-> M4 Distribution -> M5 Embodiment -> M6 Console

REFERENCE IMPLEMENTATION:
sim/ is the semantic reference. Port sim/ behavior to kernel/ (seL4).
Same syscall names, same acceptance tests, real kernel space.

DEFINITION OF DONE (project):
- Boots on real hardware (not just QEMU)
- Survives agent crash without kernel panic
- Memory persists across reboot
- Task migrates across two physical machines
- Same agent + avatar + memories return after reboot
- All claims trace to CI-verified acceptance tests

STOP CONDITION:
If M0-M2 are not real, do not start M3. The foundation is the product.

HANDOFF ORDER:
Hand Antigravity M0+M1 first. Get a bootable image with a real kernel
agent-process table and a passing fault-isolation test. Then M2. Then M3.
