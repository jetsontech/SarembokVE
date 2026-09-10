/**
 * Antigravity Gemini Fabric - State Rollback & Context Re-Routing Manager
 * Sovereign Protocol [DIRECTIVE-01]
 * 
 * Executes immediate loop mitigation:
 * 1. Freezes offending agent thread
 * 2. Rolls back uncommitted WAL transaction
 * 3. Injects hard system directive into Strategist Agent prompt window
 */

export class RollbackManager {
  /**
   * @param {import('../memory/wal_store.js').WalStore} walStore
   */
  constructor(walStore) {
    this.walStore = walStore;
    this.strategistDirectives = new Map(); // sessionId -> string[]
  }

  /**
   * Execute immediate loop mitigation sequence
   * @param {Object} params
   * @param {string} params.sessionId
   * @param {string} params.agentId
   * @param {string} [params.uncommittedTxId]
   * @param {string} [params.reason]
   */
  mitigateLoop({ sessionId, agentId, uncommittedTxId = null, uncommittedTaskId = null, reason = 'Semantic loop detected' }) {
    // 1. Halt Execution: Freeze offending agent thread
    this.walStore.updateAgentStatus(agentId, 'FROZEN', null);

    // 2. State Rollback: Discard uncommitted transaction in WAL log if provided
    let rolledBack = false;
    const targetTaskId = uncommittedTaskId || uncommittedTxId;
    if (targetTaskId) {
      rolledBack = this.walStore.rollbackTransaction(targetTaskId);
    } else {
      // Find the latest transaction and check if it can be rolled back
      const latest = this.walStore.getLatestTransaction(sessionId);
      if (latest && (latest.sender_agent_id === agentId || latest.agent_id === agentId)) {
        rolledBack = this.walStore.rollbackTransaction(latest.task_id || latest.tx_id);
      }
    }

    // 3. Context Re-routing: Inject hard system directive for Strategist
    const directive = [
      `[SOVEREIGN GUARDRAIL INTERVENTION: LOOP MITIGATION]`,
      `CRITICAL: Agent '${agentId}' triggered recursive loop threshold.`,
      `Reason: ${reason}`,
      `Action: The offending transaction was rolled back and agent thread '${agentId}' was FROZEN.`,
      `Directive to Strategist: Do NOT repeat previous subtask assignment. Formulate an alternate path, decompose task into distinct primitives, or assign a replacement worker.`
    ].join('\n');

    if (!this.strategistDirectives.has(sessionId)) {
      this.strategistDirectives.set(sessionId, []);
    }
    this.strategistDirectives.get(sessionId).push({
      timestamp: Date.now(),
      agentId,
      directive
    });

    return {
      status: 'MITIGATED',
      frozenAgentId: agentId,
      rolledBack,
      directive
    };
  }

  /**
   * Retrieve active pending directives for the Strategist in a session
   * @param {string} sessionId
   */
  getDirectives(sessionId) {
    return this.strategistDirectives.get(sessionId) || [];
  }

  /**
   * Clear processed directives
   * @param {string} sessionId
   */
  clearDirectives(sessionId) {
    this.strategistDirectives.delete(sessionId);
  }
}
