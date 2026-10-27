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
  await p.screenshot({path:`qa/pro_sol_${tag}.png`,fullPage:true});await p.close();}
 fs.writeFileSync('qa/log.txt',log.join('\n')+'\n');console.log(log.join('\n'));await b.close();})();
