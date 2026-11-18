# SarembokVE (Sarembok)

**SarembokVE** — also known as **Sarembok** — is an AI-native execution runtime, distributed GPU and heterogeneous compute mesh, deterministic multi-agent orchestration platform, zero-trust execution fabric, and OpenAPI contract governance system.

Official platform: **[SarembokVE (Sarembok) at sarembok.com](https://sarembok.com)**

[![CI](https://github.com/jetsontech/SarembokVE/actions/workflows/ci.yml/badge.svg)](https://github.com/jetsontech/SarembokVE/actions/workflows/ci.yml)
[![License: BSL-1.1](https://img.shields.io/badge/License-BSL--1.1-blue.svg)](LICENSE)
[![Tests: 34 Passing](https://img.shields.io/badge/Tests-34%20Passing-brightgreen.svg)](test/)
[![Security: NVIDIA OpenShell](https://img.shields.io/badge/Security-NVIDIA%20OpenShell%20Zero--Trust-blueviolet.svg)](Docs/SECURITY.md)
[![ADR: Documented](https://img.shields.io/badge/Architecture-ADR--001%20Modular-informational.svg)](Docs/ADR.md)

**Modular AI-Native Computing Environment, Zero-Trust Execution Fabric, and Automated Contract Governance.**

SarembokVE is built with a **3-Tier Progressive Adoption Architecture**—ranging from a 30-second drop-in CI/CD GitHub Action for standard React/Next.js/Node web apps to an enterprise distributed agentic mesh with Raft consensus and SQLite-WAL state machines.

[Console](https://sarembok.com) · [Live Terminal Simulator](public/demo_terminal.html) · [Quickstart Guide](#quickstart-in-10-seconds) · [Solutions & 12 Use Cases](Docs/SOLUTIONS_AND_USE_CASES.md) · [Architecture Decision Records](Docs/ADR.md) · [Status](https://sarembok.com/status) · [Security Architecture](Docs/SECURITY.md)

---

## Progressive Adoption (Use Only What You Need)

| Tier | Component | Setup Time | Primary Goal | Target Audience |
| :--- | :--- | :--- | :--- | :--- |
| **Tier 1** | GitHub Action (`.github/workflows/sarembok.yml`) | **30 seconds** | Zero-trust contract gating, automated drift detection, PR comments | React, Next.js, Node.js developers |
| **Tier 2** | Local Runtime (`sarembok-runtime`) | **2 minutes** | Local evaluation, sandboxed execution, SQLite-WAL state machine | Local dev & testing |
| **Tier 3** | Enterprise Distributed Mesh (`sarembok-mesh`) | **Production** | Raft consensus, multi-node clustering, zero-trust fabric | Enterprise engineering teams |

---

## Quickstart in 10 Seconds

Add SarembokVE to any React/Next.js/Node repository:

```yaml
name: SarembokVE Security & Contract Gate
on: [push, pull_request]

jobs:
  sarembok-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: jetsontech/SarembokVE@v1
        with:
          profile: strict
          audit-report: true
```

---

## Live Interactive Simulation & Video Tour

Watch the full automated walkthrough of all 16 commands in action with real-time zero-trust policy checks, Macaroon token minting, and SQLite-WAL state machines:

[![SarembokVE Live CLI & Troubleshooting Demo](public/videos/sarembok_cli_troubleshooting_demo.webp)](public/demo_terminal.html)

> 💡 **Try it live**: Launch the [Interactive Terminal Simulator](public/demo_terminal.html) directly in your browser with automated playback and failure troubleshooting modes.

---

## Key Capabilities

* **Zero-Trust Execution Fabric:** Enforces least-privilege capability tokens for local and cloud environments.
* **Contract Diffing & Drift Gating:** Prevents breaking API changes during CI build steps.
* **SQLite-WAL State Engine:** Low-latency transactional audit logs and execution history.
* **Raft Consensus Integration:** Multi-node synchronization and distributed state management.
* **NVIDIA OpenShell Security Rules:** Native profile enforcement for enterprise workloads.

---

## Architecture & Documentation

- [Architecture Decision Records (ADR)](Docs/ADR.md)
- [Solutions & 12 Use Cases](Docs/SOLUTIONS_AND_USE_CASES.md)
- [Security Architecture & Profiles](Docs/SECURITY.md)

---

## Security Containment Profiles

Configured via `Config/openshell.policy.yaml` and `Config/openshell.profiles.json`:

| Profile | Target Environment | Filesystem | Network Egress | HITL Required Actions | Secret Zero |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`strict`** (default) | Production / Banking | Read-only root | Whitelist only | All DB writes, financial, cloud destroy | Enforced |
| **`enterprise`** | Corporate Infrastructure | Read-only root | Whitelist + Intranet | Production DB, cloud destroy | Enforced |
| **`audit`** | Playwright Web Crawler | Read-only root | HTTP/HTTPS only | None (automated extraction) | Enforced |
| **`developer`** | Local Workstation | Read-write | Unrestricted | Financial transactions only | Optional |

---

## Test Suite & Verification

All automated tests pass cleanly with 0 external background daemons required:

```bash
# Fast Node.js test suite (26 passing tests)
npm test

# Fast alias
npm run test:fast
```

Test coverage includes:
- **Contract Diffing & Drift Gating**: 6 tests verifying breaking vs additive changes and schema synthesis.
- **Shannon Entropy Evaluator & Voice Fabric**: 4 tests verifying loop defense and vector rollback SVG generation.
- **NVIDIA OpenShell Supervisor & HITL**: 4 tests verifying deny-patterns, profile switching, and credential masking.
- **Distributed Fabric & Memory Subsystem**: Raft leader election, WAL replay, capability tokens, and state machine projection.
- **Cognitive Router & Visualizer**: Multi-provider circuit breakers, semantic caching, and tamper-proof HTML audit reports.

---

## Leadership & Architecture

Sarembok VE is developed and architected by the SarembokVE team, led by **Tim Hall**, its Founder and AI Systems Architect. Tim founded SarembokVE and leads its overall technical vision, systems architecture, and development direction.

---

## License

SarembokVE is licensed under the **Business Source License 1.1 (BSL-1.1)**. See [LICENSE](LICENSE) and [TRADEMARK.md](TRADEMARK.md) for commercial licensing and brand protection terms.
