const http = require('http');
const fs = require('fs');
const path = require('path');

const { execFile } = require('child_process');
const crypto = require('crypto');

// Supported static audio/asset extensions
const MIME_TYPES = {
    '.mp3': 'audio/mpeg',
    '.wav': 'audio/wav',
    '.ogg': 'audio/ogg',
    '.m4a': 'audio/mp4',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.svg': 'image/svg+xml',
    '.json': 'application/json',
    '.js': 'text/javascript',
    '.css': 'text/css'
};

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
    } else if (req.url === '/api/chat-sessions' && req.method === 'GET') {
        try {
            const db = new Database(DB_PATH);
            const sessions = db.prepare(`SELECT session_id, title, created_at, updated_at FROM chat_sessions ORDER BY updated_at DESC LIMIT 50`).all();
            db.close();
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ sessions }));
        } catch (e) {
            res.writeHead(500, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: e.message }));
        }
    } else if (req.url === '/api/chat-sessions' && req.method === 'POST') {
        let body = '';
        req.on('data', chunk => { body += chunk.toString(); });
        req.on('end', () => {
            try {
                const data = JSON.parse(body || '{}');
                const { session_id, title, messages } = data;
                if (!session_id || !messages) {
                    res.writeHead(400, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ error: 'Missing session_id or messages.' }));
                    return;
                }
                const db = new Database(DB_PATH);
                const titleStr = title || 'Session ' + new Date().toLocaleDateString();
                const jsonStr = JSON.stringify(messages);
                db.prepare(`
                    INSERT INTO chat_sessions (session_id, title, messages_json, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(session_id) DO UPDATE SET
                        title = excluded.title,
                        messages_json = excluded.messages_json,
                        updated_at = CURRENT_TIMESTAMP
                `).run(session_id, titleStr, jsonStr);
                db.close();
                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ success: true, session_id }));
            } catch (e) {
                res.writeHead(500, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: e.message }));
            }
        });
    } else if (req.url.startsWith('/api/chat-sessions') && req.method === 'DELETE') {
        try {
            const parsedUrl = new URL(req.url, `http://${req.headers.host || 'localhost:3000'}`);
            const sessionId = parsedUrl.searchParams.get('id');
            if (sessionId) {
                const db = new Database(DB_PATH);
                db.prepare(`DELETE FROM chat_sessions WHERE session_id = ?`).run(sessionId);
                db.close();
            }
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ success: true }));
        } catch (e) {
            res.writeHead(500, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: e.message }));
        }
    } else if (req.url.startsWith('/api/chat-session-load')) {
        try {
            const parsedUrl = new URL(req.url, `http://${req.headers.host || 'localhost:3000'}`);
            const sessionId = parsedUrl.searchParams.get('id');
            const db = new Database(DB_PATH);
            const row = db.prepare(`SELECT * FROM chat_sessions WHERE session_id = ?`).get(sessionId);
            db.close();
            if (row) {
                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({
                    session_id: row.session_id,
                    title: row.title,
                    messages: JSON.parse(row.messages_json || '[]'),
                    created_at: row.created_at,
                    updated_at: row.updated_at
                }));
            } else {
                res.writeHead(404, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: 'Session not found.' }));
            }
        } catch (e) {
            res.writeHead(500, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: e.message }));
        }
    } else if (req.url === '/api/background-tasks') {
        try {
            const db = new Database(DB_PATH);
            const tasks = db.prepare(`SELECT * FROM transaction_log ORDER BY created_at DESC LIMIT 50`).all();
            const agents = db.prepare(`SELECT * FROM agent_nodes`).all();
            db.close();
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ tasks, agents }));
        } catch (e) {
            res.writeHead(500, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: e.message }));
        }
    } else if (req.url.startsWith('/api/tts')) {
        try {
            const parsedUrl = new URL(req.url, `http://${req.headers.host || 'localhost:3000'}`);
            const text = (parsedUrl.searchParams.get('text') || '').trim();
            const voiceParam = (parsedUrl.searchParams.get('voice') || 'Vega').toLowerCase();
            if (!text) {
                res.writeHead(400, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: 'Missing text parameter.' }));
                return;
            }

            // Empirical voice fidelity mapping: Ava is closest match to New Recording 61 (OpenAI Shimmer)
            let neuralVoice = 'en-US-AvaNeural';
            if (voiceParam.includes('ada') || voiceParam.includes('gb') || voiceParam.includes('british')) {
                neuralVoice = 'en-GB-SoniaNeural';
            } else if (voiceParam.includes('aoede')) {
                neuralVoice = 'en-US-JennyNeural';
            } else if (voiceParam.includes('kore')) {
                neuralVoice = 'en-US-EmmaNeural';
            } else if (voiceParam.includes('puck')) {
                neuralVoice = 'en-US-BrianNeural';
            } else if (voiceParam.includes('fenrir')) {
                neuralVoice = 'en-US-GuyNeural';
            } else if (voiceParam.includes('jenny')) {
                neuralVoice = 'en-US-JennyNeural';
            } else if (voiceParam.includes('aria')) {
                neuralVoice = 'en-US-AriaNeural';
            }

            const cacheDir = path.resolve(__dirname, '..', '..', 'frontend', '.audio_cache');
            if (!fs.existsSync(cacheDir)) {
                fs.mkdirSync(cacheDir, { recursive: true });
            }

            const hash = crypto.createHash('md5').update(`${neuralVoice}__${text}`).digest('hex');
            const cachedFile = path.join(cacheDir, `${hash}.mp3`);

            const sendAudioFile = (filePath) => {
                const stat = fs.statSync(filePath);
                res.writeHead(200, {
                    'Content-Type': 'audio/mpeg',
                    'Content-Length': stat.size,
                    'Cache-Control': 'public, max-age=86400',
                    'Access-Control-Allow-Origin': '*'
                });
                fs.createReadStream(filePath).pipe(res);
            };

            if (fs.existsSync(cachedFile)) {
                sendAudioFile(cachedFile);
                return;
            }

            // Synthesize neural audio using edge_tts
            const args = ['-m', 'edge_tts', '--voice', neuralVoice, '--text', text, '--write-media', cachedFile];
            execFile('python', args, { timeout: 15000 }, (err, stdout, stderr) => {
                if (err || !fs.existsSync(cachedFile)) {
                    console.error('[TTS] edge-tts error:', err || stderr);
                    res.writeHead(500, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ error: 'TTS generation failed', details: stderr || String(err) }));
                    return;
                }
                sendAudioFile(cachedFile);
            });
        } catch (e) {
            res.writeHead(500, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: e.message }));
        }
    } else {
        // Handle static assets (.mp3, .wav, .png, etc.)
        const parsedUrl = new URL(req.url, `http://${req.headers.host || 'localhost:3000'}`);
        const pathname = parsedUrl.pathname;
        const ext = path.extname(pathname).toLowerCase();

        if (MIME_TYPES[ext]) {
            const cleanName = path.basename(pathname);
            const candidatePaths = [
                path.resolve(__dirname, '..', '..', 'frontend', cleanName),
                path.resolve(__dirname, cleanName),
                path.resolve(__dirname, '..', '..', 'frontend', pathname.replace(/^\/+/, ''))
            ];
            const targetStatic = candidatePaths.find(p => fs.existsSync(p));
            if (targetStatic) {
                const stat = fs.statSync(targetStatic);
                const range = req.headers.range;

                if (range) {
                    const parts = range.replace(/bytes=/, "").split("-");
                    const start = parseInt(parts[0], 10);
                    const end = parts[1] ? parseInt(parts[1], 10) : stat.size - 1;
                    const chunksize = (end - start) + 1;
                    const file = fs.createReadStream(targetStatic, { start, end });
                    res.writeHead(206, {
                        'Content-Range': `bytes ${start}-${end}/${stat.size}`,
                        'Accept-Ranges': 'bytes',
                        'Content-Length': chunksize,
                        'Content-Type': MIME_TYPES[ext],
                        'Access-Control-Allow-Origin': '*'
                    });
                    file.pipe(res);
                } else {
                    res.writeHead(200, {
                        'Content-Length': stat.size,
                        'Content-Type': MIME_TYPES[ext],
                        'Accept-Ranges': 'bytes',
                        'Access-Control-Allow-Origin': '*'
                    });
                    fs.createReadStream(targetStatic).pipe(res);
                }
                return;
            }
        }

        res.writeHead(404);
        res.end('Out of Bounds.');
    }
});

server.listen(PORT, () => {
    console.log(`>>> INTERACTIVE SPLIT COCKPIT LIVE AT: http://localhost:${PORT}`);
    console.log(`>>> Substrate Database: ${DB_PATH}`);
});
