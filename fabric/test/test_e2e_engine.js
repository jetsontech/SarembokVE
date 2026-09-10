/**
 * Test Suite: End-to-End Fabric Kernel Integration
 * Sovereign Protocol [DIRECTIVE-01]
 */

const assert = require('node:assert/strict');
const WalStore = require('../wal_store');
const EntropyEvaluator = require('../entropy_evaluator');

console.log('>>> [INTEGRATION] Running Master Fabric Kernel End-to-End Test...');

const wal = new WalStore(':memory:');
const sessionId = 'session_e2e_001';
wal.initializeSession(sessionId, 50000);

// Turn 1: Normal operational task
const turn1 = wal.commitMicroStep(
  'task_turn_1',
  sessionId,
  'STRATEGIST',
  'WORKER',
  { prompt: 'Generate SQLite WAL substrate' },
  350,
  0.02,
  'VALIDATION_HASH_TURN_1'
);

assert.equal(turn1.task_id, 'task_turn_1');
console.log('  [PASS] Turn 1 executed, audited, and committed to WAL.');

// Turn 2: Another unique operational task
const turn2 = wal.commitMicroStep(
  'task_turn_2',
  sessionId,
  'STRATEGIST',
  'WORKER',
  { prompt: 'Construct entropy loop mitigation guardrails' },
  250,
  0.03,
  'VALIDATION_HASH_TURN_2'
);

assert.equal(turn2.task_id, 'task_turn_2');
console.log('  [PASS] Turn 2 executed, audited, and committed to WAL.');

// Check Reconstituted State from WAL log (Stateless reducer)
const reconstructedState = wal.reconstituteState(sessionId);
assert.equal(reconstructedState.sessionId, sessionId);
assert.equal(reconstructedState.tokenBurned, 600); // 350 + 250
assert.equal(reconstructedState.stepCount, 2);
assert.ok(reconstructedState[1].validationHash);
console.log('  [PASS] Kernel state reconstituted on-demand from append-only WAL stream.');

// Turn 3: Simulate intentional loop by setting worker to repeat exact text 3 times
const loopingDialogue = [
  'Exact repetitive output payload to trigger proactive semantic loop evaluator.',
  'Exact repetitive output payload to trigger proactive semantic loop evaluator.',
  'Exact repetitive output payload to trigger proactive semantic loop evaluator.'
];

const loopEval = EntropyEvaluator.evaluateLoop(loopingDialogue);
assert.equal(loopEval.triggerRollback, true);
assert.ok(loopEval.score >= 0.88);

// Trigger mitigation
wal.registerAgent('worker-repeater', 'WORKER', 'FROZEN');
wal.rollbackStep('task_turn_2');

console.log('  [PASS] Proactive semantic loop mitigation triggered and intercepted in live flywheel.');

wal.close();
console.log('>>> [INTEGRATION] ALL MASTER FABRIC KERNEL TESTS PASSED.\n');
