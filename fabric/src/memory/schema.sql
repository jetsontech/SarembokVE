-- =====================================================================
-- ANTIGRAVITY GEMINI KERNEL - CORRECTED ENGINE STRUCTURE (schema.sql)
-- =====================================================================
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
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
    role TEXT NOT NULL,                             -- STRATEGIST, WORKER, AUDITOR
    status TEXT DEFAULT 'IDLE',                     -- IDLE, BUSY, FROZEN, HALTED
    current_task_id TEXT,                           -- Resolved at runtime via cross-table updates
    last_heartbeat TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS transaction_log (
    task_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    sender_agent_id TEXT NOT NULL,
    recipient_agent_id TEXT,
    payload TEXT NOT NULL,                          -- Raw JSON micro-step string
    tokens_consumed INTEGER DEFAULT 0,
    entropy_score REAL DEFAULT 0.0,
    validation_hash TEXT,
    committed INTEGER DEFAULT 1,                    -- 1 = Valid state, 0 = Rolled back
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(session_id) REFERENCES session_state(session_id),
    FOREIGN KEY(sender_agent_id) REFERENCES agent_nodes(agent_id)
);

CREATE INDEX IF NOT EXISTS idx_tx_session ON transaction_log(session_id, committed);
CREATE INDEX IF NOT EXISTS idx_tx_entropy ON transaction_log(entropy_score) WHERE committed = 1;
CREATE INDEX IF NOT EXISTS idx_tx_sender ON transaction_log(sender_agent_id);
