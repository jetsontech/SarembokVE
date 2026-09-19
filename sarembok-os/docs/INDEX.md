# Sarembok OS ? Documentation Index

| Doc | What it covers |
|---|---|
| ARCHITECTURE.md | System layers, seL4 + Linux VM rationale, the three bets |
| SYSCALLS.md | The agent-native syscall surface |
| CLAIMS.md | Claim -> test map. CI enforces this. |
| ANTIGRAVITY.md | Execution contract for Antigravity |

## Two implementations, one model
- `sim/` ? runnable kernel-model simulation (Python). Demo + reference.
- `kernel/` ? seL4 port target (C skeleton). Antigravity ports sim here.

## Run the simulation now
    python3 sim/run_tests.py       # acceptance suite
    python3 sim/shell.py           # interactive Sarembok shell
    python3 sim/embodiment_stub.py # persistent embodied identity PoC
    python3 sim/console_bridge.py  # JSON-RPC WebSocket bridge (needs websockets)

## Enforce claims
    make verify-claims

## Port to seL4 (Antigravity)
    See docs/ANTIGRAVITY.md. M0 -> M1 -> M2 first. Do not fake kernel work.
