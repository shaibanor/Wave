// Live check of the voice agent on the published site (fake microphone), from GitHub Actions.
const {chromium}=require('playwright');
(async()=>{const b=await chromium.launch({args:['--use-fake-ui-for-media-stream','--use-fake-device-for-media-stream','--autoplay-policy=no-user-gesture-required']});
  const c=await b.newContext({permissions:['microphone'],viewport:{width:430,height:900}});const p=await c.newPage();
  const H=process.env.GATE_HASH||'';
  await p.addInitScript(h=>{try{sessionStorage.setItem('tk-gate',JSON.stringify({h:h,x:Date.now()+36e5}));localStorage.setItem('wave-all','2222')}catch(e){}},H);
  p.on('console',m=>{const t=m.text();if(/agent|eleven|webrtc|livekit|error|warn/i.test(t))console.log('console',m.type(),t.slice(0,400));});
  p.on('pageerror',e=>console.log('pageerror',String(e).slice(0,400)));
  p.on('requestfailed',r=>{if(/eleven|jsdelivr|livekit/.test(r.url()))console.log('reqfail',r.url().slice(0,160),r.failure()&&r.failure().errorText);});
  p.on('response',r=>{if(/elevenlabs|livekit/.test(r.url())&&r.status()>=400)console.log('resp',r.status(),r.url().slice(0,200));});
  await p.goto('https://shaibanor.github.io/Wave/?v='+Date.now(),{waitUntil:'load'});await p.waitForTimeout(5000);
  await p.click('#tkAgent');
  await p.waitForTimeout(9000);await p.fill('#agTxt',process.env.AGENT_Q||'وش رأيك في سهم أرامكو الحين؟');await p.press('#agTxt','Enter');
  for(let i=0;i<14;i++){await p.waitForTimeout(3000);const s=await p.evaluate(()=>[document.getElementById('agSt')&&agSt.textContent,document.getElementById('agLog')&&agLog.innerText.replace(/\s+/g,' ').slice(-900)]);console.log('t'+(i*3+3),JSON.stringify(s));}
  await p.screenshot({path:'agent_live.png'});await b.close();})();
