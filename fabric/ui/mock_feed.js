/**
 * Antigravity Gemini Fabric (V3.8-Flash) - Mock Feed Visualization Script
 * Context: Sovereign Protocol [DIRECTIVE-01]
 * Implementation Target: c:/SarembokVE/fabric/ui/mock_feed.js
 * 
 * Feeds dummy agent steps into the SQLite-WAL database to test real-time cockpit rendering.
 */

const http = require('node:http');

const PORT = process.env.COCKPIT_PORT || 3800;

function postRequest(endpoint, body = {}) {
  return new Promise((resolve, reject) => {
    const data = JSON.stringify(body);
    const req = http.request({
      hostname: 'localhost',
      port: PORT,
      path: endpoint,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(data)
      }
    }, res => {
      let responseBody = '';
      res.on('data', chunk => { responseBody += chunk; });
      res.on('end', () => {
        try {
          resolve(JSON.parse(responseBody));
        } catch {
          resolve(responseBody);
        }
      });
    });

    req.on('error', reject);
    req.write(data);
    req.end();
  });
}

const sleep = ms => new Promise(r => setTimeout(r, ms));

async function runMockSimulation() {
  console.log('>>> [MOCK FEED] Starting real-time Antigravity Cockpit visualization feed...');
  console.log(`>>> [MOCK FEED] Target Server: http://localhost:${PORT}`);

  try {
    // 1. Reset
    console.log('\n1. Resetting session envelope...');
    await postRequest('/api/reset');
    await sleep(600);

    // 2. Normal Step 1
    console.log('2. Emitting Turn 1: Edge routing and micro-step initialization...');
    await postRequest('/api/step', { directive: 'Edge routing and micro-step initialization' });
    await sleep(700);

    // 3. Normal Step 2
    console.log('3. Emitting Turn 2: Compute tensor projection & verify baseline state...');
    await postRequest('/api/step', { directive: 'Compute tensor projection & verify baseline state' });
    await sleep(700);

    // 4. Trigger Recursive Loop
    console.log('4. Triggering Recursive Loop Interception (Entropy >= 0.88)...');
    await postRequest('/api/simulate-loop');
    console.log('   -> WORKER transitioned to FROZEN (flashing red flare).');
    console.log('   -> Logged committed = 0 soft-rollback entry with strike-through.');
    await sleep(1500);

    // 5. Recovery Step
    console.log('5. Emitting Recovery Turn 3: Strategist self-heals loop and unfreezes pipeline...');
    await postRequest('/api/step', { directive: 'Strategist context re-routing & loop recovery' });
    await sleep(700);

    console.log('\n>>> [MOCK FEED] COMPLETE! Cockpit is live and continuously rendering telemetry.');
  } catch (err) {
    console.error('>>> [MOCK FEED ERROR]:', err.message);
  }
}

if (require.main === module) {
  runMockSimulation();
}

module.exports = { runMockSimulation };
