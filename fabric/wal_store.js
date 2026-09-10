/**
 * Antigravity Gemini Fabric - Universal SQLite-WAL Storage Wrapper
 * Sovereign Protocol [DIRECTIVE-01]
 * 
 * Supports both CommonJS require() and ESM import.
 */

const { DatabaseSync } = require('node:sqlite');
const { randomUUID } = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');

class WalStore {
  /**
   * @param {string} [dbPath=':memory:'] Path to SQLite database file or ':memory:'
   */
  constructor(dbPath = ':memory:') {
    this.dbPath = dbPath;
    this.db = new DatabaseSync(this.dbPath);
    this.init();
  }

  /**
   * Initialize tables and enforce WAL mode pragmas with zero cyclic dependency
   */
  init() {
    if (this.dbPath !== ':memory:') {
      this.db.exec('PRAGMA journal_mode = WAL;');
    }
    this.db.exec('PRAGMA synchronous = NORMAL;');
    this.db.exec('PRAGMA foreign_keys = ON;');

    const schemaPath = path.join(__dirname, 'src', 'memory', 'schema.sql');
    let schemaDdl;
    if (fs.existsSync(schemaPath)) {
      schemaDdl = fs.readFileSync(schemaPath, 'utf-8');
    } else {
      schemaDdl = `
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
            last_heartbeat TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS transaction_log (
            task_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            sender_agent_id TEXT NOT NULL,
            recipient_agent_id TEXT,
            payload TEXT NOT NULL,
            tokens_consumed INTEGER DEFAULT 0,
            entropy_score REAL DEFAULT 0.0,
            validation_hash TEXT,
            committed INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(session_id) REFERENCES session_state(session_id),
            FOREIGN KEY(sender_agent_id) REFERENCES agent_nodes(agent_id)
        );

        CREATE INDEX IF NOT EXISTS idx_tx_session ON transaction_log(session_id, committed);
        CREATE INDEX IF NOT EXISTS idx_tx_entropy ON transaction_log(entropy_score) WHERE committed = 1;
        CREATE INDEX IF NOT EXISTS idx_tx_sender ON transaction_log(sender_agent_id);
      `;
    }

    this.db.exec(schemaDdl);

    // Seed internal sovereign kernel agents to satisfy foreign keys
    this.db.exec(`
      INSERT OR IGNORE INTO agent_nodes (agent_id, role, status, current_task_id)
      VALUES 
        ('STRATEGIST', 'STRATEGIST', 'IDLE', NULL),
        ('WORKER', 'WORKER', 'IDLE', NULL),
        ('AUDITOR', 'AUDITOR', 'IDLE', NULL),
        ('KERNEL_GUARDRAIL', 'AUDITOR', 'IDLE', NULL),
        ('SYSTEM', 'STRATEGIST', 'IDLE', NULL);
    `);
  }

  /**
   * Task B: Inserts the initial session boundary record
   * @param {string} [sessionId]
   * @param {number} [hardCap=100000]
   */
  initializeSession(sessionId = randomUUID(), hardCap = 100000) {
    const stmt = this.db.prepare(`
      INSERT INTO session_state (session_id, global_status, token_burned, hard_cap)
      VALUES (?, 'AWAITING_WORKLOAD', 0, ?)
      ON CONFLICT(session_id) DO UPDATE SET
        global_status = 'AWAITING_WORKLOAD',
        token_burned = 0,
        hard_cap = excluded.hard_cap,
        updated_at = CURRENT_TIMESTAMP
    `);
    stmt.run(sessionId, hardCap);
    return this.getSession(sessionId);
  }

  createSession(sessionId, hardCap) {
    return this.initializeSession(sessionId, hardCap);
  }

  getSession(sessionId) {
    const stmt = this.db.prepare('SELECT * FROM session_state WHERE session_id = ?');
    return stmt.get(sessionId);
  }

  updateSessionStatus(sessionId, status) {
    const stmt = this.db.prepare(`
      UPDATE session_state 
      SET global_status = ?, updated_at = CURRENT_TIMESTAMP 
      WHERE session_id = ?
    `);
    stmt.run(status, sessionId);
    return this.getSession(sessionId);
  }

  burnTokens(sessionId, count) {
    const stmt = this.db.prepare(`
      UPDATE session_state
      SET token_burned = token_burned + ?, updated_at = CURRENT_TIMESTAMP
      WHERE session_id = ?
    `);
    stmt.run(count, sessionId);
    return this.getSession(sessionId);
  }

  registerAgent(agentId, role, status = 'IDLE') {
    const stmt = this.db.prepare(`
      INSERT INTO agent_nodes (agent_id, role, status, current_task_id)
      VALUES (?, ?, ?, NULL)
      ON CONFLICT(agent_id) DO UPDATE SET
        role = excluded.role,
        status = excluded.status,
        last_heartbeat = CURRENT_TIMESTAMP
    `);
    stmt.run(agentId, role, status);
    return this.getAgent(agentId);
  }

  updateAgentStatus(agentId, status, currentTaskId = null) {
    const stmt = this.db.prepare(`
      UPDATE agent_nodes
      SET status = ?, current_task_id = ?, last_heartbeat = CURRENT_TIMESTAMP
      WHERE agent_id = ?
    `);
    stmt.run(status, currentTaskId, agentId);
    return this.getAgent(agentId);
  }

  getAgent(agentId) {
    const stmt = this.db.prepare('SELECT * FROM agent_nodes WHERE agent_id = ?');
    return stmt.get(agentId);
  }

  listAgents() {
    const stmt = this.db.prepare('SELECT * FROM agent_nodes ORDER BY agent_id ASC');
    return stmt.all();
  }

