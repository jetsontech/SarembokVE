/**
 * Antigravity Gemini Fabric - Protocol Schemas & Archetype Definitions
 * Sovereign Protocol [DIRECTIVE-01]
 */

export const AgentRole = Object.freeze({
  STRATEGIST: 'STRATEGIST',
  WORKER: 'WORKER',
  AUDITOR: 'AUDITOR'
});

export const AgentStatus = Object.freeze({
  IDLE: 'IDLE',
  BUSY: 'BUSY',
  FROZEN: 'FROZEN',
  HALTED: 'HALTED'
});

export const MessageType = Object.freeze({
  TASK_DELEGATION: 'TASK_DELEGATION',
  TASK_RESULT: 'TASK_RESULT',
  AUDIT_REQUEST: 'AUDIT_REQUEST',
  AUDIT_VERDICT: 'AUDIT_VERDICT',
  YIELD_OPERATOR: 'YIELD_OPERATOR',
  SAFE_HALT: 'SAFE_HALT'
});

/**
 * Validate a protocol message
 * @param {Object} msg
 */
export function validateProtocolMessage(msg) {
  const required = ['id', 'sessionId', 'from', 'to', 'type', 'payload', 'timestamp'];
  for (const field of required) {
    if (msg[field] === undefined || msg[field] === null) {
      throw new Error(`Invalid protocol message: missing required field '${field}'`);
    }
  }
  return true;
}
