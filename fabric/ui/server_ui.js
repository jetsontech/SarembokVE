/**
 * Antigravity Gemini Fabric (V3.8-Flash) - Abstracted API Streamer & Server
 * Context: Sovereign Protocol [DIRECTIVE-01]
 * Implementation Target: c:/SarembokVE/fabric/ui/server_ui.js
 * 
 * Native Node.js HTTP stream bridge serving the progressive split canvas
 * and piping real-time SQLite-WAL telemetry.
 */

const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const { createHmac } = require('node:crypto');
const WalStore = require('../wal_store');

const PORT = parseInt(process.env.PORT || '3000', 10);
const DB_PATH = path.join(__dirname, '..', 'kernel.db');

// Initialize WAL store using native node:sqlite (zero dependency)
const wal = new WalStore(DB_PATH);
const DEFAULT_SESSION_ID = 'sess_gemini_38_flash';
const HARD_CAP = 100000;

// Ensure default session exists
let session = wal.getSession(DEFAULT_SESSION_ID);
if (!session) {
  session = wal.initializeSession(DEFAULT_SESSION_ID, HARD_CAP);
}

// Ensure sovereign agents are registered
wal.registerAgent('STRATEGIST', 'STRATEGIST', 'IDLE');
wal.registerAgent('WORKER', 'WORKER', 'IDLE');
wal.registerAgent('AUDITOR', 'AUDITOR', 'IDLE');

function generateAuditSignature(payload, salt = 'SOVEREIGN_KEY_01') {
  return '0x' + createHmac('sha256', salt)
    .update(typeof payload === 'string' ? payload : JSON.stringify(payload))
    .digest('hex')
    .substring(0, 16);
}

// Seed initial transactions if empty
const existingTxs = wal.db.prepare('SELECT COUNT(*) as count FROM transaction_log WHERE session_id = ?').get(DEFAULT_SESSION_ID);
if (existingTxs.count === 0) {
  const initPayload = { directive: 'SOVEREIGN_BOOT_DIRECTIVE', target: 'EDGE_SANDBOX', mode: 'CONTINUOUS_LOOP' };
  wal.commitMicroStep('step_init_001', DEFAULT_SESSION_ID, 'STRATEGIST', 'WORKER', initPayload, 280, 0.12, generateAuditSignature(initPayload), 1);

  const workerPayload = { action: 'COMPILE_SUBTASKS', status: 'SUCCESS', latencyMs: 2.4 };
  wal.commitMicroStep('step_init_002', DEFAULT_SESSION_ID, 'WORKER', 'AUDITOR', workerPayload, 560, 0.14, generateAuditSignature(workerPayload), 1);

  const auditorPayload = { verification: 'HMAC_VALID', entropy: 0.13, hardCapCheck: 'PASS' };
  wal.commitMicroStep('step_init_003', DEFAULT_SESSION_ID, 'AUDITOR', 'STRATEGIST', auditorPayload, 190, 0.13, generateAuditSignature(auditorPayload), 1);
}

