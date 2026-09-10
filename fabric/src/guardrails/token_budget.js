/**
 * Antigravity Gemini Fabric - Strict Token Budget Guardrail
 * Sovereign Protocol [DIRECTIVE-01]
 * 
 * Tracks cumulative token consumption per session and enforces hard stop:
 * if (current_burn >= hard_cap) trigger_safe_halt()
 */

export class TokenCapExceededError extends Error {
  constructor(sessionId, burned, hardCap) {
    super(`Token hard cap exceeded for session '${sessionId}': burned ${burned} >= cap ${hardCap}. Execution halted.`);
    this.name = 'TokenCapExceededError';
    this.sessionId = sessionId;
    this.burned = burned;
    this.hardCap = hardCap;
  }
}

export class TokenBudgetGuard {
  /**
   * @param {import('../memory/wal_store.js').WalStore} walStore
   */
  constructor(walStore) {
    this.walStore = walStore;
  }

  /**
   * Check budget and record consumed tokens.
   * If limit breached, triggers safe halt across session and all agents.
   * 
   * @param {string} sessionId
   * @param {number} tokensToBurn
   * @returns {{ status: 'OK' | 'HALTED', tokenBurned: number, hardCap: number }}
   */
  recordAndVerify(sessionId, tokensToBurn = 0) {
    const session = this.walStore.getSession(sessionId);
    if (!session) {
      throw new Error(`Session '${sessionId}' not found.`);
    }

    if (session.global_status === 'HALTED') {
      throw new TokenCapExceededError(sessionId, session.token_burned, session.hard_cap);
    }

    const updated = this.walStore.burnTokens(sessionId, tokensToBurn);

    if (updated.token_burned >= updated.hard_cap) {
      this.triggerSafeHalt(sessionId, updated.token_burned, updated.hard_cap);
      throw new TokenCapExceededError(sessionId, updated.token_burned, updated.hard_cap);
    }

    return {
      status: 'OK',
      tokenBurned: updated.token_burned,
      hardCap: updated.hard_cap
    };
  }

  /**
   * Trigger safe halt: set session to HALTED and freeze all active agents
   * @param {string} sessionId
   * @param {number} burned
   * @param {number} hardCap
   */
  triggerSafeHalt(sessionId, burned, hardCap) {
    // 1. Update session status
    this.walStore.updateSessionStatus(sessionId, 'HALTED');

    // 2. Halt all registered agents
    const agents = this.walStore.listAgents();
    for (const ag of agents) {
      this.walStore.updateAgentStatus(ag.agent_id, 'HALTED', null);
    }

    // 3. Log an immutable audit transaction indicating the halt
    this.walStore.appendTransaction({
      sessionId,
      senderAgentId: 'KERNEL_GUARDRAIL',
      recipientAgentId: 'BROADCAST',
      payload: { action: 'TRIGGER_SAFE_HALT', burned, hardCap, status: 'HALTED', reason: 'TOKEN_HARD_CAP_REACHED' },
      committed: true
    });
  }
}
