// Verify the Vision 5D viewer loads the real GLB via GLTFLoader (CDP).
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const URL = 'http://localhost:8000/apps/web/viewer.html';
const OUT = process.env.LOCALAPPDATA + '/Temp';
const PORT = 9334;

const chrome = spawn(CHROME, [
  '--headless=new', '--disable-gpu', '--no-first-run', '--hide-scrollbars',
  `--remote-debugging-port=${PORT}`, '--window-size=1440,900', 'about:blank'
], { stdio: 'ignore' });

const sleep = (ms) => new Promise(r => setTimeout(r, ms));

async function getPageWsUrl() {
  for (let i = 0; i < 60; i++) {
    try {
      const r = await fetch(`http://localhost:${PORT}/json/new?${encodeURIComponent(URL)}`, { method: 'PUT' });
      const t = await r.json();
      if (t.webSocketDebuggerUrl) return t.webSocketDebuggerUrl;
    } catch (e) { /* retry */ }
    await sleep(300);
  }
  throw new Error('CDP page target unreachable');
}

(async () => {
  const wsUrl = await getPageWsUrl();
  const ws = new WebSocket(wsUrl);
  await new Promise((res, rej) => { ws.addEventListener('open', res); ws.addEventListener('error', rej); });

  let id = 0;
  const pending = new Map();
  ws.addEventListener('message', (ev) => {
    const m = JSON.parse(typeof ev.data === 'string' ? ev.data : Buffer.from(ev.data).toString());
    if (m.id && pending.has(m.id)) {
      pending.get(m.id)(m);
      pending.delete(m.id);
    }
  });
  const send = (method, params = {}) => new Promise((res) => {
    const mid = ++id;
    pending.set(mid, res);
    ws.send(JSON.stringify({ id: mid, method, params }));
  });

  await send('Page.enable');
  await send('Page.navigate', { url: URL });

  // Poll for GLB load completion (HUD ok/err populated)
  let status = {};
  for (let i = 0; i < 120; i++) {
    await sleep(500);
    const m = await send('Runtime.evaluate', {
      expression: `JSON.stringify({
        title: document.title,
        ok: document.getElementById('hud-ok') && document.getElementById('hud-ok').style.display !== 'none' ? document.getElementById('hud-ok').textContent : '',
        err: document.getElementById('hud-err') && document.getElementById('hud-err').style.display !== 'none' ? document.getElementById('hud-err').textContent : '',
        meta: document.getElementById('hud-meta') ? document.getElementById('hud-meta').textContent : '',
      })`,
      returnByValue: true,
    });
    const v = m.result && m.result.result && m.result.result.value;
    if (v) {
      status = JSON.parse(v);
      if (status.ok || status.err) break;
    }
    if (m.error) { status = { cdpError: m.error }; break; }
  }

  console.log('VIEWER STATUS:', JSON.stringify(status, null, 2));

  const shot = await send('Page.captureScreenshot', { format: 'png' });
  if (shot.result && shot.result.data) {
    const p = path.join(OUT, 'v5d_viewer_verified.png');
    fs.writeFileSync(p, Buffer.from(shot.result.data, 'base64'));
    console.log('SCREENSHOT:', p);
  } else {
    console.log('SCREENSHOT: failed', JSON.stringify(shot).slice(0, 200));
  }

  ws.close();
  chrome.kill();
  process.exit(0);
})().catch(e => { console.error('ERROR:', e); try { chrome.kill(); } catch {} process.exit(1); });
