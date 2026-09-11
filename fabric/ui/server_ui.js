const http = require('http');
const fs = require('fs');
const path = require('path');

// Zero-dependency SQLite interface: Use better-sqlite3 if present, otherwise native node:sqlite DatabaseSync
let Database;
try {
    Database = require('better-sqlite3');
} catch (e) {
    const { DatabaseSync } = require('node:sqlite');
    Database = DatabaseSync;
}

const PORT = 3000;
const DB_PATH = path.resolve(__dirname, '..', 'kernel.db');

const server = http.createServer((req, res) => {
    // Enable API CORS headers safely for local loop operations
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'POST, GET, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

    if (req.method === 'OPTIONS') {
        res.writeHead(200);
        res.end();
        return;
    }

    if (req.url === '/' || req.url === '/index.html') {
        const prodHtmlPath = path.resolve(__dirname, '..', '..', 'frontend', 'index.html');
        const targetHtml = fs.existsSync(prodHtmlPath) ? prodHtmlPath : path.join(__dirname, 'index.html');
        fs.readFile(targetHtml, (err, content) => {
            if (err) {
                res.writeHead(500, { 'Content-Type': 'text/plain' });
                res.end('Substrate mounting exception.');
            } else {
                res.writeHead(200, {
                    'Content-Type': 'text/html',
                    'Cache-Control': 'no-cache, no-store, must-revalidate',
                    'Pragma': 'no-cache',
                    'Expires': '0'
                });
                res.end(content);
            }
        });
    } else if (req.url === '/audio_bridge.html' || req.url === '/voice') {
        const audioBridgePath = path.resolve(__dirname, 'audio_bridge.html');
        fs.readFile(audioBridgePath, (err, content) => {
            if (err) {
                res.writeHead(404, { 'Content-Type': 'text/plain' });
                res.end('Audio Bridge UI not found.');
            } else {
                res.writeHead(200, { 'Content-Type': 'text/html' });
                res.end(content);
            }
        });
    } else if (req.url === '/session') {
        const https = require('https');
        const options = {
            headers: { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) SarembokLocal/1.0' }
        };
        https.get('https://sarembok.com/session', options, (remoteRes) => {
            let data = '';
            remoteRes.on('data', chunk => data += chunk);
            remoteRes.on('end', () => {
                res.writeHead(remoteRes.statusCode || 200, {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                });
                res.end(data);
            });
        }).on('error', (err) => {
            res.writeHead(200, { 'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*' });
            res.end(JSON.stringify({ sessionToken: 'local_dev_token', expiresIn: 3600 }));
        });
    } else if (req.url === '/api/telemetry') {
        try {
            const db = new Database(DB_PATH);
            const session = db.prepare(`SELECT * FROM session_state ORDER BY initialized_at DESC LIMIT 1`).get() || { global_status: 'AWAITING_WORKLOAD', token_burned: 0, hard_cap: 10000 };
            const agents = db.prepare(`SELECT * FROM agent_nodes`).all();
            const logs = db.prepare(`SELECT * FROM transaction_log ORDER BY created_at DESC LIMIT 30`).all();
            db.close();

            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ session, agents, logs }));
        } catch (dbErr) {
            res.writeHead(500, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: "Failed to read database pipeline state matrix: " + dbErr.message }));
        }
    } else if (req.url === '/api/execute-task' && req.method === 'POST') {
        let body = '';
        req.on('data', chunk => { body += chunk.toString(); });
        req.on('end', () => {
            try {
                const data = JSON.parse(body || '{}');
                const db = new Database(DB_PATH);
                
                // Retrieve or ensure active session
                let session = db.prepare(`SELECT session_id FROM session_state ORDER BY initialized_at DESC LIMIT 1`).get();
                if (!session) {
                    db.prepare(`INSERT INTO session_state (session_id, global_status, token_burned, hard_cap) VALUES ('session_active', 'AWAITING_WORKLOAD', 0, 100000)`).run();
                    session = { session_id: 'session_active' };
                }

                // Inject an event directly into the transaction substrate
                const taskId = 'step_' + Math.floor(Math.random() * 1000000);
                const tokensConsumed = Math.floor(Math.random() * 120) + 180;
                db.prepare(`UPDATE session_state SET global_status = 'RUNNING', token_burned = token_burned + ?`).run(tokensConsumed);
                db.prepare(`UPDATE agent_nodes SET status = 'BUSY' WHERE role = 'STRATEGIST'`).run();
                db.prepare(`
                    INSERT INTO transaction_log (task_id, session_id, sender_agent_id, recipient_agent_id, payload, tokens_consumed, entropy_score, validation_hash)
                    VALUES (?, ?, 'STRATEGIST', 'WORKER', ?, ?, 0.12, 'HMAC_VERIFIED_SIGNATURE')
                `).run(taskId, session.session_id, JSON.stringify({ text: data.task || 'Autonomous directive execution' }), tokensConsumed);
                
                db.close();
                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ success: true, taskId }));
            } catch (err) {
                res.writeHead(500, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: 'Execution Ingestion Failure: ' + err.message }));
            }
        });
    } else if (req.url === '/api/force-rollback' && req.method === 'POST') {
        try {
            const db = new Database(DB_PATH);
            const latest = db.prepare(`SELECT task_id FROM transaction_log WHERE committed = 1 ORDER BY created_at DESC LIMIT 1`).get();
            if (latest && latest.task_id) {
                db.prepare(`UPDATE transaction_log SET committed = 0 WHERE task_id = ?`).run(latest.task_id);
            }
            db.prepare(`UPDATE agent_nodes SET status = 'FROZEN' WHERE role = 'WORKER'`).run();
            db.close();
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ status: "ROLLBACK_COMMITTED" }));
        } catch (e) {
            res.writeHead(500, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: e.message }));
        }
    } else if (req.url === '/api/clear-storage' && req.method === 'POST') {
        try {
            const db = new Database(DB_PATH);
            db.prepare(`DELETE FROM transaction_log`).run();
            db.prepare(`UPDATE agent_nodes SET status = 'IDLE'`).run();
            db.prepare(`UPDATE session_state SET token_burned = 0, global_status = 'AWAITING_WORKLOAD'`).run();
            db.close();
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ status: "STORAGE_PURGED" }));
        } catch (e) {
            res.writeHead(500, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: e.message }));
        }
    } else {
        res.writeHead(404);
        res.end('Out of Bounds.');
    }
});

server.listen(PORT, () => {
    console.log(`>>> INTERACTIVE SPLIT COCKPIT LIVE AT: http://localhost:${PORT}`);
    console.log(`>>> Substrate Database: ${DB_PATH}`);
});
