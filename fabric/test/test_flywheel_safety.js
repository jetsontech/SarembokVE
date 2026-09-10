/**
 * Test Suite: Defensive Safety, Token Budget, Worker Timeout & Auditor Signatures (Phase C)
 * Sovereign Protocol [DIRECTIVE-01]
 */

const assert = require('node:assert/strict');
const WalStore = require('../wal_store');
const { createHmac } = require('node:crypto');

console.log('>>> [PHASE C] Running Defensive Safety & Flywheel Tests...');

const wal = new WalStore(':memory:');

// 1. Test Strict Token Budget Hard Cap & Safe Halt
wal.initializeSession('sess_safety_test', 1000);
wal.registerAgent('worker-1', 'WORKER', 'IDLE');

// Burn 600 tokens -> OK
wal.burnTokens('sess_safety_test', 600);
let sess = wal.getSession('sess_safety_test');
assert.equal(sess.token_burned, 600);
console.log('  [PASS] Token budget tracking within allowed limit.');

// Simulate Token Cap Exceeded Guard
function checkTokenBudget(sessionId, additionalTokens) {
  const session = wal.getSession(sessionId);
  if (session.token_burned + additionalTokens >= session.hard_cap) {
    wal.updateSessionStatus(sessionId, 'HALTED');
    const agents = wal.listAgents();
    for (const ag of agents) {
      wal.updateAgentStatus(ag.agent_id, 'HALTED', null);
    }
    throw new Error(`Token hard cap exceeded for session '${sessionId}'`);
  }
  wal.burnTokens(sessionId, additionalTokens);
}

assert.throws(
  () => checkTokenBudget('sess_safety_test', 500),
  /Token hard cap exceeded/
);

const sessionAfterHalt = wal.getSession('sess_safety_test');
assert.equal(sessionAfterHalt.global_status, 'HALTED');

const agentAfterHalt = wal.getAgent('worker-1');
assert.equal(agentAfterHalt.status, 'HALTED');
console.log('  [PASS] Token cap breach triggered safe halt across session and agent nodes.');

// 2. Test Worker Timeout & Yield to Operator
async function executeWorkerTaskWithTimeout(taskId, timeoutMs, workFn) {
  let timeoutId;
  const timeoutPromise = new Promise((resolve) => {
    timeoutId = setTimeout(() => {
      resolve({
        status: 'YIELDED_TO_OPERATOR',
        reason: `TIMEOUT: Worker exceeded thread allocation limit (${timeoutMs}ms)`
      });
    }, timeoutMs);
  });

  const execPromise = (async () => {
    try {
      const res = await workFn();
      clearTimeout(timeoutId);
      return { status: 'SUCCESS', result: res };
    } catch (e) {
      clearTimeout(timeoutId);
      throw e;
    }
  })();

  return await Promise.race([execPromise, timeoutPromise]);
}

async function run() {
  const timeoutResult = await executeWorkerTaskWithTimeout('task_slow', 100, async () => {
    await new Promise(r => setTimeout(r, 400));
    return { done: true };
  });

  assert.equal(timeoutResult.status, 'YIELDED_TO_OPERATOR');
  assert.ok(timeoutResult.reason.includes('TIMEOUT'));
  console.log('  [PASS] Worker timeout gracefully yielded control back to operator.');

  // 3. Test Auditor Deterministic Boundary & Cryptographic Verification Signature
  const auditSecret = 'SOVEREIGN_AUDIT_SECRET_DIRECTIVE_01';

  function auditWorkerOutput(workerId, output, boundaryMaxChars = 200) {
    const outputStr = typeof output === 'string' ? output : JSON.stringify(output);
    const dangerousPatterns = [/eval\s*\(/i, /<script[\s>]/i];

    for (const pattern of dangerousPatterns) {
      if (pattern.test(outputStr)) {
        return { passed: false, validationHash: null, reason: 'Disallowed pattern detected' };
      }
    }

    if (outputStr.length > boundaryMaxChars) {
      return { passed: false, validationHash: null, reason: 'Boundary length exceeded' };
    }

    const hmac = createHmac('sha256', auditSecret);
    hmac.update(workerId);
    hmac.update(outputStr);
    const hash = hmac.digest('hex');

    return { passed: true, validationHash: hash };
  }

  // Valid Output
  const validAudit = auditWorkerOutput('worker-code-1', { status: 'COMPLETE', summary: 'Clean code generated' });
  assert.equal(validAudit.passed, true);
  assert.ok(validAudit.validationHash);
  console.log('  [PASS] Auditor produced cryptographic HMAC verification signature for valid output.');

  // Dangerous Output with eval
  const dangerousAudit = auditWorkerOutput('worker-bad', { code: 'eval("inject_payload()")' });
  assert.equal(dangerousAudit.passed, false);
  assert.equal(dangerousAudit.validationHash, null);
  console.log('  [PASS] Auditor intercepted dangerous script patterns and rejected verification.');

  wal.close();
  console.log('>>> [PHASE C] ALL DEFENSIVE & FLYWHEEL SAFETY TESTS PASSED SUCCESSFULLY.\n');
}

run().catch(err => {
  console.error('Test failure:', err);
  process.exit(1);
});
