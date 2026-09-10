/**
 * Antigravity Gemini Fabric - State Machine Projector
 * Sovereign Protocol [DIRECTIVE-01]
 * 
 * Recreates the active state machine on-demand by reducing over the append-only
 * SQLite-WAL transaction log without holding bulky objects in active RAM.
 */

export class StateMachineProjector {
  /**
   * @param {import('./wal_store.js').WalStore} walStore
   */
  constructor(walStore) {
    this.walStore = walStore;
    this.subscribers = new Set();
  }

  /**
   * Subscribe to live state transactions
   * @param {Function} callback
   */
  subscribe(callback) {
    this.subscribers.add(callback);
    return () => this.subscribers.delete(callback);
  }

  /**
   * Notify subscribers of a new transaction
   * @param {Object} tx
   */
  emitTransaction(tx) {
    for (const sub of this.subscribers) {
      try {
        sub(tx);
      } catch (err) {
        console.error('[StateMachineProjector] Subscriber error:', err);
      }
    }
  }

  /**
   * Reconstitute complete state from WAL on-demand
   * @param {string} sessionId
   */
  reconstituteState(sessionId) {
    const session = this.walStore.getSession(sessionId);
    if (!session) {
      throw new Error(`Session ${sessionId} not found.`);
    }

    const txLogs = this.walStore.getAllCommittedTransactions(sessionId);
    const agents = this.walStore.listAgents();

    const state = {
      sessionId: session.session_id,
      status: session.global_status,
      tokenBurned: session.token_burned,
      hardCap: session.hard_cap,
      stepCount: txLogs.length,
      initializedAt: session.initialized_at,
      updatedAt: session.updated_at,
      agents: {},
      taskHistory: [],
      latestValidationHash: null
    };

    for (const ag of agents) {
      state.agents[ag.agent_id] = {
        role: ag.role,
        status: ag.status,
        currentTaskId: ag.current_task_id,
        lastHeartbeat: ag.last_heartbeat
      };
    }

    for (const tx of txLogs) {
      let parsedPayload;
      try {
        parsedPayload = JSON.parse(tx.payload);
      } catch {
        parsedPayload = tx.payload;
      }

      state.taskHistory.push({
        taskId: tx.task_id,
        senderAgentId: tx.sender_agent_id,
        recipientAgentId: tx.recipient_agent_id,
        payload: parsedPayload,
        tokensConsumed: tx.tokens_consumed,
        entropyScore: tx.entropy_score,
        validationHash: tx.validation_hash,
        createdAt: tx.created_at
      });

      if (tx.validation_hash) {
        state.latestValidationHash = tx.validation_hash;
      }
    }

    return state;
  }
}
