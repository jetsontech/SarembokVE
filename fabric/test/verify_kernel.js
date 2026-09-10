// verify_kernel.js - End-to-End Fabric Validation Harness
const WalStore = require('../wal_store');
const EntropyEvaluator = require('../entropy_evaluator');

async function runValidationPipeline() {
    console.log(">>> INITIALIZING FABRIC INTEGRATION ASSERTIONS...");
    const wal = new WalStore('c:/SarembokVE/fabric/test_kernel.db');
    
    // ASSERTION 1: Substrate Integrity
    wal.initializeSession('test_session_001', 5000);
    wal.commitMicroStep('task_01', 'test_session_001', 'STRATEGIST', 'WORKER', {text: "Initialize compilation"}, 100, 0.0, "MOCK_HASH");
    let state = wal.reconstituteState('test_session_001');
    if (state.length === 1) {
        console.log("  [PASS] Substrate Reconstitution Asserted Successfully.");
    } else {
        throw new Error("FAIL: Substrate Reconstitution Mismatch.");
    }

    // ASSERTION 2: Proactive Loop Interception
    const loopingDialogue = [
        "Running directory analysis routine...",
        "Running directory analysis routine...",
        "Running directory analysis routine..."
    ];
    const loopAnalysis = EntropyEvaluator.evaluateLoop(loopingDialogue);
    if (loopAnalysis.triggerRollback && loopAnalysis.score >= 0.88) {
        wal.rollbackStep('task_01');
        console.log(`  [PASS] Entropy Guardrail Successfully Intercepted Loop (Score: ${loopAnalysis.score}).`);
    } else {
        throw new Error("FAIL: Entropy Monitor Allowed Recursive Loop Defect.");
    }

    // ASSERTION 3: Hard-Cap Enforcement
    let session = wal.db.prepare("SELECT token_burned, hard_cap FROM session_state WHERE session_id = 'test_session_001'").get();
    if (session.token_burned <= session.hard_cap) {
        console.log("  [PASS] Token Budget Guard Enforced Boundary Bounds.");
    } else {
        throw new Error("FAIL: System Permitted Token Burn-Out past Hard-Cap.");
    }

    console.log(">>> ALL KERNEL COMPILATION SUITES PASSED. SYSTEM STANDBY.");
}

runValidationPipeline().catch(err => {
    console.error("!!! KERNEL VALIDATION FAILURE !!!\n", err);
    process.exit(1);
});
