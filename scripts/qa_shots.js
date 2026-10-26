// Visual QA: opens the pages with real libraries and data, saves screenshots to qa/
const {chromium}=require('playwright');const fs=require('fs');
const H=process.env.GATE_HASH;const base='http://localhost:8099/';
(async()=>{fs.mkdirSync('qa',{recursive:true});const b=await chromium.launch();const log=[];
 const page=async(w,h)=>{const p=await b.newPage({viewport:{width:w,height:h},deviceScaleFactor:1,colorScheme:'dark'});
   await p.addInitScript(h=>{try{localStorage.setItem('wave-gate',h)}catch(e){}},H);
   p.on('pageerror',e=>log.push('pageerror '+e.message));p.on('console',m=>{if(m.type()==='error')log.push('console '+m.text())});return p;};
 const shots=[['pro_sa_1d','cx',null],['pro_btc_4h','cx','BTC'],['pro_eth_1h','cx','ETH']];
 for(const [w,h,tag] of [[430,900,'m'],[1280,900,'d']]){
   const p=await page(w,h);await p.goto(base+'pro.html');await p.waitForTimeout(6000);
   await p.screenshot({path:`qa/pro_2222_${tag}.png`,fullPage:true});await p.click('[data-tf="1M"]');await p.waitForTimeout(2000);await p.screenshot({path:`qa/pro_2222M_${tag}.png`});await p.click('[data-tf="1d"]');await p.waitForTimeout(800);log.push(tag+' sa status: '+await p.textContent('#status'));
   await p.click('[data-as="cx:BTC"]');await p.waitForTimeout(6000);await p.click('[data-tf="4h"]');await p.waitForTimeout(2500);
   await p.screenshot({path:`qa/pro_btc4h_${tag}.png`,fullPage:true});log.push(tag+' btc status: '+await p.textContent('#status'));
   await p.close();}
 const p=await page(430,900);await p.goto(base);await p.waitForTimeout(4000);await p.screenshot({path:'qa/index_m.png'});
 fs.writeFileSync('qa/log.txt',log.join('\n')+'\n');console.log(log.join('\n'));await b.close();})();
