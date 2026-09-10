/**
 * Antigravity Gemini Fabric - Strategist / Orchestrator Node
 * Sovereign Protocol [DIRECTIVE-01]
 * 
 * Parses primary tasks, establishes boundary constraints, delegates work to
 * execution Workers, and handles conflict resolution & loop mitigation directives.
 */

import { AgentRole, AgentStatus, MessageType } from './types.js';

export class StrategistNode {
  /**
   * @param {Object} config
   * @param {string} [config.agentId='strategist-primary']
   * @param {import('../memory/wal_store.js').WalStore} config.walStore
   * @param {import('./bus.js').MessageBus} config.bus
   * @param {import('../guardrails/rollback_manager.js').RollbackManager} config.rollbackManager
   */
  constructor({
    agentId = 'strategist-primary',
    walStore,
    bus,
    rollbackManager
  }) {
    this.agentId = agentId;
    this.walStore = walStore;
    this.bus = bus;
    this.rollbackManager = rollbackManager;

    // Register node in WAL
    this.walStore.registerAgent(this.agentId, AgentRole.STRATEGIST, AgentStatus.IDLE);

    // Register on bus
    this.bus.registerHandler(this.agentId, this.handleIncomingMessage.bind(this));
  }

  /**
   * Handle incoming protocol message
   * @param {Object} msg
   */
  async handleIncomingMessage(msg) {
    return {
      status: 'ACK',
      agentId: this.agentId,
      receivedType: msg.type
    };
  }

  /**
   * Parse user intent, decompose into subtasks, and apply constraints
   * @param {string} prompt
   */
  decomposeTask(prompt) {
    // Check if there are active loop mitigation directives
    return {
      objective: prompt,
      subtasks: [
        {
          id: `subtask_1_${Date.now()}`,
          action: 'analyze_and_extract',
          data: { prompt }
        },
        {
          id: `subtask_2_${Date.now()}`,
          action: 'execute_core_operation',
          data: { prompt }
        }
      ],
      constraints: {
        maxChars: 50000,
        disallowDangerousScripts: true
      }
    };
  }

  /**
   * Delegate subtask to target worker node
   * @param {Object} params
   * @param {string} params.sessionId
   * @param {string} params.workerId
   * @param {Object} params.subtask
   * @param {Object} [params.boundaryParameters]
   */
  async delegateToWorker({ sessionId, workerId, subtask, boundaryParameters }) {
    // 1. Check for loop mitigation directives
    const directives = this.rollbackManager.getDirectives(sessionId);
    if (directives.length > 0) {
      // Incorporate mitigation directive into subtask payload to break loop
      const latestDirective = directives[directives.length - 1];
      subtask.systemDirective = latestDirective.directive;
      this.rollbackManager.clearDirectives(sessionId);
    }

    // 2. Record delegation intention to WAL first to establish foreign key reference
    this.walStore.appendTransaction({
      taskId: subtask.id,
      sessionId,
      senderAgentId: this.agentId,
      recipientAgentId: workerId,
      payload: { action: 'DELEGATE_TASK', workerId, subtask },
      tokensConsumed: 10,
      committed: true
    });

    this.walStore.updateAgentStatus(this.agentId, AgentStatus.BUSY, subtask.id);

    // 3. Send via message bus
    const workerResult = await this.bus.send({
      sessionId,
      from: this.agentId,
      to: workerId,
      type: MessageType.TASK_DELEGATION,
      payload: { ...subtask, boundaryParameters }
    });

    this.walStore.updateAgentStatus(this.agentId, AgentStatus.IDLE, null);
    return workerResult;
  }

  /**
   * Request verification signature from Auditor
   * @param {Object} params
   * @param {string} params.sessionId
   * @param {string} params.auditorId
   * @param {string} params.workerId
   * @param {any} params.workerOutput
   * @param {Object} params.boundaryParameters
   */
  async requestAudit({ sessionId, auditorId = 'auditor-primary', workerId, workerOutput, boundaryParameters }) {
    return await this.bus.send({
      sessionId,
      from: this.agentId,
      to: auditorId,
      type: MessageType.AUDIT_REQUEST,
      payload: { workerId, workerOutput, boundaryParameters }
    });
  }
}