const server = http.createServer((req, res) => {
  // CORS Headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    res.writeHead(204);
    res.end();
    return;
  }

  const url = new URL(req.url, `http://${req.headers.host}`);

  // 1. Serve Progressive Split Canvas
  if (url.pathname === '/' || url.pathname === '/index.html') {
    const htmlPath = path.join(__dirname, 'index.html');
    fs.readFile(htmlPath, 'utf8', (err, content) => {
      if (err) {
        res.writeHead(500, { 'Content-Type': 'text/plain; charset=utf-8' });
        res.end('Resource mapping fault.');
        return;
      }
      res.writeHead(200, {
        'Content-Type': 'text/html; charset=utf-8',
        'Cache-Control': 'no-store, no-cache, must-revalidate, proxy-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0'
      });
      res.end(content);
    });
    return;
  }

  // 2. Telemetry Pipeline Endpoint: /api/telemetry
  if (url.pathname === '/api/telemetry' && req.method === 'GET') {
    try {
      const currentSession = wal.getSession(DEFAULT_SESSION_ID) || {
        session_id: DEFAULT_SESSION_ID,
        global_status: 'AWAITING_WORKLOAD',
        token_burned: 0,
        hard_cap: HARD_CAP
      };

      const allAgents = wal.listAgents().filter(a => ['STRATEGIST', 'WORKER', 'AUDITOR'].includes(a.agent_id));
      
      const txStmt = wal.db.prepare(`
        SELECT 
          task_id, session_id, sender_agent_id, recipient_agent_id,
          payload, tokens_consumed, entropy_score, validation_hash,
          committed, created_at
        FROM transaction_log
        WHERE session_id = ?
        ORDER BY rowid ASC
      `);

      const transactions = txStmt.all(DEFAULT_SESSION_ID).map(tx => {
        let parsed = tx.payload;
        try { parsed = JSON.parse(tx.payload); } catch {}
        return {
          taskId: tx.task_id,
          task_id: tx.task_id,
          sessionId: tx.session_id,
          senderAgentId: tx.sender_agent_id,
          sender_agent_id: tx.sender_agent_id,
          recipientAgentId: tx.recipient_agent_id,
          recipient_agent_id: tx.recipient_agent_id,
          payload: parsed,
          tokensConsumed: tx.tokens_consumed,
          tokens_consumed: tx.tokens_consumed,
          entropyScore: tx.entropy_score,
          entropy_score: tx.entropy_score,
          validationHash: tx.validation_hash,
          validation_hash: tx.validation_hash,
          committed: tx.committed,
          createdAt: tx.created_at
        };
      });

      let reconstitutedState = [];
      try {
        reconstitutedState = wal.reconstituteState(DEFAULT_SESSION_ID);
      } catch (e) {
        reconstitutedState = [];
      }

      res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({
        session: currentSession,
        agents: allAgents,
        logs: transactions,
        transactions: transactions,
        reconstitutedState: Array.isArray(reconstitutedState) ? reconstitutedState : []
      }));
    } catch (err) {
      res.writeHead(500, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ error: 'Failed to read database state matrix: ' + err.message }));
    }
    return;
  }

  // 3. Instruction Dispatch Endpoint: /api/step or /api/chat
  if ((url.pathname === '/api/step' || url.pathname === '/api/chat') && req.method === 'POST') {
    let body = '';
    req.on('data', chunk => { body += chunk; });
    req.on('end', () => {
      try {
        const data = body ? JSON.parse(body) : {};
        const directive = data.directive || data.message || 'Edge micro-step telemetry sync';

        const sess = wal.getSession(DEFAULT_SESSION_ID);
        if (sess && sess.token_burned >= sess.hard_cap) {
          wal.updateSessionStatus(DEFAULT_SESSION_ID, 'HALTED');
          res.writeHead(400, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ error: 'HARD_CAP_EXHAUSTED', status: 'HALTED' }));
          return;
        }

        // Cycle multi-agent states
        wal.updateSessionStatus(DEFAULT_SESSION_ID, 'RUNNING');
        wal.updateAgentStatus('STRATEGIST', 'BUSY', 'step_decompose');

        setTimeout(() => {
          wal.updateAgentStatus('STRATEGIST', 'IDLE');
          wal.updateAgentStatus('WORKER', 'BUSY', 'step_execute');

          setTimeout(() => {
            wal.updateAgentStatus('WORKER', 'IDLE');
            wal.updateAgentStatus('AUDITOR', 'BUSY', 'step_audit');

            setTimeout(() => {
              wal.updateAgentStatus('AUDITOR', 'IDLE');
              wal.updateSessionStatus(DEFAULT_SESSION_ID, 'AWAITING_WORKLOAD');

              const stepId = 'step_' + Date.now().toString().slice(-6);
              const tokens = Math.floor(Math.random() * 240) + 210;
              const entropy = Number((0.11 + Math.random() * 0.08).toFixed(2));
              const payload = {
                directive: directive,
                executionNode: 'WORKER',
                status: 'RESOLVED',
                timestamp: new Date().toISOString()
              };
              const validationHash = generateAuditSignature(payload);

              wal.commitMicroStep(
                stepId,
                DEFAULT_SESSION_ID,
                'WORKER',
                'AUDITOR',
                payload,
                tokens,
                entropy,
                validationHash,
                1
              );

              res.writeHead(200, { 'Content-Type': 'application/json' });
              res.end(JSON.stringify({ success: true, stepId, tokens, validationHash, directive }));
            }, 100);
          }, 120);
        }, 100);

      } catch (err) {
        res.writeHead(500, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: err.message }));
      }
    });
    return;
  }

  // 4. Simulate Recursive Loop Endpoint: /api/simulate-loop
  if (url.pathname === '/api/simulate-loop' && req.method === 'POST') {
    try {
      const stepId = 'loop_intercept_' + Date.now().toString().slice(-4);
      const loopPayload = {
        error: 'SEMANTIC_ENTROPY_WATCHDOG_INTERCEPT',
        detectedSimilarity: 0.94,
        safetyThreshold: 0.88,
        action: 'SOFT_ROLLBACK'
      };
      const validationHash = '0xREJECTED_LOOP';

      // Transition to FROZEN
      wal.updateAgentStatus('WORKER', 'FROZEN', stepId);
      wal.updateSessionStatus(DEFAULT_SESSION_ID, 'RUNNING');

      // Soft rollback transaction
      wal.commitMicroStep(
        stepId,
        DEFAULT_SESSION_ID,
        'WORKER',
        'AUDITOR',
        loopPayload,
        50,
        0.94,
        validationHash,
        0
      );

      setTimeout(() => {
        wal.updateSessionStatus(DEFAULT_SESSION_ID, 'AWAITING_WORKLOAD');
      }, 400);

      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ success: true, stepId, status: 'INTERCEPTED', committed: 0, entropy: 0.94 }));
    } catch (err) {
      res.writeHead(500, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: err.message }));
    }
    return;
  }

  // 5. Reset Session Endpoint: /api/reset
  if (url.pathname === '/api/reset' && req.method === 'POST') {
    try {
      wal.initializeSession(DEFAULT_SESSION_ID, HARD_CAP);
      wal.updateAgentStatus('STRATEGIST', 'IDLE');
      wal.updateAgentStatus('WORKER', 'IDLE');
      wal.updateAgentStatus('AUDITOR', 'IDLE');

      wal.db.prepare('DELETE FROM transaction_log WHERE session_id = ?').run(DEFAULT_SESSION_ID);

      const initPayload = { directive: 'RESET_INITIALIZED', target: 'CLEAN_SLATE' };
      wal.commitMicroStep('step_init_001', DEFAULT_SESSION_ID, 'STRATEGIST', 'WORKER', initPayload, 120, 0.11, generateAuditSignature(initPayload), 1);

      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ success: true, message: 'Session reset to clean slate' }));
    } catch (err) {
      res.writeHead(500, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: err.message }));
    }
    return;
  }

  res.writeHead(404, { 'Content-Type': 'text/plain' });
  res.end('Out of bounds.');
});

server.listen(PORT, () => {
  console.log(`>>> [ANTIGRAVITY FABRIC] CONSUMER WORKSPACE SERVING AT: http://localhost:${PORT}`);
  console.log(`>>> [ANTIGRAVITY FABRIC] Substrate Database: ${DB_PATH}`);
});

module.exports = server;
