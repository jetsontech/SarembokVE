# ARCHITECTURAL & UX HANDOFF: ANTIGRAVITY GEMINI FABRIC (V3.8-FLASH-MEDIUM)
## CONTEXT: SOVEREIGN PROTOCOL [DIRECTIVE-01] · EDGE-NATIVE RUNTIME KERNEL
## DEPLOYMENT ROOT: `c:/SarembokVE/fabric/` & `c:/SarembokVE/frontend/`
## TARGET MODEL / ENGINE: Antigravity Gemini V3.8-Flash-Medium

---

## 1. STRATEGIC MISSION & SYSTEM IDENTITY
**Antigravity Gemini (V3.8-Flash-Medium)** is an anchorless, zero-dependency cognitive orchestration kernel designed to execute multi-agent micro-steps directly in local edge environments and standard browser sandboxes without the latency, fragility, or overhead of monolithic cloud agent frameworks.

### The Core Architectural Pillars:
1. **Lightweight Edge Storage**: SQLite in WAL mode (`PRAGMA journal_mode = WAL; PRAGMA foreign_keys = ON;`) capturing micro-step state deltas (`transaction_log`) rather than ballooning in-memory trees.
2. **Decoupled Asynchronous Micro-Envelopes**: An event-driven bus (`bus.js`) passing transactional envelopes between decoupled agents without blocking thread stacks.
3. **Shannon Entropy Loop Defense**: A mathematical sliding-window evaluator (`entropy_evaluator.js`) halting recursive loops when repetition entropy reaches $\ge 0.88$.
4. **Cybernetic Command Center**: A zero-latency, high-fidelity UI overhaul in `c:/SarembokVE/frontend/index.html` giving operators direct visual feedback, telemetry, and interactive flight controls.

---

## 2. SYSTEM ARCHITECTURE & FILE MANIFEST

```
c:/SarembokVE/
├── fabric/
│   ├── src/
│   │   ├── memory/
│   │   │   └── schema.sql              # Corrected DDL: session_state, agent_nodes, transaction_log
│   │   ├── bus.js                      # Async EventEmitter transaction bus
│   │   ├── strategist.js               # Payload decomposition & historical WAL snapshot queries
│   │   ├── worker.js                   # Micro-step Promise runner with strict timeout watchdog (5000ms)
│   │   ├── auditor.js                  # HMAC-SHA256 signer, entropy evaluator, hard cap enforcer
│   │   └── flywheel.js                 # End-to-end loop orchestrator connecting all 3 nodes
│   ├── ui/
│   │   ├── index.html                  # Quadrants A, B, C high-density cockpit dashboard
│   │   ├── server_ui.js                # Native Node.js HTTP bridge server (Port 3800, /api/telemetry)
│   │   └── mock_feed.js                # Live simulation feeding steps, state flares, & loop rollbacks
│   ├── wal_store.js                    # Universal SQLite-WAL driver (CJS & ESM compatible)
│   ├── entropy_evaluator.js            # Sliding-window Shannon entropy calculator (<0.88 safety limit)
│   ├── test/
│   │   ├── verify_kernel.js            # Flight assertions: session init, micro-step, rollback, reconstitute
│   │   ├── verify_loop.js              # Recursive loop interception test (entropy >= 0.88)
│   │   ├── verify_rollback.js          # Atomic rollback verification on worker timeout/fault
│   │   └── verify_e2e_flywheel.js      # Full flywheel lifecycle test
│   └── package.json                    # Zero external framework dependencies; native node:sqlite support
│
├── frontend/
│   └── index.html                      # Cybernetic Command Deck with integrated Antigravity Fabric panel (Port 3000)
│
└── ANTIGRAVITY_3.8_FLASH_UX_HANDOFF.md # This precise handoff specification
```

---

## 3. VISIBLE UI OVERHAUL & UX SPECIFICATION

Operators can visibly view and interact with the overhaul immediately by opening **`http://localhost:3000`** in any web browser (or loading `c:\SarembokVE\frontend\index.html` directly).

### A. Surface Enhancements Across the Dashboard:
1. **Top Header HUD**:
   - Dedicated **`FABRIC: V3.8-FLASH`** quick-status button with cyan halo. Clicking it instantly switches to the Fabric workspace.
