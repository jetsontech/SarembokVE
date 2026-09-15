# ADR: Open-Model-First Frontier Architecture

## Status
Accepted

## Decision

SarembokVE is **open-model-first** and **self-hosting-ready**.

> **WE DON'T BUY IT. WE BUILD IT.**

The core execution fabric must remain capable of operating with open-weight
models and Sarembok-controlled GPU workers. Hosted inference providers are
acceleration paths, not architectural ownership boundaries.

External frontier models are an optional **review council**. They provide
independent critique of architecture, implementation, security, and verification
when their credentials are configured. They are not required for ordinary
Sarembok operation.

## Execution hierarchy

1. Sarembok-owned/open-weight models and workers.
2. Open-model inference providers such as Groq/OpenRouter when useful.
3. Sarembok-controlled GPU worker capacity as hardware becomes available.
4. Proprietary frontier models for independent review/specialist reasoning.

## Review council

The initial council contract supports:

- OpenAI `gpt-5.1-codex-max` for long-horizon coding and implementation review.
- Anthropic `claude-opus-4-8` for independent architecture/reasoning review.

Credentials are optional and must never be inferred from model metadata.

## Required invariants

- No proprietary provider is a hard dependency for core runtime operation.
- Model selection is capability-based rather than UI-name-based.
- Open-weight model availability is separated from provider availability.
- Local model inventory is explicit (`SAREMBOK_LOCAL_OPEN_MODELS`).
- Review findings are evidence, not automatic authority to mutate production.
- Production changes require deterministic verification and a decision gate.
- Secrets are never returned in capability or telemetry payloads.

## Engineering loop

```text
PRODUCT
  -> SYSTEM ARCHITECTURE
  -> PROGRAM DESIGN
  -> VERTICAL SLICE
  -> IMPLEMENTATION
  -> DETERMINISTIC VERIFICATION
  -> INDEPENDENT REVIEW
  -> RECONCILIATION / DECISION GATE
  -> LIVE RUNTIME PROOF
```
