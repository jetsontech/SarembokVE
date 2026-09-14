import { chromium } from 'playwright';

const url = process.argv[2] || 'https://sarembok.com/';
const failures = [];

function check(name, ok, detail = '') {
  console.log(`${name}: ${ok ? 'PASS' : 'FAIL'}${detail ? ` — ${detail}` : ''}`);
  if (!ok) failures.push(name);
}

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({
  viewport: { width: 1440, height: 1000 },
  permissions: [],
});
const page = await context.newPage();

const pageErrors = [];
page.on('pageerror', err => pageErrors.push(String(err)));

try {
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(2500);
  await page.screenshot({ path: '/work/sarembok-boot.png', fullPage: true });
  check('browser navigation', page.url().startsWith(url));
  check('no pageerror during boot', pageErrors.length === 0, pageErrors.slice(0, 3).join(' | '));

  const identity = await page.evaluate(() => ({
    speech: typeof window.normalizeSarembokSpeech === 'function'
      ? window.normalizeSarembokSpeech('SarembokVE is online. Sarembok VE ready.')
      : null,
    legacy: /\b(?:activeAstraFrame|astraVisionMode|astraScreenStream|captureAstraCameraFrame|toggleAstraScreenShare|setAstraActiveFrame|clearAstraFrame|toggleAstraVisionMode)\b/i.test(document.documentElement.innerHTML),
    bareAria: (() => {
      const stripped = document.documentElement.innerHTML.replace(/\baria-[a-z-]+\b/gi, '');
      return /\baria\b/i.test(stripped);
    })()
  }));
  check('speech = Sarembok V E', identity.speech === 'Sarembok V E is online. Sarembok V E ready.', identity.speech || 'missing');
  check('legacy vision symbols absent', !identity.legacy);
  check('bare Aria absent', !identity.bareAria);

  const tabs = ['workspace', 'deck', 'metahuman', 'dialogue', 'agents', 'memory', 'fabric', 'research', 'compute', 'features'];
  for (const tab of tabs) {
    const btn = page.locator(`#dock-btn-${tab}`);
    const exists = await btn.count();
    check(`tab ${tab} exists`, exists === 1);
    if (!exists) continue;
    await btn.click();
    await page.waitForTimeout(120);
    const active = await page.locator('.view-panel.active').evaluateAll(nodes => nodes.map(n => n.id));
    check(`tab ${tab} activates view`, active.includes(`view-${tab}`), active.join(', '));
  }

  // Always return to the actual conversation surface before testing its controls.
  await page.locator('#dock-btn-dialogue').click();
  await page.waitForTimeout(120);
  check('dialogue surface active for interaction test', await page.locator('#view-dialogue').evaluate(el => el.classList.contains('active')));

  await page.locator('#mode-btn-simple').click();
  await page.waitForTimeout(100);
  check('simple mode activates', await page.evaluate(() => document.body.classList.contains('mode-simple')));
  await page.locator('#mode-btn-cockpit').click();
  await page.waitForTimeout(100);
  check('cockpit mode restores', await page.evaluate(() => !document.body.classList.contains('mode-simple')));

  const interactionState = await page.evaluate(() => {
    const button = document.getElementById('execute-button');
    const input = document.getElementById('directive-input');
    if (!button || !input) return { ok: false, reason: 'missing dialogue control' };
    const b = button.getBoundingClientRect();
    const i = input.getBoundingClientRect();
    return {
      ok: b.width > 0 && b.height > 0 && i.width > 0 && i.height > 0,
      button: { width: b.width, height: b.height },
      input: { width: i.width, height: i.height }
    };
  });
  check('dialogue controls visible', interactionState.ok, JSON.stringify(interactionState));
  await page.screenshot({ path: '/work/sarembok-dialogue.png', fullPage: true });

  window.__srbkExecuteHit = false;
  await page.evaluate(() => {
    window.__srbkExecuteHit = false;
    window.sendDirective = () => { window.__srbkExecuteHit = true; };
  });
  await page.locator('#execute-button').click();
  check('execute button dispatches', await page.evaluate(() => window.__srbkExecuteHit === true));

  await page.locator('#hud-features-btn').click();
  await page.waitForTimeout(100);
  check('features button opens features', await page.locator('#view-features').evaluate(el => el.classList.contains('active')));

  await page.locator('#hud-history-drawer-btn').click();
  await page.waitForTimeout(100);
  check('history drawer opens', await page.locator('#task-history-drawer').evaluate(el => el.classList.contains('open')));
  const drawerTabs = await page.locator('.drawer-tab-btn').evaluateAll(btns => btns.map(b => ({ id: b.id, tab: b.id.replace(/^tab-btn-/, '') })));
  for (const d of drawerTabs) {
    await page.locator(`#${d.id}`).click();
    await page.waitForTimeout(100);
    check(`drawer tab ${d.tab} activates`, await page.locator(`#drawer-panel-${d.tab}`).evaluate(el => el.classList.contains('active')));
  }
  await page.locator('#task-history-backdrop').click().catch(() => {});

  for (const width of [1440, 700, 390]) {
    await page.setViewportSize({ width, height: 900 });
    const result = await page.evaluate(() => {
      const host = document.getElementById('dialogue-history') || document.body;
      const holder = document.createElement('div');
      holder.id = '__srbk_video_acceptance_host';
      holder.style.cssText = 'width:100%; max-width:100%; overflow:hidden;';
      const card = document.createElement('div');
      card.innerHTML = window.renderVideoCard('Acceptance Video', 'https://www.youtube.com/watch?v=dQw4w9WgXcQ');
      const node = card.firstElementChild;
      holder.appendChild(node);
      host.appendChild(holder);
      const cardRect = node.getBoundingClientRect();
      const hostRect = host.getBoundingClientRect();
      const wrap = node.querySelector('.srbk-video-player-wrap');
      const iframe = node.querySelector('.srbk-video-iframe');
      const wrapRect = wrap?.getBoundingClientRect();
      const iframeRect = iframe?.getBoundingClientRect();
      const ok = !!node && !!wrap && !!iframe &&
        cardRect.width <= hostRect.width + 1 &&
        wrapRect.width <= node.getBoundingClientRect().width + 1 &&
        iframeRect.width <= wrapRect.width + 1 &&
        iframeRect.height <= wrapRect.height + 1 &&
        Math.abs((wrapRect.width / wrapRect.height) - (16 / 9)) < 0.03;
      holder.remove();
      return { ok, card: cardRect.width, host: hostRect.width, wrap: wrapRect?.width, iframe: iframeRect?.width, ratio: wrapRect ? wrapRect.width / wrapRect.height : null };
    });
    check(`video fits at ${width}px`, result.ok, JSON.stringify(result));
  }

  const markdown = await page.evaluate(() => {
    const standard = window.md('### Comparison\n\n| Feature | SarembokVE | Chat app |\n| --- | --- | --- |\n| Memory | Persistent | Session-limited |\n| Planning | Task graph | Prompt response |\n\n- One\n- Two');
    const neutral = window.enrichResponseOnClient(
      "Explain SarembokVE's purpose in 3 clearly formatted sections, with bullets where appropriate and a small table comparing SarembokVE with a conventional AI chat application.",
      'Section one. Section two. Section three.\n\n| Feature | SarembokVE | Conventional AI chat |\n| --- | --- | --- |\n| State | Persistent | Limited |\n| Agents | Orchestrated | Usually single |'
    );
    const videoPrompt = window.enrichResponseOnClient('watch a video about NASA', 'NASA video');
    return { standard, neutral, videoPrompt };
  });
  check('markdown table renders', /<table[\s>]/i.test(markdown.standard) && !/\|\s*Feature\s*\|/i.test(markdown.standard));
  check('markdown bullets render', /<li[\s>]/i.test(markdown.standard));
  check('neutral prompt has no unsolicited video card', !/srbk-video-card|srbk-music-card|<iframe/i.test(markdown.neutral));
  check('explicit video intent creates video card', /srbk-video-card/i.test(markdown.videoPrompt));

  const selection = await page.evaluate(() => {
    const bubble = document.querySelector('.srbk-bubble .srbk-content');
    if (!bubble) return { ok: false, reason: 'no bubble' };
    const range = document.createRange();
    range.selectNodeContents(bubble);
    const sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(range);
    return { ok: !!sel && sel.toString().trim().length > 0, text: sel?.toString().slice(0, 60) || '' };
  });
  check('response text is selectable', selection.ok, selection.text);

  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.locator('#hud-auth-btn').click();
  check('auth menu opens', await page.locator('#hud-user-dropdown').isVisible());

  check('no new page errors', pageErrors.length === 0, pageErrors.slice(-3).join(' | '));
} finally {
  await browser.close();
}

console.log('\n===== BROWSER ACCEPTANCE RESULT =====');
if (failures.length) {
  console.log(`FAIL (${failures.length}): ${failures.join(', ')}`);
  process.exit(1);
}
console.log('PASS — primary navigation, controls, media layout, renderer behavior, selection, and auth menu verified in Chromium.');