2. **Cybernetic Marquee Ticker**:
   - Real-time notification: `◇ ANTIGRAVITY GEMINI FABRIC (V3.8-FLASH-MEDIUM) · SOVEREIGN DIRECTIVE-01`.
3. **Left Vertical Icon Dock**:
   - Dedicated **⚡ Antigravity Fabric** button (`#dock-btn-fabric`) positioned seamlessly between memory and research tools.
4. **Command Deck (View 1 - Main Landing)**:
   - **Card 4: Fabric Kernel · V3.8**: Displays real-time kernel status, current Shannon entropy, token burn progress, and quick-dispatch step buttons.

### B. Dedicated View Panel 8 (`#view-fabric`):
- **Sovereign Telemetry HUD**:
  - **Kernel Status**: Live state indicator (`ONLINE / READY`, `EXECUTING STEP`, `HALTED: LOOP PREVENTED`, `HALTED: HARD CAP EXHAUSTED`).
  - **Token Hard-Cap Meter**: Dynamic visual progress gauge reflecting burned tokens vs. hard limit ($100,000$).
  - **Shannon Entropy Gauge**: Real-time display of window entropy. Stays emerald at $\le 0.87$; pulses radiant red with high-priority alert if $\ge 0.88$.
- **Multi-Agent Flywheel Nodes Grid**:
  - **Strategist Node** (`role: STRATEGIST`): Intercepts user workload payload, inspects WAL baseline.
  - **Worker Node** (`role: WORKER`): Executes promise steps bounded by a 5,000ms watchdog timer.
  - **Auditor Node** (`role: AUDITOR`): Signs transactions with HMAC-SHA256 and computes loop entropy.
- **Interactive Execution Console**:
  - `[ ⚡ EXECUTE FLYWHEEL STEP ]`: Submits a custom directive, cycling through Strategist $\to$ Worker $\to$ Auditor $\to$ SQLite-WAL.
  - `[ 🔄 RECONSTITUTE STATE FROM WAL ]`: Queries the WAL log and reconstitutes the entire memory tree dynamically.
  - `[ ⚠️ SIMULATE RECURSIVE LOOP (>0.88) ]`: Deliberately triggers the loop watchdog ($\text{entropy} = 0.94$), demonstrating instant thread interception and rollback.
  - `[ 🛑 TEST HARD-CAP HALT ]`: Demonstrates token budget hard-cap clamping ($100,000 / 100,000$).
  - `[ 🧹 RESET SESSION ]`: Initializes a clean session envelope and clears previous state.
- **Live SQLite-WAL Transaction Stream & JSON State Inspector**:
  - Real-time table displaying Step ID, Agent Node, Commit Status, Token Cost, Entropy Score, Timestamp, and HMAC Checksum.
### C. High-Density Developer Cockpit (`http://localhost:3800`):
Located at `c:/SarembokVE/fabric/ui/` and served via native Node.js HTTP stream bridge (`server_ui.js`):
- **Quadrant A: System State & Token Telemetry (Header)**:
  - **Visual Status Indicator**: Real-time pulse mapping `session_state.global_status`:
    - `RUNNING` $\implies$ Active glowing emerald pulse
    - `AWAITING_WORKLOAD` $\implies$ Amber pulsing state
    - `HALTED` $\implies$ Solid red safety freeze
  - **Token Burn Meter**: Proportional linear progress bar reflecting live `token_burned` dynamically filling toward total `hard_cap` ($100,000$).
- **Quadrant B: The Agent Graph Canvas (Left Pane - 60% Width)**:
  - **Interactive Node Grid**: Visual cards for active agents: `STRATEGIST`, `WORKER`, and `AUDITOR`.
  - **Dynamic State Flares**:
    - When `status === 'BUSY'`: Border glows intense electric blue (`#00f0ff` / `#2563eb`).
    - When `status === 'FROZEN'`: Card border instantly flashes bright warning red (`#ef4444`) with high-priority pulse.
  - **Mission Controls**: Direct triggers to dispatch steps, simulate loops, inspect state reconstitution, and reset runtime.
  - **Reconstituted Active Memory View**: Real-time JSON tree of `wal.reconstituteState()`.
