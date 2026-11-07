(function(){
  /* «أخبار السلحفاة»: market-wide headlines per market (listings, IPOs, results, dividends, regulation)
     plus per-asset headlines, with a swimming 3D turtle host. */
  const RAW='https://raw.githubusercontent.com/shaibanor/Wave/main/';
  const $=id=>document.getElementById(id);
  const esc=s=>String(s==null?'':s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  const MK=[['sa','السوق السعودي'],['us','السوق الأمريكي'],['cx','العملات الرقمية'],['ix','السلع والمؤشرات']];
  const CAT=[['ipo','اكتتابات وإدراج',/(اكتتاب|إدراج|ادراج|طرح|الطرح|نمو|السوق الموازية|ipo|debut|listing|lists|listed|launches token)/i],
    ['earn','نتائج وأرباح',/(نتائج|أرباح|ارباح|الربع|صافي|earnings|revenue|profit|quarter|guidance)/i],
    ['div','توزيعات',/(توزيع|توزيعات|كوبون|dividend|buyback)/i],
    ['reg','تنظيم وقرارات',/(هيئة|تنظيم|قرار|المركزي|الفيدرالي|sec\b|regulat|law|ban|approval|approves|fed\b|federal reserve|opec|أوبك)/i]];
  const cat=t=>{for(const c of CAT)if(c[2].test(t))return c[0];return'gen';};
  const CN={ipo:'اكتتاب وإدراج',earn:'نتائج',div:'توزيعات',reg:'تنظيم',gen:'عام'};
  let M=null,N=null,mk='sa',cf='all',busy=false;
  async function get(f){for(const b of [RAW,'']){try{const r=await fetch(b+f+'?v='+Date.now(),{cache:'no-store'});if(r.ok)return await r.json();}catch(_){}}return null;}
  const ago=d=>{const t=Date.parse(d);if(!isFinite(t))return'';const n=Math.round((Date.now()-t)/864e5);return n<=0?'اليوم':n===1?'أمس':n===2?'قبل يومين':n<=10?`قبل ${n} أيام`:`قبل ${n} يومًا`;};
  function list(items){if(!items.length)return'<p class="nh-e">لا توجد أخبار في هذا التصنيف حاليًا.</p>';
    return`<ul class="nh-l">${items.map(x=>{const c=cat(x.t);return`<li class="c-${c}"><span class="nh-c">${CN[c]}</span><a href="${esc(x.u)}" target="_blank" rel="noopener noreferrer" dir="auto">${esc(x.t)}</a><small>${esc(x.s||'')}${x.d?' · '+ago(x.d):''}${x.lang==='en'?' · EN':''}</small></li>`;}).join('')}</ul>`;}
  function draw(){const el=$('nhBody');if(!el)return;document.querySelectorAll('[data-nhm]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.nhm===mk)));document.querySelectorAll('[data-nhc]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.nhc===cf)));
    if(!M&&!N){el.innerHTML=busy?'<p class="nh-e"><span class="ov-spin"></span> جارٍ جلب الأخبار…</p>':'<p class="nh-e">تعذر جلب الأخبار الآن.</p>';return;}
    let L=(M&&M.m&&M.m[mk])||[];if(cf!=='all')L=L.filter(x=>cat(x.t)===cf);
    const A=((window.WAVE_API&&WAVE_API.assets)||[]).filter(a=>(mk==='sa'?a.market==='saudi':mk==='us'?a.market==='us':mk==='cx'?a.market==='crypto':a.market==='ix'));
    const per=A.map(a=>{const it=(N&&N.a&&N.a[a.id])||[];return it.length?`<details class="nh-a"><summary>${window.EMB?EMB.tag(a.id,26):''}<b>${esc(a.btn||a.name)}</b><small>${it.length} خبر · آخرها ${ago(it[0].d)}</small></summary>${list(it.slice(0,8))}</details>`:'';}).join('');
    el.innerHTML=`<section class="nh-s"><h3>أخبار ${esc(MK.find(x=>x[0]===mk)[1])}</h3>${list(L.slice(0,30))}</section>${per?`<section class="nh-s"><h3>أخبار كل سهم</h3>${per}</section>`:''}
      <p class="nh-n">العناوين تُجمع آليًا من Google News وتُصنَّف بالكلمات الدالة. اضغط الخبر لقراءته من مصدره. آخر تحديث: ${esc(((M||N||{}).updated||'').replace('T',' ').replace('Z',' UTC'))}</p>`;}
  async function load(){if(M||busy)return draw();busy=true;draw();[M,N]=await Promise.all([get('pro/mnews.json'),get('pro/news.json')]);busy=false;draw();}
  let raf=0,t0=0;function swim(now){const c=$('nhTurtle');if(!c||$('nhApp').hidden){raf=0;return;}const g=c.getContext('2d'),d=c.width/140;g.setTransform(1,0,0,1,0,0);g.clearRect(0,0,c.width,c.height);
    const t=(now-t0)/1000;g.save();g.translate(c.width/2+Math.sin(t*.7)*c.width*.04,Math.sin(t*1.3)*4*d);g.scale(-.86,.86);g.translate(-c.width*.5,c.width*.06);if(window.TURTLE)TURTLE.draw(g,c.width,t,{skin:'arctic',move:'hover',mp:.5});g.restore();raf=requestAnimationFrame(swim);}
  function open(){const o=$('nhApp');o.hidden=false;requestAnimationFrame(()=>o.classList.add('on'));document.documentElement.classList.add('ov-open');const c=$('nhTurtle'),dd=Math.min(2.5,devicePixelRatio||1);c.width=c.height=Math.round(140*dd);t0=performance.now();if(!raf)raf=requestAnimationFrame(swim);load();}
  function close(){const o=$('nhApp');o.classList.remove('on');document.documentElement.classList.remove('ov-open');setTimeout(()=>{o.hidden=true;},300);}
  function init(){const b=$('nhOpen');if(!b)return;
    const mc=$('nhMini');if(mc&&window.TURTLE){const mg=mc.getContext('2d');let lt=0;const ml=now=>{if(now-lt>50&&!document.hidden){lt=now;mg.setTransform(1,0,0,1,0,0);mg.clearRect(0,0,128,128);TURTLE.draw(mg,128,now/1000);}requestAnimationFrame(ml);};requestAnimationFrame(ml);}b.addEventListener('click',open);$('nhX').addEventListener('click',close);
    document.querySelectorAll('[data-nhm]').forEach(x=>x.addEventListener('click',()=>{mk=x.dataset.nhm;draw();}));
    document.querySelectorAll('[data-nhc]').forEach(x=>x.addEventListener('click',()=>{cf=x.dataset.nhc;draw();}));
    document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!$('nhApp').hidden)close();});}
  document.readyState==='loading'?document.addEventListener('DOMContentLoaded',init):init();
  window.NEWSHUB={open};
})();
