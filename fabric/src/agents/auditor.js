/**
 * Antigravity Gemini Fabric - Auditor Node & Structural Isolation Guard
 * Sovereign Protocol [DIRECTIVE-01]
 * 
 * Deterministically verifies Worker output against Strategist boundary parameters.
 * Produces cryptographic validation signatures (SHA-256 HMAC).
 * Enforces structural isolation: blocks unauthorized scripts or environment mutations
 * without valid Auditor signatures.
 */

import { createHmac } from 'node:crypto';
import { AgentRole, AgentStatus, MessageType } from './types.js';

export class AuditorNode {
  /**
   * @param {Object} config
   * @param {string} config.agentId
   * @param {import('../memory/wal_store.js').WalStore} config.walStore
   * @param {import('./bus.js').MessageBus} config.bus
   * @param {string} [config.auditSecret='SOVEREIGN_AUDIT_SECRET_DIRECTIVE_01']
   */
  constructor({
    agentId = 'auditor-primary',
    walStore,
    bus,
    auditSecret = 'SOVEREIGN_AUDIT_SECRET_DIRECTIVE_01'
  }) {
    this.agentId = agentId;
    this.walStore = walStore;
    this.bus = bus;
    this.auditSecret = auditSecret;

    // Register node in WAL
    this.walStore.registerAgent(this.agentId, AgentRole.AUDITOR, AgentStatus.IDLE);

    // Register on bus
    this.bus.registerHandler(this.agentId, this.handleIncomingMessage.bind(this));
  }

  /**
   * Handle incoming protocol message
   * @param {Object} msg
   */
  async handleIncomingMessage(msg) {
    if (msg.type === MessageType.AUDIT_REQUEST) {
      return await this.auditTaskExecution(msg.sessionId, msg.payload);
    }
    throw new Error(`[AuditorNode ${this.agentId}] Unsupported message type: ${msg.type}`);
  }

  /**
   * Deterministically evaluate worker result against boundary parameters
   * @param {string} sessionId
   * @param {Object} params
   * @param {string} params.workerId
   * @param {Object} params.workerOutput
   * @param {Object} params.boundaryParameters
   */
  async auditTaskExecution(sessionId, { workerId, workerOutput, boundaryParameters }) {
    this.walStore.updateAgentStatus(this.agentId, AgentStatus.BUSY, null);

    const violations = [];

    // 1. Constraint: Disallow dangerous patterns / external script invocation
    const outputString = typeof workerOutput === 'string' ? workerOutput : JSON.stringify(workerOutput);
    const dangerousPatterns = [
      /eval\s*\(/i,
      /Function\s*\(/i,
      /<script[\s>]/i,
      /rm\s+-rf/i,
      /drop\s+table/i
    ];

    for (const pattern of dangerousPatterns) {
      if (pattern.test(outputString)) {
        violations.push(`Violation: Disallowed pattern detected [${pattern.toString()}]`);
      }
    }

    // 2. Constraint: Check boundary parameters (e.g. maxOutputSize, requiredFields)
    if (boundaryParameters) {
      if (boundaryParameters.maxChars && outputString.length > boundaryParameters.maxChars) {
        violations.push(`Violation: Output length (${outputString.length}) exceeds boundary (${boundaryParameters.maxChars})`);
      }

      if (boundaryParameters.requiredFields && typeof workerOutput === 'object' && workerOutput !== null) {
        for (const req of boundaryParameters.requiredFields) {
          if (workerOutput[req] === undefined) {
            violations.push(`Violation: Missing required boundary field '${req}'`);
          }
        }
      }
    }

    const passed = violations.length === 0;
    let validationHash = null;

    if (passed) {
      // Deterministic cryptographic validation hash (HMAC-SHA256)
      const hmac = createHmac('sha256', this.auditSecret);
      hmac.update(sessionId);
      hmac.update(workerId);
      hmac.update(outputString);
      hmac.update(JSON.stringify(boundaryParameters || {}));
      validationHash = hmac.digest('hex');
    }

    const auditVerdict = {
      passed,
      violations,
      validationHash,
      auditedAt: Date.now(),
      auditorId: this.agentId
    };

    // Log transaction to WAL
    this.walStore.appendTransaction({
      taskId: `audit_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`,
      sessionId,
      senderAgentId: this.agentId,
      recipientAgentId: workerId,
      payload: { workerId, boundaryParameters, auditVerdict },
      validationHash: auditVerdict.validationHash,
      tokensConsumed: 5,
      committed: true
    });

    this.walStore.updateAgentStatus(this.agentId, AgentStatus.IDLE, null);

    return auditVerdict;
  }

  /**
   * Structural Isolation Guard:
   * Asserts whether an environment mutation or external script has valid Auditor verification signature
   * @param {string} sessionId
   * @param {string} workerId
   * @param {any} output
   * @param {Object} boundaryParameters
   * @param {string} validationHash
   */
  assertVerificationSignature(sessionId, workerId, output, boundaryParameters, validationHash) {
    if (!validationHash) {
      throw new Error('[StructuralIsolationGuard] Access Denied: Missing Auditor verification signature.');
    }

    const outputString = typeof output === 'string' ? output : JSON.stringify(output);
    const hmac = createHmac('sha256', this.auditSecret);
    hmac.update(sessionId);
    hmac.update(workerId);
    hmac.update(outputString);
    hmac.update(JSON.stringify(boundaryParameters || {}));
    const expectedHash = hmac.digest('hex');

    if (expectedHash !== validationHash) {
      throw new Error('[StructuralIsolationGuard] Access Denied: Invalid or forged Auditor verification signature.');
    }

    return true;
  }
}
