/**
 * Antigravity Gemini Fabric - SQLite-WAL Transactional Memory Substrate
 * Sovereign Protocol [DIRECTIVE-01]
 * 
 * Zero-dependency, anchorless edge runtime storage wrapper.
 * Guarantees zero-loss atomic micro-step streaming to disk without holding
 * bulky JSON state trees in active RAM.
 */

import { DatabaseSync } from 'node:sqlite';
import { randomUUID } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

export class WalStore {
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

    const schemaDdl = readFileSync(join(__dirname, 'schema.sql'), 'utf-8');
    this.db.exec(schemaDdl);

    // Seed internal sovereign kernel agents to satisfy foreign keys
    this.db.exec(`
      INSERT OR IGNORE INTO agent_nodes (agent_id, role, status, current_task_id)
      VALUES 
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
        updated_at = CURRENT_TIMESTAMP
    `);
    stmt.run(sessionId, hardCap);
    return this.getSession(sessionId);
  }

  // Alias for backwards compatibility
  createSession(sessionId, hardCap) {
    return this.initializeSession(sessionId, hardCap);
  }

  /**
   * Retrieve session by ID
   * @param {string} sessionId
   */
  getSession(sessionId) {
    const stmt = this.db.prepare('SELECT * FROM session_state WHERE session_id = ?');
    return stmt.get(sessionId);
  }

  /**
   * Update session status
   * @param {string} sessionId
   * @param {string} status 'AWAITING_WORKLOAD' | 'RUNNING' | 'HALTED' | 'ERROR'
   */
  updateSessionStatus(sessionId, status) {
    const stmt = this.db.prepare(`
      UPDATE session_state 
      SET global_status = ?, updated_at = CURRENT_TIMESTAMP 
      WHERE session_id = ?
    `);
    stmt.run(status, sessionId);
    return this.getSession(sessionId);
  }

  /**
   * Atomically increment burned token counter
   * @param {string} sessionId
   * @param {number} count
   */
  burnTokens(sessionId, count) {
    const stmt = this.db.prepare(`
      UPDATE session_state
      SET token_burned = token_burned + ?, updated_at = CURRENT_TIMESTAMP
      WHERE session_id = ?
    `);
    stmt.run(count, sessionId);
    return this.getSession(sessionId);
  }

  /**
   * Register or update an agent node
   * @param {string} agentId
   * @param {string} role 'STRATEGIST' | 'WORKER' | 'AUDITOR'
   * @param {string} [status='IDLE']
   */
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

  /**
   * Update agent node status
   * @param {string} agentId
   * @param {string} status 'IDLE' | 'BUSY' | 'FROZEN' | 'HALTED'
   * @param {string|null} [currentTaskId=null]
   */
  updateAgentStatus(agentId, status, currentTaskId = null) {
    const stmt = this.db.prepare(`
      UPDATE agent_nodes
      SET status = ?, current_task_id = ?, last_heartbeat = CURRENT_TIMESTAMP
      WHERE agent_id = ?
    `);
    stmt.run(status, currentTaskId, agentId);
    return this.getAgent(agentId);
  }

  /**
   * Retrieve agent node by ID
   * @param {string} agentId
   */
  getAgent(agentId) {
    const stmt = this.db.prepare('SELECT * FROM agent_nodes WHERE agent_id = ?');
    return stmt.get(agentId);
  }

  /**
   * List all registered agents
   */
  listAgents() {
    const stmt = this.db.prepare('SELECT * FROM agent_nodes ORDER BY agent_id ASC');
    return stmt.all();
  }

  /**
   * Task B: Atomically appends a transaction step to the WAL log
   * @param {string} taskId
   * @param {string} sessionId
   * @param {string} senderId
   * @param {any} payload Raw JSON micro-step string or serializable object
   * @param {number} [tokens=0]
   * @param {number} [entropy=0.0]
   * @param {string|null} [hash=null]
   * @param {string|null} [recipientId=null]
   * @param {boolean} [committed=true]
   */
  commitMicroStep(
    taskId = randomUUID(),
    sessionId,
    senderId,
    payload,
    tokens = 0,
    entropy = 0.0,
    hash = null,
    recipientId = null,
    committed = true
  ) {
    const payloadStr = typeof payload === 'string' ? payload : JSON.stringify(payload);

    const stmt = this.db.prepare(`
      INSERT INTO transaction_log (
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

  /**
   * Adapter for object signature
   */
  appendTransaction({
    taskId = randomUUID(),
    sessionId,
    senderAgentId,
    senderId,
    recipientAgentId = null,
    recipientId = null,
    payload,
    tokensConsumed = 0,
    tokens = 0,
    entropyScore = 0.0,
    entropy = 0.0,
    validationHash = null,
    hash = null,
    committed = true
  }) {
    return this.commitMicroStep(
      taskId,
      sessionId,
      senderAgentId || senderId,
      payload,
      tokensConsumed || tokens,
      entropyScore || entropy,
      validationHash || hash,
      recipientAgentId || recipientId,
      committed
    );
  }

  /**
   * Task B: Switches the committed binary flag to 0 instead of physically destroying data
   * @param {string} taskId
   */
  rollbackStep(taskId) {
    const stmt = this.db.prepare(`
      UPDATE transaction_log
      SET committed = 0
      WHERE task_id = ?
    `);
    const result = stmt.run(taskId);
    return result.changes > 0;
  }

  // Alias for backwards compatibility
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

    // Reconstruct lightweight step array
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

    return {
      sessionId: session.session_id,
      globalStatus: session.global_status,
      tokenBurned: session.token_burned,
      hardCap: session.hard_cap,
      stepCount: memoryArray.length,
      memoryArray
    };
  }

  /**
   * Get the most recent transaction for a session
   * @param {string} sessionId
   */
  getLatestTransaction(sessionId) {
    const stmt = this.db.prepare(`
      SELECT * FROM transaction_log 
      WHERE session_id = ? AND committed = 1
      ORDER BY rowid DESC 
      LIMIT 1
    `);
    return stmt.get(sessionId);
  }

  /**
   * Get recent transactions for sliding-window evaluations
   * @param {string} sessionId
   * @param {number} [limit=5]
   * @param {boolean} [committedOnly=true]
   * @param {string|null} [senderAgentId=null]
   */
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

  /**
   * Get all committed transactions
   * @param {string} sessionId
   */
  getAllCommittedTransactions(sessionId) {
    const stmt = this.db.prepare(`
      SELECT * FROM transaction_log
      WHERE session_id = ? AND committed = 1
      ORDER BY rowid ASC
    `);
    return stmt.all(sessionId);
  }

  /**
   * Close database connection
   */
  close() {
    this.db.close();
  }
}
