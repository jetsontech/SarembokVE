# SarembokVE Frontier Control Plane

This document defines non-negotiable production invariants for the control plane.

## Execution identity
Every RPC receives an `executionId`. Mutating requests may supply an `idempotencyKey` and are de-duplicated for the configured retention window.

## Authorization
Browser sessions are USER-scoped. Runtime operator, administrator, master and worker identities are distinct. Unknown methods fail closed at the production boundary.

## Secrets
API keys, session tokens, worker credentials, administrator credentials and passcodes are never emitted in logs or error payloads.

## Capability truth
Operational status is derived from runtime state. Hardware claims remain explicitly self-reported until a worker capability probe or attestation succeeds.

## Distributed execution
Worker registration, heartbeat, task claim, completion and failure are expected to become lease-based and idempotent. A missing worker must never silently strand a task.

## Research provenance
Retrieved evidence, synthesis, inference and unresolved contradiction are separate concepts and must not be conflated.

## Observability
Execution ID, RPC method, role, provider/model, timing, finish state and failure class form the minimum execution telemetry contract.

## Recovery
Database persistence is insufficient without a verified backup and restore path. Production deployment must preserve a known-good rollback point.