  /**
   * Task B: Atomically appends a transaction step to the WAL log
   * Handles dynamic signature:
   * (taskId, sessionId, senderId, recipientId, payload, tokens, entropy, hash)
   * OR
   * (taskId, sessionId, senderId, payload, tokens, entropy, hash, recipientId)
   */
  commitMicroStep(
    taskId = randomUUID(),
    sessionId,
    senderId,
    arg4,
    arg5 = 0,
    arg6 = 0.0,
    arg7 = null,
    arg8 = null,
    committed = true
  ) {
    let recipientId = null;
    let payload;
    let tokens = 0;
    let entropy = 0.0;
    let hash = null;

    // Check if 4th argument is recipientId string or payload
    if (typeof arg4 === 'string' && (typeof arg5 === 'object' || (typeof arg5 === 'string' && arg6 !== undefined))) {
      recipientId = arg4;
      payload = arg5;
      tokens = typeof arg6 === 'number' ? arg6 : 0;
      entropy = typeof arg7 === 'number' ? arg7 : 0.0;
      hash = arg8;
    } else {
      payload = arg4;
      tokens = typeof arg5 === 'number' ? arg5 : 0;
      entropy = typeof arg6 === 'number' ? arg6 : 0.0;
      hash = arg7;
      recipientId = arg8;
    }

    const payloadStr = typeof payload === 'string' ? payload : JSON.stringify(payload);

    const stmt = this.db.prepare(`
      INSERT OR REPLACE INTO transaction_log (
        task_id, session_id, sender_agent_id, recipient_agent_id,
        payload, tokens_consumed, entropy_score, validation_hash, committed
      )
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    `);

    stmt.run(
      taskId,
      sessionId,
      senderId,
      recipientId,
      payloadStr,
      tokens,
      entropy,
      hash,
      committed ? 1 : 0
    );

    // Increment session token burn count if tokens were consumed
    if (tokens > 0) {
      this.burnTokens(sessionId, tokens);
    }

    return {
      task_id: taskId,
      session_id: sessionId,
      sender_agent_id: senderId,
      recipient_agent_id: recipientId,
      payload: payloadStr,
      tokens_consumed: tokens,
      entropy_score: entropy,
      validation_hash: hash,
      committed: committed ? 1 : 0
    };
  }

  appendTransaction(options) {
    return this.commitMicroStep(
      options.taskId || randomUUID(),
      options.sessionId,
      options.senderAgentId || options.senderId,
      options.recipientAgentId || options.recipientId,
      options.payload,
      options.tokensConsumed || options.tokens || 0,
      options.entropyScore || options.entropy || 0.0,
      options.validationHash || options.hash || null,
      options.committed !== false
    );
  }

  rollbackStep(taskId) {
    const stmt = this.db.prepare(`
      UPDATE transaction_log
      SET committed = 0
      WHERE task_id = ?
    `);
    const result = stmt.run(taskId);
    return result.changes > 0;
  }

  rollbackTransaction(taskId) {
    return this.rollbackStep(taskId);
  }

  /**
   * Task B: Rebuilds the memory array by scanning only active committed = 1 steps sequentially
   * @param {string} sessionId
   */
  reconstituteState(sessionId) {
    const session = this.getSession(sessionId);
    if (!session) {
      throw new Error(`Session '${sessionId}' not found.`);
    }

    const stmt = this.db.prepare(`
      SELECT 
        task_id, session_id, sender_agent_id, recipient_agent_id,
        payload, tokens_consumed, entropy_score, validation_hash,
        created_at
      FROM transaction_log
      WHERE session_id = ? AND committed = 1
      ORDER BY rowid ASC
    `);
    const committedSteps = stmt.all(sessionId);

    const memoryArray = committedSteps.map((step) => {
      let parsedPayload;
      try {
        parsedPayload = JSON.parse(step.payload);
      } catch {
        parsedPayload = step.payload;
      }

      return {
        taskId: step.task_id,
        senderId: step.sender_agent_id,
        recipientId: step.recipient_agent_id,
        payload: parsedPayload,
        tokensConsumed: step.tokens_consumed,
        entropyScore: step.entropy_score,
        validationHash: step.validation_hash,
        createdAt: step.created_at
      };
    });

    // Provide dual Array and Object interface
    memoryArray.sessionId = session.session_id;
    memoryArray.globalStatus = session.global_status;
    memoryArray.tokenBurned = session.token_burned;
    memoryArray.hardCap = session.hard_cap;
    memoryArray.stepCount = memoryArray.length;
    memoryArray.memoryArray = memoryArray;

    return memoryArray;
  }

  getLatestTransaction(sessionId) {
    const stmt = this.db.prepare(`
      SELECT * FROM transaction_log 
      WHERE session_id = ? AND committed = 1
      ORDER BY rowid DESC 
      LIMIT 1
    `);
    return stmt.get(sessionId);
  }

  getRecentTransactions(sessionId, limit = 5, committedOnly = true, senderAgentId = null) {
    let sql = `
      SELECT * FROM transaction_log
      WHERE session_id = ? ${committedOnly ? 'AND committed = 1' : ''}
    `;
    const params = [sessionId];

    if (senderAgentId) {
      sql += ' AND sender_agent_id = ?';
      params.push(senderAgentId);
    }

    sql += ' ORDER BY rowid DESC LIMIT ?';
    params.push(limit);

    const stmt = this.db.prepare(sql);
    const rows = stmt.all(...params);
    return rows.reverse();
  }

  getAllCommittedTransactions(sessionId) {
    const stmt = this.db.prepare(`
      SELECT * FROM transaction_log
      WHERE session_id = ? AND committed = 1
      ORDER BY rowid ASC
    `);
    return stmt.all(sessionId);
  }

  close() {
    this.db.close();
  }
}

module.exports = WalStore;
module.exports.WalStore = WalStore;
module.exports.default = WalStore;
