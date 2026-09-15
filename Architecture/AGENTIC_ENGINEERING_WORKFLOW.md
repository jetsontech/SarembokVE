# SarembokVE Agentic Engineering Workflow

## Source

**Video:** Ex-NASA dev reveals his Agentic Engineering Workflow  
**URL:** https://www.youtube.com/watch?v=xgkjtF89-44  
**Guests:** David Ondrej and Dex Horthy  
**Published:** 2026-08-07  

The source is useful to SarembokVE because it focuses on the engineering control loop around coding agents: program design before implementation, deterministic feedback, context selection, vertical slices, and optimizing the actual delivery bottleneck rather than agent activity.

## What transfers directly to SarembokVE

### 1. Program design before implementation

Before a non-trivial Sarembok change is allowed to generate code, capture four decisions:

1. **Product:** what user problem is being solved and how success is measured.
2. **System architecture:** services, request flow, data boundaries, endpoints, persistence, and security boundaries.
3. **Program design:** important call paths, function/module responsibilities, data contracts, and failure behavior.
4. **Vertical slice:** the smallest end-to-end implementation that proves the design in the real runtime.

The agent should not be allowed to silently invent these decisions after implementation has begun.

### 2. Context engineering is retrieval, not context dumping

Sarembok should supply the smallest relevant set of authoritative context:

- current repository state and commit
- relevant source files and symbols
- runtime authority snapshot
- provider/model inventory
- tests and recent failures
- deployment configuration
- recent task/event evidence
- source URLs or documents when research is involved

Every retrieved context item should have a source, freshness signal, and reason for inclusion.

### 3. Deterministic back-pressure

Agent output must encounter measurable gates instead of subjective confidence alone.

Examples for Sarembok:

- `python -m compileall Deployment/cloud`
- provider contract tests
- compose configuration validation
- runtime health checks
- WebSocket/RPC smoke tests
- browser interaction tests
- public HTTPS checks
- response rendering assertions
- task lifecycle assertions

An agent may propose a change, but the runtime and CI must provide deterministic evidence that the change works.

### 4. Vertical slices instead of giant rewrites

Prefer one complete path over broad unfinished infrastructure.

For example:

`user prompt -> intent routing -> provider selection -> execution -> persisted lifecycle -> rendered response -> verification`

Once that slice works, expand capability breadth.

### 5. Optimize the bottleneck

The source video's strongest operational lesson is that increasing agent activity does not help if review, verification, deployment, or another downstream step is the actual constraint.

For Sarembok, current evidence says the provider fabric was the bottleneck, not worker count. The provider failure loop therefore takes priority over adding more orchestration or UI complexity.

## Sarembok implementation rule

Every substantial feature should carry this compact design packet before implementation:

```text
FEATURE
Problem:
Success metric:

ARCHITECTURE
Request path:
Modules/files:
Data/state changes:
External boundaries:
Failure modes:

PROGRAM DESIGN
Key functions:
Contracts:
Fallback behavior:
Observability:

VERTICAL SLICE
Smallest end-to-end path:
Proof commands/tests:
Rollback point:

CONTEXT
Authoritative sources:
Freshness:
Retrieved evidence:
Unknowns:
```

## Context retrieval map

| Stage | Sarembok source | Rule | Proof |
|---|---|---|---|
| Product | feature request / acceptance criteria | retrieve only the current goal and measurable outcome | acceptance metric exists |
| Architecture | architecture docs + relevant modules | retrieve only affected boundaries | request/data flow is explicit |
| Program design | exact symbols/files/tests | retrieve implementation context before code generation | call path and failure behavior are named |
| Runtime | runtime authority + provider metrics | use observed state, never inference | snapshot timestamp |
| Research | web/source evidence | freshness and source quality required | citations/evidence trail |
| Verification | CI + smoke tests + live health | deterministic gates | pass/fail artifact |

## Failure modes this prevents

### Context dumping

Sending the entire repository or stale history into an agent increases noise and makes important constraints harder to see. Retrieval should be targeted and evidence-backed.

### Stale or unverified memory

Remembered architecture is not authoritative when production state may have changed. Runtime observations, current source, and current deployment configuration win.

### Code generation without a reviewable design

Large generated changes are expensive to understand after the fact. Program design and vertical slices reduce the amount of generated behavior that must be inspected at once.

### Optimizing the wrong station

More agents, more tokens, or more workers do not fix a broken provider, failing deployment, or missing verification gate. Measure the delivery path and fix its current constraint first.

## Source-backed anchors

- **0:31:** frames the software-factory transition and the shift from implementation speed toward review/trust.
- **3:18:** discusses agentic code review and browser-based testing as deterministic feedback mechanisms.
- **7:13:** asks how to minimize the amount of code humans must read without losing system understanding.
- **13:01:** emphasizes back-pressure and deterministic evaluation rather than relying on vague confidence.
- **16:00:** describes architecture/program design conversations before allowing the coding agent to implement.
- **36:48:** discusses the agent assembling context from RAG, history, memory, and prompt/context mechanisms.
- **46:48:** emphasizes finding and improving the real bottleneck rather than optimizing a non-bottleneck station.

These anchors are used here as engineering principles, not as claims that the video proves a particular Sarembok implementation.

## Done signal

A Sarembok feature is ready to leave the implementation lane only when:

1. the user-visible success condition is explicit;
2. the architecture and important call paths are documented;
3. the smallest vertical slice works in the real runtime;
4. deterministic tests pass;
5. live health/RPC behavior is verified when applicable;
6. the result is consistent with authoritative runtime state; and
7. unresolved limitations are stated instead of invented away.
