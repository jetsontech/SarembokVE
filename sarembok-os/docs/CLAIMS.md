# Claim -> Test Map

CI (`make verify-claims`) fails if any public claim lacks a passing test.

| Claim | Test | Impl | Status |
|---|---|---|---|
| "runnable kernel-model simulation" | tests/acceptance/sim_boot.sh | sim | pending |
| "kernel-level agent-process table" | tests/acceptance/m1_agent_lifecycle.sh | sim | pending |
| "fault isolation (agent crash, kernel survives)" | tests/acceptance/m1_fault_isolation.sh | sim | pending |
| "kernel-primitive persistent memory" | tests/acceptance/m2_persistence.sh | sim | pending |
| "tiered kernel eviction" | tests/acceptance/m2_eviction.sh | sim | pending |
| "boots on seL4" | tests/acceptance/m0_boot.sh | kernel | planned |
| "intent-aware scheduler" | tests/acceptance/m3_cross_node.sh | kernel | planned |
| "distributed task migration" | tests/acceptance/m4_two_machine.sh | kernel | planned |
| "persistent embodied identity" | tests/acceptance/m5_reboot.sh | kernel | planned |
