// Visual QA on the unified page: real libraries and data
const {chromium}=require('playwright');const fs=require('fs');
const H=process.env.GATE_HASH;const base='http://localhost:8099/';
(async()=>{fs.mkdirSync('qa',{recursive:true});const b=await chromium.launch();const log=[];
 for(const [w,h,tag] of [[430,900,'m'],[1280,900,'d']]){
  const p=await b.newPage({viewport:{width:w,height:h},colorScheme:'dark'});
  await p.addInitScript(h=>{try{localStorage.setItem('wave-gate',h);localStorage.setItem('wave-all','2222')}catch(e){}},H);
  p.on('pageerror',e=>log.push('pageerror '+e.message));
  await p.goto(base);await p.waitForTimeout(6000);await p.screenshot({path:`qa/now_2222_${tag}.png`,fullPage:true});
  log.push(tag+' live: '+(await p.textContent('#lvHead')).replace(/\s+/g,' ').slice(0,90));
  await p.click('#t-pro');await p.waitForTimeout(5000);log.push(tag+' sa status: '+(await p.textContent('#pStatus')));
  await p.click('[data-ptf="4h"]');await p.waitForTimeout(2000);await p.screenshot({path:`qa/pro_2222_4h_${tag}.png`,fullPage:true});
  await p.click('[data-cat="crypto"]');await p.click('[data-a="SOL"]');await p.waitForTimeout(6000);log.push(tag+' sol status: '+(await p.textContent('#pStatus')));
  await p.screenshot({path:`qa/pro_sol_${tag}.png`,fullPage:true});
  await p.click('#t-chart');await p.waitForTimeout(6000);
  log.push(tag+' chart canvases: '+(await p.evaluate(()=>document.querySelectorAll('#cxMain canvas').length)));
  log.push(tag+' chart legend: '+(await p.textContent('#cxLeg')).replace(/\s+/g,' ').slice(0,90));
  log.push(tag+' chart signals: '+(await p.textContent('#cxSig')).replace(/\s+/g,' ').slice(0,140));
  for(const k of ['bb','macd','ichi','st','psar','vp','stoch','obv','cci']){await p.evaluate(k=>{const c=document.querySelector(`[data-cxi="${k}"]`);c.checked=true;c.dispatchEvent(new Event('change'));},k);await p.waitForTimeout(300);}
  for(const t of ['ha','bar','line','area','candle']){await p.selectOption('#cxType',t);await p.waitForTimeout(300);}
  for(const f of ['1h','4h','1w','1M','1d']){await p.click(`[data-cxf="${f}"]`).catch(()=>{});await p.waitForTimeout(400);}
  await p.click('[data-cxt="trend"]');await p.evaluate(()=>document.getElementById('cxMain').scrollIntoView({block:'center'}));await p.waitForTimeout(300);const bx=await p.locator('#cxMain').boundingBox();await p.mouse.click(bx.x+80,bx.y+200);await p.mouse.click(bx.x+220,bx.y+120);
  await p.click('[data-cxt="long"]');await p.evaluate(()=>document.getElementById('cxMain').scrollIntoView({block:'center'}));await p.waitForTimeout(300);const by=await p.locator('#cxMain').boundingBox();await p.mouse.click(by.x+180,by.y+220);
  log.push(tag+' chart drawings: '+(await p.evaluate(()=>Object.keys(localStorage).filter(k=>k.startsWith('cx-draw')).map(k=>localStorage.getItem(k).length).join(','))));
  await p.screenshot({path:`qa/chart_sol_${tag}.png`,fullPage:true});
  log.push(tag+' chart panes: '+(await p.evaluate(()=>document.querySelectorAll('#cxPanes .cx-pane').length)));
  await p.close();}
 fs.writeFileSync('qa/log.txt',log.join('\n')+'\n');console.log(log.join('\n'));await b.close();})();
