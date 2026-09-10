/**
 * Automated Verification: Memory & SQLite-WAL Architecture (Phase A)
 * Sovereign Protocol [DIRECTIVE-01]
 */

const assert = require('node:assert/strict');
const WalStore = require('../wal_store');

console.log('>>> [PHASE A] Running SQLite-WAL Substrate Verification...');

const wal = new WalStore(':memory:');

// 1. Verify Session Initialization
const session = wal.initializeSession('sess_sovereign_001', 75000);
assert.equal(session.session_id, 'sess_sovereign_001');
assert.equal(session.global_status, 'AWAITING_WORKLOAD');
assert.equal(session.token_burned, 0);
assert.equal(session.hard_cap, 75000);
console.log('  [PASS] initializeSession() created boundary record with hard cap.');

// 2. Verify Agent Registration & Foreign Key Constraints
wal.registerAgent('strategist-prime', 'STRATEGIST', 'IDLE');
wal.registerAgent('worker-alpha', 'WORKER', 'IDLE');

const agent = wal.getAgent('worker-alpha');
assert.equal(agent.agent_id, 'worker-alpha');
assert.equal(agent.role, 'WORKER');
assert.equal(agent.status, 'IDLE');
console.log('  [PASS] agent_nodes table populated prior to micro-step transactions.');

// 2b. Test Foreign Key Enforcement on invalid sender
assert.throws(
  () => {
    wal.commitMicroStep(
      'task_fk_fail',
      'sess_sovereign_001',
      'non_existent_agent_999', // Invalid sender -> should violate FK
      { action: 'unauthorized_emission' }
    );
  },
  /constraint failed|FOREIGN KEY/i
);
console.log('  [PASS] PRAGMA foreign_keys = ON strictly enforced on invalid sender_agent_id.');

// 3. Verify commitMicroStep()
const step1 = wal.commitMicroStep(
  'step_001',
  'sess_sovereign_001',
  'strategist-prime',
  'worker-alpha',
  { directive: 'Ingest architectural blueprint', target: 'worker-alpha' },
  45,
  0.05,
  'audit_sig_sha256_genesis'
);

assert.equal(step1.task_id, 'step_001');
assert.equal(step1.sender_agent_id, 'strategist-prime');
assert.equal(step1.recipient_agent_id, 'worker-alpha');
assert.equal(step1.tokens_consumed, 45);
assert.equal(step1.entropy_score, 0.05);
assert.equal(step1.committed, 1);

const step2 = wal.commitMicroStep(
  'step_002',
  'sess_sovereign_001',
  'worker-alpha',
  'strategist-prime',
  { code_emission: 'const wal = new WalStore();', status: 'COMPLETE' },
  120,
  0.11,
  'audit_sig_sha256_step2'
);

assert.equal(step2.task_id, 'step_002');
assert.equal(step2.committed, 1);
console.log('  [PASS] commitMicroStep() successfully appended atomic transactions to WAL.');

// 4. Verify rollbackStep()
const badStep = wal.commitMicroStep(
  'step_003_bad',
  'sess_sovereign_001',
  'worker-alpha',
  { error: 'Infinite loop detected' },
  30,
  0.94,
  null
);
assert.equal(badStep.committed, 1);

const rolledBack = wal.rollbackStep('step_003_bad');
assert.equal(rolledBack, true);

// Verify data is NOT physically destroyed in the database, only marked committed = 0
const rawStmt = wal.db.prepare('SELECT committed FROM transaction_log WHERE task_id = ?');
const rawRow = rawStmt.get('step_003_bad');
assert.equal(rawRow.committed, 0);
console.log('  [PASS] rollbackStep() switched committed binary flag to 0 preserving immutable audit log.');

// 5. Verify reconstituteState()
const state = wal.reconstituteState('sess_sovereign_001');
assert.equal(state.sessionId, 'sess_sovereign_001');
assert.equal(state.globalStatus, 'AWAITING_WORKLOAD');
assert.equal(state.stepCount, 2);
assert.equal(state[0].taskId, 'step_001');
assert.equal(state[1].taskId, 'step_002');
assert.equal(state[1].validationHash, 'audit_sig_sha256_step2');
console.log('  [PASS] reconstituteState() rebuilt sequential memory array containing only committed steps.');

wal.close();
console.log('>>> [PHASE A] ALL SUBSTRATE & CONSTRAINT TESTS PASSED CLEANLY.\n');
