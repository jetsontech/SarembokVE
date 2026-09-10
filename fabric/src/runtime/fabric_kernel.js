/**
 * Antigravity Gemini Fabric - Master Runtime Kernel
 * Sovereign Protocol [DIRECTIVE-01]
 * 
 * Unifies:
 * - Pillar 1: Anchorless SQLite-WAL memory substrate & state machine projector
 * - Pillar 2: Real-time sliding-window entropy evaluator & loop mitigation
 * - Pillar 3: Composable multi-agent flywheel (Strategist, Worker, Auditor)
 * - Defensive guardrails: Token budget hard-cap & structural isolation
 */

import { WalStore } from '../memory/wal_store.js';
import { StateMachineProjector } from '../memory/state_machine.js';
import { EntropyEvaluator } from '../guardrails/entropy_evaluator.js';
import { RollbackManager } from '../guardrails/rollback_manager.js';
import { TokenBudgetGuard, TokenCapExceededError } from '../guardrails/token_budget.js';
import { MessageBus } from '../agents/bus.js';
import { StrategistNode } from '../agents/strategist.js';
import { WorkerNode } from '../agents/worker.js';
import { AuditorNode } from '../agents/auditor.js';

export class FabricKernel {
  /**
   * @param {Object} [options]
   * @param {string} [options.dbPath=':memory:'] Path to SQLite WAL file or ':memory:'
   * @param {string} [options.auditSecret]
   * @param {number} [options.loopThreshold=0.88]
   * @param {number} [options.loopWindowSize=5]
   */
  constructor(options = {}) {
    this.dbPath = options.dbPath || ':memory:';
    this.auditSecret = options.auditSecret || 'SOVEREIGN_AUDIT_SECRET_DIRECTIVE_01';

    // 1. Core Memory Substrate
    this.walStore = new WalStore(this.dbPath);
    this.projector = new StateMachineProjector(this.walStore);

    // 2. Guardrails & Safety
    this.evaluator = new EntropyEvaluator({
      threshold: options.loopThreshold ?? 0.88,
      windowSize: options.loopWindowSize ?? 5,
      consecutiveTurns: 3
    });
    this.rollbackManager = new RollbackManager(this.walStore);
    this.tokenGuard = new TokenBudgetGuard(this.walStore);

    // 3. Messaging Bus
    this.bus = new MessageBus(this.walStore);

    // 4. Default Archetype Nodes
    this.strategist = new StrategistNode({
      walStore: this.walStore,
      bus: this.bus,
      rollbackManager: this.rollbackManager
    });

    this.workers = new Map();
    this.registerWorker('worker-code', 'code_emission');
    this.registerWorker('worker-scrape', 'log_scraping');
    this.registerWorker('worker-api', 'api_integration');

    this.auditor = new AuditorNode({
      walStore: this.walStore,
      bus: this.bus,
      auditSecret: this.auditSecret
    });
  }

  /**
   * Register a new worker node in the fabric
   * @param {string} workerId
   * @param {string} specialty
   * @param {number} [timeoutMs=5000]
   */
  registerWorker(workerId, specialty, timeoutMs = 5000) {
    const worker = new WorkerNode({
      agentId: workerId,
      specialty,
      walStore: this.walStore,
      bus: this.bus,
      timeoutMs
    });
    this.workers.set(workerId, worker);
    return worker;
  }

  /**
   * Initialize a new execution session
   * @param {string} sessionId
   * @param {number} [hardCap=100000]
   */
  initializeSession(sessionId, hardCap = 100000) {
    return this.walStore.createSession(sessionId, hardCap);
  }

  /**
   * Execute a full flywheel turn:
   * 1. Task parse by Strategist
   * 2. Delegation to Worker
   * 3. Proactive sliding-window loop detection
   * 4. Audit verification and signature generation
   * 5. Strict token budget deduction
   * 
   * @param {Object} params
   * @param {string} params.sessionId
   * @param {string} params.prompt
   * @param {string} [params.workerId='worker-code']
   * @param {number} [params.estimatedTokens=150]
   * @param {Object} [params.boundaryParameters]
   */
  async executeFlywheelTurn({
    sessionId,
    prompt,
    workerId = 'worker-code',
    estimatedTokens = 150,
    boundaryParameters = { maxChars: 50000 }
  }) {
    // Phase C: Strict token budget verification before dispatch
    this.tokenGuard.recordAndVerify(sessionId, estimatedTokens);

    const session = this.walStore.getSession(sessionId);
    if (session && session.global_status === 'AWAITING_WORKLOAD') {
      this.walStore.updateSessionStatus(sessionId, 'RUNNING');
    }

    // Phase B: Strategist decomposes task
    const taskPlan = this.strategist.decomposeTask(prompt);
    const subtask = {
      id: `task_${Date.now()}`,
      action: 'execute_primitive',
      prompt,
      plan: taskPlan
    };

    // Strategist delegates subtask to Worker
    const workerResult = await this.strategist.delegateToWorker({
      sessionId,
      workerId,
      subtask,
      boundaryParameters
    });

    if (workerResult.status === 'YIELDED_TO_OPERATOR') {
      return {
        status: 'YIELDED',
        reason: workerResult.reason,
        workerId,
        sessionId
      };
    }

    // Phase B / Pillar 2: Proactive Sliding-Window Semantic Loop Mitigation
    const recentTurns = this.walStore.getRecentTransactions(sessionId, 5, true, workerId);
    const loopEval = this.evaluator.evaluateTurns(recentTurns);

    if (loopEval.loopDetected) {
      // Trigger instant mitigation: Freeze thread, Rollback WAL tx, Inject directive
      const mitigation = this.rollbackManager.mitigateLoop({
        sessionId,
        agentId: loopEval.agentId || workerId,
        uncommittedTxId: workerResult.txId,
        reason: loopEval.reason
      });

      return {
        status: 'LOOP_INTERCEPTED',
        mitigation,
        evaluation: loopEval,
        sessionId
      };
    }

    // Phase C: Auditor Deterministic Verification
    const auditVerdict = await this.strategist.requestAudit({
      sessionId,
      auditorId: this.auditor.agentId,
      workerId,
      workerOutput: workerResult.result,
      boundaryParameters
    });

    // Enforce structural isolation
    this.auditor.assertVerificationSignature(
      sessionId,
      workerId,
      workerResult.result,
      boundaryParameters,
      auditVerdict.validationHash
    );

    return {
      status: 'SUCCESS',
      sessionId,
      workerResult,
      auditVerdict,
      snapshotHash: this.walStore.getLatestTransaction(sessionId)?.state_snapshot_hash
    };
  }

  /**
   * Reconstitute complete state from WAL on-demand
   * @param {string} sessionId
   */
  reconstituteState(sessionId) {
    return this.projector.reconstituteState(sessionId);
  }

  /**
   * Close kernel and storage
   */
  close() {
    this.walStore.close();
  }
}
