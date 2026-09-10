/**
 * Antigravity Gemini Fabric - Execution Worker Node
 * Sovereign Protocol [DIRECTIVE-01]
 * 
 * Single-purpose execution node with asynchronous Promise handler,
 * strict execution timeouts, and thread allocation guardrails that
 * yield control back to the operator upon threshold breach.
 */

import { AgentRole, AgentStatus, MessageType } from './types.js';

export class WorkerNode {
  /**
   * @param {Object} config
   * @param {string} config.agentId
   * @param {string} [config.specialty='code_emission'] 'code_emission' | 'log_scraping' | 'api_integration'
   * @param {import('../memory/wal_store.js').WalStore} config.walStore
   * @param {import('./bus.js').MessageBus} config.bus
   * @param {number} [config.timeoutMs=5000]
   * @param {number} [config.maxExecutionSteps=50]
   */
  constructor({
    agentId,
    specialty = 'general_execution',
    walStore,
    bus,
    timeoutMs = 5000,
    maxExecutionSteps = 50
  }) {
    this.agentId = agentId;
    this.specialty = specialty;
    this.walStore = walStore;
    this.bus = bus;
    this.timeoutMs = timeoutMs;
    this.maxExecutionSteps = maxExecutionSteps;
    this.taskHandler = null;

    // Register node in WAL
    this.walStore.registerAgent(this.agentId, AgentRole.WORKER, AgentStatus.IDLE);

    // Register on bus
    this.bus.registerHandler(this.agentId, this.handleIncomingMessage.bind(this));
  }

  /**
   * Set custom executor function for this worker node
   * @param {(task: any, signal?: AbortSignal) => Promise<any>} fn
   */
  setExecutor(fn) {
    this.taskHandler = fn;
  }

  /**
   * Handle incoming protocol message
   * @param {Object} msg
   */
  async handleIncomingMessage(msg) {
    if (msg.type === MessageType.TASK_DELEGATION) {
      return await this.executeTaskWithGuardrails(msg.sessionId, msg.payload, msg.correlationId);
    }
    throw new Error(`[WorkerNode ${this.agentId}] Unsupported message type: ${msg.type}`);
  }

  /**
   * Asynchronous execution handler with strict timeout and operator yield
   * @param {string} sessionId
   * @param {Object} taskPayload
   * @param {string} correlationId
   */
  async executeTaskWithGuardrails(sessionId, taskPayload, correlationId) {
    const taskId = taskPayload.taskId || `task_${Date.now()}`;
    const agent = this.walStore.getAgent(this.agentId);

    if (agent && (agent.status === AgentStatus.FROZEN || agent.status === AgentStatus.HALTED)) {
      return {
        status: 'REJECTED',
        error: `Worker ${this.agentId} cannot execute task: current status is ${agent.status}`,
        agentId: this.agentId,
        taskId
      };
    }

    try {
      this.walStore.updateAgentStatus(this.agentId, AgentStatus.BUSY, taskId);
    } catch {
      this.walStore.updateAgentStatus(this.agentId, AgentStatus.BUSY, null);
    }

    const controller = new AbortController();
    let timeoutTimer = null;

    // 1. Timeout Promise that triggers Operator Yield
    const timeoutPromise = new Promise((resolve) => {
      timeoutTimer = setTimeout(() => {
        controller.abort();
        const yieldResponse = this.yieldToOperator({
          sessionId,
          taskId,
          reason: `TIMEOUT: Worker exceeded thread allocation limit (${this.timeoutMs}ms)`,
          correlationId
        });
        resolve(yieldResponse);
      }, this.timeoutMs);
    });

    // 2. Worker Core Execution Promise
    const executionPromise = (async () => {
      try {
        let result;
        if (this.taskHandler) {
          result = await this.taskHandler(taskPayload, controller.signal);
        } else {
          // Default deterministic mock executor for testing
          result = {
            executedBy: this.agentId,
            specialty: this.specialty,
            output: `Executed ${taskPayload.action || 'subtask'} successfully`,
            data: taskPayload.data || {}
          };
        }

        clearTimeout(timeoutTimer);

        // Record successful micro-step transaction to WAL immediately
        const execTaskId = `exec_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`;
        const tx = this.walStore.appendTransaction({
          taskId: execTaskId,
          sessionId,
          senderAgentId: this.agentId,
          recipientAgentId: 'STRATEGIST',
          payload: { action: 'EXECUTE_SUBTASK', input: taskPayload, result },
          tokensConsumed: taskPayload.tokensConsumed || 15,
          committed: true
        });

        this.walStore.updateAgentStatus(this.agentId, AgentStatus.IDLE, null);

        return {
          status: 'SUCCESS',
          agentId: this.agentId,
          taskId: tx.task_id,
          txId: tx.task_id,
          result
        };
      } catch (err) {
        clearTimeout(timeoutTimer);
        this.walStore.updateAgentStatus(this.agentId, AgentStatus.IDLE, null);
        return {
          status: 'ERROR',
          agentId: this.agentId,
          taskId,
          error: err.message
        };
      }
    })();

    // Promise race ensures operator yield is triggered immediately on timeout
    return await Promise.race([executionPromise, timeoutPromise]);
  }

  /**
   * Yield control back to the operator
   * @param {Object} params
   */
  yieldToOperator({ sessionId, taskId, reason, correlationId }) {
    this.walStore.updateAgentStatus(this.agentId, AgentStatus.IDLE, null);

    // Record yield event in WAL log
    const tx = this.walStore.appendTransaction({
      taskId: `yield_${Date.now()}`,
      sessionId,
      senderAgentId: this.agentId,
      recipientAgentId: 'OPERATOR',
      payload: { action: 'YIELD_OPERATOR', taskId, reason, yieldedAt: Date.now() },
      committed: true
    });

    return {
      status: 'YIELDED_TO_OPERATOR',
      agentId: this.agentId,
      taskId,
      txId: tx.task_id,
      reason,
      correlationId
    };
  }
}