- **Quadrant C: The Ledger & Loop Telemetry (Right Pane - 40% Width)**:
  - **Continuous Memory Feed**: Auto-scrolling terminal window displaying rows pulled sequentially from `transaction_log`.
  - **Green Audit Signature Badges**: Every committed step prominently displays the verified cryptographic `validation_hash` generated by the Auditor node.
  - **Soft-Rollback Rows (`committed = 0`)**: Rendered grayed out with a strike-through to visually demonstrate loop interception and safety rollback!
- **Asynchronous 500ms Long-Poll Engine**:
  - Automatically queries `/api/telemetry` every 500ms to paint changes live with zero framework overhead.

---

## 4. RUNTIME DATA CONTRACTS

### A. Database Schema (`fabric/src/memory/schema.sql`)
```sql
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS session_state (
    session_id TEXT PRIMARY KEY,
    global_status TEXT DEFAULT 'AWAITING_WORKLOAD',
    token_burned INTEGER DEFAULT 0,
    hard_cap INTEGER NOT NULL,
    initialized_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS agent_nodes (
    agent_id TEXT PRIMARY KEY,
    role TEXT NOT NULL,
    status TEXT DEFAULT 'IDLE',
    current_task_id TEXT,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS transaction_log (
    step_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    step_status TEXT NOT NULL,
    payload_snapshot TEXT NOT NULL,
    token_cost INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(session_id) REFERENCES session_state(session_id),
    FOREIGN KEY(agent_id) REFERENCES agent_nodes(agent_id)
);
```

### B. Transaction Envelope Structure (`bus.js`)
```typescript
interface TransactionEnvelope {
    stepId: string;
    sessionId: string;
    agentId: string;
    role: "STRATEGIST" | "WORKER" | "AUDITOR";
    status: "PENDING" | "COMMITTED" | "ROLLED_BACK";
    payload: Record<string, any>;
    tokenCost: number;
    entropyScore: number;
    hmacSignature: string;
    timestamp: string;
}
```

### C. Shannon Entropy Safety Threshold (`entropy_evaluator.js`)
$$H(X) = -\sum_{i=1}^{n} P(x_i) \log_2 P(x_i)$$
- **Safe Execution Boundary**: $H_{norm} < 0.88$
- **Halt Condition**: $H_{norm} \ge 0.88$ $\implies$ Immediate thread interception and step rollback.

---

## 5. VALIDATION & VERIFICATION EVIDENCE

The entire test harness has been executed with zero failures:
```bash
cd c:/SarembokVE/fabric
npm test
```

### Test Suite Execution Output:
| Suite | Target | Status |
| :--- | :--- | :--- |
| `verify_kernel.js` | Session Init, Micro-Step Commit, Rollback, Reconstitution | **PASS** |
| `verify_loop.js` | Shannon Entropy Sliding Window Watchdog ($\ge 0.88$) | **PASS** |
| `verify_rollback.js` | Worker Watchdog Timeout (5000ms) & Atomic WAL Rollback | **PASS** |
| `verify_e2e_flywheel.js`| End-to-End Orchestrator (Strategist $\to$ Worker $\to$ Auditor) | **PASS** |
| `frontend/index.html` | Client-Side JavaScript Syntax & DOM Initialization | **PASS** |

---

## 6. OPERATIONAL INSTRUCTIONS FOR OPERATORS & AGENTS

1. **Viewing the Dashboard**:
   - Access **`http://localhost:3000`** in your browser.
   - Click the **⚡ Antigravity Fabric** tab on the left dock or the **FABRIC: V3.8-FLASH** button in the header.
2. **Testing Interactive Flights**:
   - Type any directive (e.g. *"Synthesize edge audio telemetry"*) and click **`EXECUTE FLYWHEEL STEP`**. Observe the live transaction added to the SQLite-WAL stream.
   - Click **`SIMULATE RECURSIVE LOOP (>0.88)`** to watch the auditor intercept repetitive loops and log a rollback.
   - Click **`RECONSTITUTE STATE FROM WAL`** to review the memory tree.
3. **Backend / Edge Kernel Execution**:
   - The edge micro-kernel can be triggered programmatically from Node.js or embedded directly inside browser WebWorkers using `wal_store.js` and `flywheel.js`.
