/**
 * Test Suite: Sliding-Window Semantic Loop Mitigation (Phase B & Pillar 2)
 * Sovereign Protocol [DIRECTIVE-01]
 */

const assert = require('node:assert/strict');
const EntropyEvaluator = require('../entropy_evaluator');
const WalStore = require('../wal_store');

console.log('>>> [PHASE B] Running Proactive Semantic Loop Mitigation Test...');

const evaluator = new EntropyEvaluator({
  windowSize: 5,
  consecutiveTurns: 3,
  threshold: 0.88
});

// 1. Test Dissimilar Dialogue Turns (Should Pass)
const normalTurns = [
  { sender_agent_id: 'worker-1', payload: 'Initializing database tables and schema.' },
  { sender_agent_id: 'worker-1', payload: 'Constructing message bus routing logic.' },
  { sender_agent_id: 'worker-1', payload: 'Evaluating security parameters for auditor.' }
];

const normalResult = evaluator.evaluateTurns(normalTurns);
assert.equal(normalResult.loopDetected, false);
console.log('  [PASS] Normal heterogeneous dialogue turns passed without false positives.');

// 2. Test Repetitive Semantic Loop (> 0.88 across 3 turns)
const repetitiveTurns = [
  { sender_agent_id: 'worker-loop', payload: 'Please wait while I process the request for the system configuration.' },
  { sender_agent_id: 'worker-loop', payload: 'Please wait while I process the request for system configuration settings.' },
  { sender_agent_id: 'worker-loop', payload: 'Please wait while I process the request for the system configuration settings now.' }
];

const loopResult = evaluator.evaluateTurns(repetitiveTurns);
assert.equal(loopResult.loopDetected, true);
assert.ok(loopResult.maxSimilarity >= 0.88);
assert.equal(loopResult.agentId, 'worker-loop');
console.log(`  [PASS] Semantic loop detected accurately (Similarity: ${loopResult.maxSimilarity} >= 0.88).`);

// 3. Test Static evaluateLoop method
const dialogueStrings = [
  "Running directory analysis routine...",
  "Running directory analysis routine...",
  "Running directory analysis routine..."
];
const staticResult = EntropyEvaluator.evaluateLoop(dialogueStrings);
assert.equal(staticResult.triggerRollback, true);
assert.ok(staticResult.score >= 0.88);
console.log(`  [PASS] Static evaluateLoop detected loop accurately (Score: ${staticResult.score}).`);

// 4. Test Rollback & Context Re-Routing Intervention
const wal = new WalStore(':memory:');
wal.initializeSession('sess_loop_test', 50000);
wal.registerAgent('worker-loop', 'WORKER', 'BUSY');
wal.registerAgent('strategist-1', 'STRATEGIST', 'IDLE');

// Write initial tx and looping tx to WAL
wal.commitMicroStep('loop_tx_1', 'sess_loop_test', 'worker-loop', null, repetitiveTurns[0].payload, 10, 0.0);
const badTx = wal.commitMicroStep('loop_tx_2', 'sess_loop_test', 'worker-loop', null, repetitiveTurns[2].payload, 10, 0.95);

// Freeze offending agent
wal.updateAgentStatus('worker-loop', 'FROZEN', null);
const rolledBack = wal.rollbackStep(badTx.task_id);
assert.equal(rolledBack, true);

// Verify 1: Agent thread is FROZEN
const agentStatus = wal.getAgent('worker-loop');
assert.equal(agentStatus.status, 'FROZEN');
console.log('  [PASS] Offending agent thread immediately FROZEN.');

// Verify 2: Uncommitted transaction rolled back in WAL
const committedTxs = wal.getAllCommittedTransactions('sess_loop_test');
assert.equal(committedTxs.length, 1);
console.log('  [PASS] Transaction rolled back in SQLite-WAL log.');

wal.close();
console.log('>>> [PHASE B] ALL LOOP MITIGATION TESTS PASSED SUCCESSFULLY.\n');
