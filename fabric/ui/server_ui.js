/**
 * Antigravity Gemini Fabric (V3.8-Flash) - Cockpit HTTP Bridge Server
 * Context: Sovereign Protocol [DIRECTIVE-01]
 * Implementation Target: c:/SarembokVE/fabric/ui/server_ui.js
 * 
 * Zero-dependency native Node.js HTTP server.
 * Serves the developer cockpit (index.html) and pipes live SQLite-WAL telemetry.
 */

const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const { createHmac, randomBytes } = require('node:crypto');
const WalStore = require('../wal_store');

const PORT = process.env.COCKPIT_PORT || 3800;
const DB_PATH = path.join(__dirname, '..', 'fabric_cockpit.db');

// Initialize WAL store instance
const wal = new WalStore(DB_PATH);
const DEFAULT_SESSION_ID = 'sess_gemini_38_flash_cockpit';
const HARD_CAP = 100000;

// Ensure default session exists
let session = wal.getSession(DEFAULT_SESSION_ID);
if (!session) {
  session = wal.initializeSession(DEFAULT_SESSION_ID, HARD_CAP);
}

// Ensure sovereign agents exist
wal.registerAgent('STRATEGIST', 'STRATEGIST', 'IDLE');
wal.registerAgent('WORKER', 'WORKER', 'IDLE');
wal.registerAgent('AUDITOR', 'AUDITOR', 'IDLE');

// Helper to generate HMAC signature
function generateAuditSignature(payload, salt = 'SOVEREIGN_KEY_01') {
  return '0x' + createHmac('sha256', salt).update(typeof payload === 'string' ? payload : JSON.stringify(payload)).digest('hex').substring(0, 16);
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

  // 1. Serve Dashboard HTML
  if (url.pathname === '/' || url.pathname === '/index.html') {
    const htmlPath = path.join(__dirname, 'index.html');
    fs.readFile(htmlPath, 'utf8', (err, content) => {
      if (err) {
        res.writeHead(500, { 'Content-Type': 'text/plain; charset=utf-8' });
        res.end('Error loading dashboard: ' + err.message);
        return;
      }
      res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
      res.end(content);
    });
    return;
  }

  // 2. API Endpoint: /api/telemetry
  if (url.pathname === '/api/telemetry' && req.method === 'GET') {
    try {
      const currentSession = wal.getSession(DEFAULT_SESSION_ID);
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
          sessionId: tx.session_id,
          senderAgentId: tx.sender_agent_id,
          recipientAgentId: tx.recipient_agent_id,
          payload: parsed,
          tokensConsumed: tx.tokens_consumed,
          entropyScore: tx.entropy_score,
          validationHash: tx.validation_hash,
          committed: tx.committed,
          createdAt: tx.created_at
        };
      });

      let reconstitutedState = [];
      try {
        reconstitutedState = wal.reconstituteState(DEFAULT_SESSION_ID);
      } catch (e) {
        reconstitutedState = { error: e.message };
      }

      const responsePayload = {
        session: currentSession,
        agents: allAgents,
        transactions: transactions,
        reconstitutedState: Array.isArray(reconstitutedState) ? reconstitutedState : []
      };

      res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify(responsePayload));
    } catch (err) {
      res.writeHead(500, { 'Content-Type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ error: err.message }));
    }
    return;
  }

  // 3. API Endpoint: /api/step (Run live micro-step)
  if (url.pathname === '/api/step' && req.method === 'POST') {
    let body = '';
    req.on('data', chunk => { body += chunk; });
    req.on('end', () => {
      try {
        const data = body ? JSON.parse(body) : {};
        const directive = data.directive || 'Edge micro-step telemetry sync';

        // Check hard cap
        const sess = wal.getSession(DEFAULT_SESSION_ID);
        if (sess && sess.token_burned >= sess.hard_cap) {
          wal.updateSessionStatus(DEFAULT_SESSION_ID, 'HALTED');
          res.writeHead(400, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ error: 'HARD_CAP_REACHED', status: 'HALTED' }));
          return;
        }

        // Set status to RUNNING
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
              const tokens = Math.floor(Math.random() * 250) + 220;
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
              res.end(JSON.stringify({ success: true, stepId, tokens, validationHash }));
            }, 120);
          }, 150);
        }, 120);

      } catch (err) {
        res.writeHead(500, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: err.message }));
      }
    });
    return;
  }

  // 4. API Endpoint: /api/simulate-loop (Spike entropy, trigger rollback & FROZEN state)
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

      // Mark agent FROZEN
      wal.updateAgentStatus('WORKER', 'FROZEN', stepId);
      wal.updateSessionStatus(DEFAULT_SESSION_ID, 'RUNNING');

      // Commit rollback row with committed = 0
      wal.commitMicroStep(
        stepId,
        DEFAULT_SESSION_ID,
        'WORKER',
        'AUDITOR',
        loopPayload,
        50,
        0.94,
        validationHash,
        0 // Soft rollback!
      );

      setTimeout(() => {
        wal.updateSessionStatus(DEFAULT_SESSION_ID, 'AWAITING_WORKLOAD');
      }, 500);

      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ success: true, stepId, status: 'INTERCEPTED', committed: 0, entropy: 0.94 }));
    } catch (err) {
      res.writeHead(500, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: err.message }));
    }
    return;
  }

  // 5. API Endpoint: /api/reset
  if (url.pathname === '/api/reset' && req.method === 'POST') {
    try {
      wal.initializeSession(DEFAULT_SESSION_ID, HARD_CAP);
      wal.updateAgentStatus('STRATEGIST', 'IDLE');
      wal.updateAgentStatus('WORKER', 'IDLE');
      wal.updateAgentStatus('AUDITOR', 'IDLE');

      // Clean transaction log for this session
      wal.db.prepare('DELETE FROM transaction_log WHERE session_id = ?').run(DEFAULT_SESSION_ID);

      const initPayload = { directive: 'RESET_INITIALIZED', target: 'CLEAN_SLATE' };
      wal.commitMicroStep('step_init_001', DEFAULT_SESSION_ID, 'STRATEGIST', 'WORKER', initPayload, 120, 0.11, generateAuditSignature(initPayload), 1);

      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ success: true, message: 'Session reset to clean state' }));
    } catch (err) {
      res.writeHead(500, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: err.message }));
    }
    return;
  }

  // 404 Catch-all
  res.writeHead(404, { 'Content-Type': 'text/plain' });
  res.end('Not Found');
});

server.listen(PORT, () => {
  console.log(`[ANTIGRAVITY COCKPIT] Server listening at http://localhost:${PORT}`);
  console.log(`[ANTIGRAVITY COCKPIT] Connected to WAL Substrate at: ${DB_PATH}`);
});

module.exports = server;
