const { spawn } = require('child_process');
const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const URL = 'http://localhost:8000/apps/web/viewer.html';
const PORT = 9336;
const chrome = spawn(CHROME, ['--headless=new','--no-first-run','--use-gl=swiftshader','--enable-unsafe-swiftshader',`--remote-debugging-port=${PORT}`,'about:blank'], {stdio:'ignore'});
const sleep = ms => new Promise(r=>setTimeout(r,ms));
(async () => {
  let t;
  for (let i=0;i<60;i++){ try{ const r=await fetch(`http://localhost:${PORT}/json/new?${encodeURIComponent(URL)}`,{method:'PUT'}); t=await r.json(); if(t.webSocketDebuggerUrl)break;}catch(e){} await sleep(300); }
  const ws = new WebSocket(t.webSocketDebuggerUrl);
  await new Promise(r=>ws.addEventListener('open',r));
  let id=0; const pending=new Map();
  const logs=[];
  ws.addEventListener('message',ev=>{const m=JSON.parse(typeof ev.data==='string'?ev.data:Buffer.from(ev.data).toString()); if(m.id&&pending.has(m.id)){pending.get(m.id)(m);pending.delete(m.id);} if(m.method==='Runtime.consoleAPICalled'){logs.push(m.params.args.map(a=>a.value||a.description||'').join(' '));} if(m.method==='Runtime.exceptionThrown'){logs.push('EXCEPTION: '+(m.params.exceptionDetails.exception?.description||m.params.exceptionDetails.text));}});
  const send=(method,params={})=>new Promise(r=>{const mid=++id;pending.set(mid,r);ws.send(JSON.stringify({id:mid,method,params}));});
  await send('Runtime.enable'); await send('Log.enable'); await send('Page.enable');
  await sleep(15000);
  const res = await send('Runtime.evaluate',{expression:`JSON.stringify({
    ok: document.getElementById('hud-ok')&&document.getElementById('hud-ok').style.display!=='none'?document.getElementById('hud-ok').textContent:'',
    err: document.getElementById('hud-err')&&document.getElementById('hud-err').style.display!=='none'?document.getElementById('hud-err').textContent:'',
    meta: document.getElementById('hud-meta').textContent,
    canvases: document.querySelectorAll('canvas').length,
  })`, returnByValue:true});
  console.log('STATE:', res.result && res.result.result && res.result.result.value);
  console.log('CONSOLE LOGS:', JSON.stringify(logs.slice(0,25), null, 1));
  ws.close(); chrome.kill(); process.exit(0);
})().catch(e=>{console.error('ERR',e.message);try{chrome.kill()}catch{}process.exit(1);});
