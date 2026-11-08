(function(){
  const $=id=>document.getElementById(id);
  const esc=s=>String(s==null?'':s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  const API=()=>window.WAVE_API;
  if(!$('botBtn')||!API())return;

  /* ---------- language ---------- */
  const norm=s=>String(s||'').toLowerCase()
    .replace(/[ً-ٰٟـ]/g,'').replace(/[أإآٱ]/g,'ا').replace(/ة/g,'ه').replace(/ى/g,'ي').replace(/ؤ/g,'و').replace(/ئ/g,'ي')
    .replace(/[٠-٩]/g,d=>String('٠١٢٣٤٥٦٧٨٩'.indexOf(d))).replace(/[۰-۹]/g,d=>String('۰۱۲۳۴۵۶۷۸۹'.indexOf(d)))
    .replace(/[؟?!.,،؛:()"'«»\-_/\\*]+/g,' ').replace(/\s+/g,' ').trim();
  const ALIAS={
    '2222':['ارامكو','أرامكو السعودية','aramco'],'1120':['الراجحي','مصرف الراجحي','بنك الراجحي','rajhi'],'4340':['الراجحي ريت','ريت الراجحي','صندوق الراجحي ريت'],
    '8311':['عناية'],'1211':['معادن','maaden'],'1180':['الأهلي','البنك الأهلي','الأهلي السعودي','snb'],'7010':['stc','اس تي سي','الاتصالات','الاتصالات السعودية'],
    '2010':['سابك','sabic'],'2082':['أكوا','أكوا باور','acwa'],'4013':['الحبيب','سليمان الحبيب'],'1010':['بنك الرياض','riyad bank'],'1325':['حديد وطني','وطني للحديد','حديد الوطني','الوطني للحديد','watani steel'],'1150':['الإنماء','مصرف الإنماء','بنك الإنماء','alinma'],
    'BTC':['بيتكوين','بتكوين','bitcoin','بيتكون'],'ETH':['إيثريوم','ايثيريوم','إيثيريوم','الإيثر','ايثر','ethereum'],'XRP':['ريبل','ripple'],'BNB':['بينانس','بي إن بي'],
    'SOL':['سولانا','solana'],'TRX':['ترون','tron'],'DOGE':['دوج','دوجكوين','دوج كوين','dogecoin'],'ZEC':['زي كاش','زيكاش','zcash'],'LINK':['لينك','تشين لينك','chainlink'],
    'ADA':['كاردانو','cardano'],'LTC':['لايتكوين','لايت كوين','ليتكوين','litecoin'],
    'GOOGL':['قوقل','جوجل','google','ألفابت','alphabet'],'META':['ميتا','فيسبوك','facebook'],'AVGO':['برودكوم','broadcom'],'TSM':['تايوان','tsmc','تايوان للرقائق'],
    'JPM':['جي بي مورقان','جي بي مورغان','jp morgan','jpmorgan','مورقان','مورغان'],'LLY':['إيلي ليلي','ليلي','eli lilly'],'V':['فيزا','visa'],
    'TASI':['تاسي','المؤشر العام','مؤشر السوق','السوق السعودي','المؤشر السعودي','السوق'],'DJI':['داو جونز','داوجونز','الداو','dow jones','dow'],
    'SPX':['اس اند بي','إس آند بي','اس آند بي','s&p','s&p 500','sp500','اس اند بي 500'],'NDX':['ناسداك','nasdaq'],'GOLD':['الذهب','ذهب','gold','الدهب'],
    'SILVER':['الفضة','فضة','silver'],'BRENT':['برنت','النفط','نفط','البترول','brent','oil'],'US10Y':['السندات','عائد السندات','سندات','السندات الأمريكية','us10y'],'DXY':['مؤشر الدولار','dxy']};
  const AS=API().assets.filter(a=>a.pro),BY=Object.fromEntries(AS.map(a=>[a.id,a]));
  const PAT=[];
  for(const a of AS){const set=new Set([a.name,a.btn,...(ALIAS[a.id]||[])]);if(a.id.length>1)set.add(a.id);
    for(const raw of set){const n=norm(raw);if(!n||n.length<2)continue;const v=new Set([n]);if(n.startsWith('ال')&&n.length>4)v.add(n.slice(2));else if(!/^[a-z0-9&]/.test(n))v.add('ال'+n);
      for(const x of v)PAT.push({id:a.id,x,re:new RegExp('(^| )(و|ف|ب|ك|ل|لل|وب|ول)?'+x.replace(/[.*+?^${}()|[\]\\&]/g,'\\$&')+'( |$)')});}}
  PAT.sort((p,q)=>q.x.length-p.x.length);
  const skel=w=>w.replace(/[اويىءئؤ]/g,'');
  const lev=(a,b)=>{if(Math.abs(a.length-b.length)>2)return 9;const d=Array.from({length:a.length+1},(_,i)=>[i]);for(let j=1;j<=b.length;j++)d[0][j]=j;
    for(let i=1;i<=a.length;i++)for(let j=1;j<=b.length;j++)d[i][j]=Math.min(d[i-1][j]+1,d[i][j-1]+1,d[i-1][j-1]+(a[i-1]===b[j-1]?0:1));return d[a.length][b.length];};
  function fuzzy(t){let best=null;const skip=typeof STOP!=='undefined'?STOP:new Set();
    for(const raw of t.split(' ')){const w=raw.replace(/^(و|ف|ب|ل|ك)?(ال)?/,'');if(w.length<4||skip.has(raw)||skip.has(w))continue;const sw=skel(w);
      for(const p of PAT){if(p.x.includes(' '))continue;const x=p.x.replace(/^ال/,'');if(x.length<4)continue;let sc=99;
        if(sw.length>=3&&skel(x)===sw)sc=.5;else{const d=lev(w,x),lim=w.length>=7?2:1;if(d<=lim)sc=d;}
        if(sc<99&&(!best||sc<best.sc))best={id:p.id,sc};}}
    return best?[best.id]:[];}
  function findAssets(t){const r=findExact(t);return r.length?r:fuzzy(t);}
  function findExact(t){const hits=[];for(const p of PAT){const m=p.re.exec(t);if(!m)continue;const s=m.index+m[1].length+(m[2]||'').length,e=s+p.x.length;
      if(hits.some(h=>s<h.e&&e>h.s))continue;hits.push({id:p.id,s,e});}
    const out=[];hits.sort((a,b)=>a.s-b.s).forEach(h=>{if(!out.includes(h.id))out.push(h.id);});return out;}
  const TFR=[['4h',/(4 ?ساعات|اربع ساعات|4 ?h\b|اربع ساعه|4 ساعه)/],['1h',/(^| )(ال)?(ساعه|ساعي|1h)( |$)/],['1w',/(^| )(ال)?اسبوعي( |$)/],['1M',/(^| )(ال)?(شهري|شهر)( |$)/],['1d',/(^| )(ال)?(يومي|1d)( |$)/]];
  const tfOf=t=>{for(const [k,r] of TFR)if(r.test(t))return k;return null;};
  const has=(t,r)=>r.test(t);
  const I={
    greet:/^(السلام|سلام|مرحبا|هلا|اهلا|هاي|hi|hello|صباح|مساء|كيف حالك|شلونك|كيفك)/,thanks:/(شكرا|يعطيك|مشكور|جزاك|تسلم)/,
    help:/(وش تقدر|ماذا تستطيع|كيف استخدم|ساعدني|مساعده|ايش تسوي|وش تسوي)/,
    list:/(وش الاسهم|ايش الاسهم|الاصول المتاحه|المتاحه|القائمه|وش عندك|ايش عندك|ماذا تحلل|وش تحلل)/,
    rank:/(اقوي|افضل|احسن|اضعف|اسوا|ترتيب|انسب)/,cmp:/(قارن|مقارنه|الفرق بين|افضل من|احسن من|ولا)/,
    weekly:/(اغلاق|يغلق|تغلق|الاسبوع|هالاسبوع|نهايه الاسبوع|الاسبوع الجاي|الاسبوع القادم|الجمعه|الخميس)/,
    levels:/(دعم|مقاوم|مستوي|مستويات)/,target:/(هدف|اهداف|يوصل|يصل|توصل|تصل|الي كم|لين كم|وين يروح|وين بيروح|سقف)/,
    mom:/(rsi|زخم|تشبع|macd|ماكد|انحراف|دايفرجنس)/,act:/(اشتري|اشتر|شراء|ابيع|بيع|ادخل|دخول|اخرج|استثمر|يستاهل|اجمع|اعزز|اتعزز)/,
    news:/(خبر|اخبار)/,plan:/(وين اشتري|متي اشتري|وين ابيع|متي ابيع|نقطه دخول|نقاط دخول|نقطه الدخول|منطقه شراء|منطقه الشراء|منطقه بيع|وقف الخساره|ستوب|خطه|خطة|كيف اتداول|كيف ادخل|وش اسوي|ايش اسوي|ماذا افعل|افضل سعر|سعر الشراء|سعر البيع|اين اشتري|اين ابيع)/,
    why:/^(ليش|لماذا|ليه|علي ايش|علي اي اساس|كيف عرفت|وش السبب|السبب|ايش السبب)/,
    bull:/(لو طلع|اذا طلع|لو ارتفع|اذا ارتفع|لو اخترق|اذا اخترق|لو كسر المقاومه|سيناريو الصعود|لو صعد|اذا صعد)/,
    bear:/(لو نزل|اذا نزل|لو كسر|اذا كسر|لو هبط|اذا هبط|لو طاح|اذا طاح|سيناريو الهبوط)/,
    sit:/(وش يصير|ايش يصير|ماذا يحدث|وش الوضع|ايش الوضع|كيف الوضع|وضعه|وضعها|فهمني|اشرح لي وضع|وش قاعد يصير|ايش قاعد يصير|الصوره|ملخص)/,
    yes:/^(نعم|ايوه|ايه|اكيد|تمام|اوكي|ok|يب|طيب|زين|ياليت|كمل|اكمل|المزيد|زيدني|وبعد)( |$)/,define:/(ما هو|ما هي|ماهو|ماهي|وش يعني|ايش يعني|وش معني|معني|اشرح|شرح|عرف|تعريف|كيف اقرا|كيف تحسب|كيف يحسب)/};
  /* English questions (English interface) */
  const EI={greet:/^(hey|good (morning|evening|afternoon))\b/,thanks:/\b(thanks|thank you|thx)\b/,help:/\b(help|what can you do|how do i use|how to use)\b/,
    list:/\b(list|available assets|what do you (cover|analy[sz]e|have))\b/,rank:/\b(strongest|best|weakest|worst|rank|ranking|top)\b/,cmp:/\b(compare|vs|versus|difference between|better than)\b/,
    weekly:/\b(close|closing|this week|next week|weekly close|end of (the )?week|friday|thursday)\b/,levels:/\b(support|resistance|levels?)\b/,target:/\b(targets?|reach|how high|upside|go to)\b/,
    mom:/\b(momentum|overbought|oversold|divergence)\b/,act:/\b(buy|sell|enter|exit|invest|worth it)\b/,news:/\b(news|headlines?)\b/,
    plan:/\b(plan|where (to|do i|should i) (buy|sell)|when (to |do i |should i )?(buy|sell)|entry|entries|stop ?loss|buy zone|sell zone|what should i do|how (to|do i) trade)\b/,
    why:/^(why|how do you know|what'?s the reason|reason)\b/,bull:/\b(if it (rises|goes up|breaks out|breaks resistance|climbs)|bull(ish)? (case|scenario))\b/,
    bear:/\b(if it (drops|falls|breaks down|goes down|breaks support)|bear(ish)? (case|scenario))\b/,
    sit:/\b(situation|status|what'?s happening|what is happening|how is|how'?s|overview|summary|outlook)\b/,yes:/^(yes|yeah|yep|sure|more|continue|go on)\b/,
    define:/\b(what is|what'?s an?|meaning of|define|how to read|how is it calculated)\b/};
  for(const k in EI)if(I[k])I[k]=new RegExp(I[k].source+'|'+EI[k].source);
  TFR.push(['4h',/\b(4 ?hours?|four hours?)\b/],['1h',/\b(hourly|1 ?hour)\b/],['1w',/\bweekly\b/],['1M',/\bmonthly\b/],['1d',/\bdaily\b/]);
  const GLOSS=[
    [/(^| )rsi|القوه النسبيه/,'RSI · مؤشر القوة النسبية','يقيس سرعة الحركة على مقياس من 0 إلى 100. فوق 70 يعني تشبع شراء وقد يتبعه تصحيح، وتحت 30 تشبع بيع وقد يتبعه ارتداد. يعتبره الموقع إيجابيًا فوق 55 وسلبيًا تحت 45، وما بينهما حياد.'],
    [/macd|ماكد/,'MACD','الفرق بين متوسطين متحركين أسيين (12 و26) مع خط إشارة (9). عندما يكون الهيستوغرام موجبًا فالزخم يميل للصعود، وعندما يكون سالبًا يميل للهبوط.'],
    [/(^| )atr|المدي الحقيقي|التذبذب/,'ATR · متوسط المدى الحقيقي','متوسط حجم الحركة في آخر 14 شمعة. يخبرك كم يتحرك السعر عادة، ويُستخدم لتحديد مسافة الوقف (1.5×ATR) والأهداف.'],
    [/(^| )ema|متوسط|التقاطع الذهبي/,'المتوسطات المتحركة EMA','متوسط 50 يعكس الاتجاه المتوسط، ومتوسط 200 الاتجاه الطويل. السعر فوق متوسط 50 إشارة إيجابية، وصعود متوسط 50 فوق 200 يسمى التقاطع الذهبي.'],
    [/poc|بروفايل|منطقه القيمه|السيوله/,'بروفايل الحجم و POC','يوزع الكميات المتداولة على مستويات السعر. POC هو السعر الذي تداولت عنده أكبر كمية، ومنطقة القيمة (VAH–VAL) تضم 70% من التداول، وغالبًا تعمل كمغناطيس للسعر.'],
    [/fvg|فجوه/,'الفجوة السعرية FVG','فراغ بين شمعة وأخرى بعد اندفاع قوي لم يتداول فيه السعر. كثيرًا ما يعود السعر لملئها قبل أن يكمل.'],
    [/(^| )ob( |$)|مناطق الاوامر|اوردر بلوك|order block/,'مناطق الأوامر OB','آخر شمعة معاكسة قبل اندفاع كسر آخر قمة أو قاع. يُفترض أن فيها أوامر كبيرة، وتعمل كدعم أو مقاومة عند العودة إليها. تحديدها في الموقع تقديري.'],
    [/دعم|مقاومه/,'الدعم والمقاومة','الدعم مستوى يتوقف عنده الهبوط عادة لكثرة المشترين، والمقاومة مستوى يتوقف عنده الصعود لكثرة البائعين. الإغلاق الواضح خلف أي منهما يعني كسره.'],
    [/مطرقه|شمعه|شموع|دوجي|ابتلاع/,'الشموع اليابانية','كل شمعة تلخص فترة: الافتتاح والإغلاق والأعلى والأدنى. المطرقة ذيلها السفلي طويل وتظهر بعد هبوط فتلمّح لانعكاس صاعد، والدوجي جسمها صغير ويعني تردد السوق. الشرح الكامل بالصور في تبويب «كيف أقرأ؟».'],
    [/توافق|نسبه/,'نسبة التوافق','متوسط مرجّح لاتجاه المؤشرات في خمسة أطر: الشهري 25% والأسبوعي 25% واليومي 20% و4 ساعات 15% والساعة 15%. ثم يُخصم 10 نقاط عن كل دليل معاكس. هي تقيس اتفاق المؤشرات، وليست احتمال ربح.'],
    [/انحراف|دايفرجنس|divergence/,'الانحراف','عندما يصنع السعر قمة أعلى بينما RSI يصنع قمة أدنى، فهذا انحراف سلبي يدل على ضعف الصعود. والعكس عند القيعان انحراف إيجابي.'],
    [/المنطقه|المستطيل|التوقع الاسبوعي/,'منطقة إغلاق الأسبوع','نطاق يُقدَّر قبل بداية كل أسبوع من تذبذب السعر الأخير. إذا أغلق الأسبوع داخله يُحسب التوقع صحيحًا، ويعرض الموقع سجل الإصابة بشفافية.']];

  /* ---------- formatting ---------- */
  const dp=p=>p>=1000?0:p>=100?1:p>=10?2:p>=1?3:p>=.1?4:5;
  const nf=(v,d)=>(v==null||!isFinite(v))?'—':Number(v).toLocaleString('en-US',{minimumFractionDigits:d,maximumFractionDigits:d});
  const unit=a=>a.pro==='sa'?'ريال':a.pro==='ix'?(a.unit||''):'دولار';
  const P=(v,a)=>{const s=`<b class="num">${nf(v,dp(Math.abs(v)))}${a&&unit(a)==='%'?'%':''}</b>`;return`<bdi class="pv">${a&&unit(a)&&unit(a)!=='%'?s+' '+unit(a):s}</bdi>`;};
  const DIR={up:'صاعد',down:'هابط',flat:'محايد'},TFN={'1M':'الشهري','1w':'الأسبوعي','1d':'اليومي','4h':'4 ساعات','1h':'الساعة'};
  const BIAS={up:'صعود',down:'هبوط',flat:'حياد'};
  const refOf=a=>({kind:a.pro,id:a.id,name:a.name,unit:a.unit||'',code:a.code||''});
  const meter=(conf,eff)=>{const c=conf.dir==='up'?'up':conf.dir==='down'?'down':'flat';
    return`<div class="bm"><div class="bm-bar"><i class="${c}" style="width:${Math.max(4,eff)}%"></i></div><span>اتجاه <b>${DIR[conf.dir]}</b> · توافق <b class="num">${conf.pct}%</b> · بعد التدقيق <b class="num">${eff}%</b></span></div>`;};
  const act=(label,q)=>`<button class="ba" data-q="${esc(q)}">${esc(label)}</button>`;
  const openBtn=(a,tab,label)=>`<button class="ba pr" data-open="${a.id}:${tab}">${esc(label)}</button>`;
  const DISC='<p class="bd">قراءة آلية للمؤشرات الفنية لغرض تعليمي، وليست توصية بالشراء أو البيع.</p>';
  const cache=new Map();
  async function an(a,tf){const k=a.id+':'+(tf||'1d'),c=cache.get(k);if(c&&Date.now()-c.t<5*60e3)return c.A;
    const A=await PRO.analyze(refOf(a),tf||'1d');if(A)cache.set(k,{A,t:Date.now()});return A;}
  const lastOf=A=>{const d=A.data['1d']||A.b,n=d.length-1;return{c:d[n].c,ch:n?(d[n].c/d[n-1].c-1)*100:0,t:d[n].t};};
  const day=t=>{const d=new Date(t*1000),M=['يناير','فبراير','مارس','أبريل','مايو','يونيو','يوليو','أغسطس','سبتمبر','أكتوبر','نوفمبر','ديسمبر'];return d.getUTCDate()+' '+M[d.getUTCMonth()];};

  /* ---------- answers ---------- */
  function head(a,A){const L=lastOf(A);
    return`<div class="bh2">${window.EMB?EMB.tag(a.id,26):''}<b>${esc(a.name)}</b><span class="tk">${esc(a.pro==='sa'?a.id:a.pro==='cx'?a.id+'/USDT':(a.code||a.id).split(' · ')[0])}</span></div>
      <p>آخر سعر ${P(L.c,a)} <span class="num ${L.ch>=0?'up':'down'}">${L.ch>=0?'+':''}${L.ch.toFixed(2)}%</span> <span class="mut">· ${day(L.t)}</span></p>`;}
  function scenTxt(a,A){const {sc}=A;
    if(sc.pick==='bull')return`<p><b>الأرجح حسب المؤشرات: الصعود.</b> يتأكد بإغلاق فوق ${P(sc.bull.trig,a)}، والهدف الأول ${P(sc.bull.t1,a)} ثم ${P(sc.bull.t2,a)}. تُلغى القراءة بإغلاق تحت ${P(sc.bull.inv,a)}.</p>`;
    if(sc.pick==='bear')return`<p><b>الأرجح حسب المؤشرات: الهبوط.</b> يتأكد بكسر ${P(sc.bear.trig,a)}، والهدف الأول ${P(sc.bear.t1,a)} ثم ${P(sc.bear.t2,a)}. تُلغى القراءة بإغلاق فوق ${P(sc.bear.inv,a)}.</p>`;
    return`<p><b>الأرجح حسب المؤشرات: تذبذب</b> بين ${P(sc.side.lo,a)} و ${P(sc.side.hi,a)} حتى يخرج السعر بإغلاق واضح. فوق ${P(sc.side.hi,a)} يفتح الطريق إلى ${P(sc.bull.t1,a)}، وتحت ${P(sc.side.lo,a)} إلى ${P(sc.bear.t1,a)}.</p>`;}
  function btTxt(A){const b=A.bt;if(!b||A.conf.dir==='flat')return'';const x=A.conf.dir==='up'?b.up:b.dn,base=A.conf.dir==='up'?b.base.pct:b.baseDown;
    if(!x||x.pct==null||x.n<15)return'';const edge=x.pct-base;
    return`<p class="mut">تاريخيًا على الشموع اليومية: عندما كانت المؤشرات ${DIR[A.conf.dir]}ة بقوة، ${A.conf.dir==='up'?'ارتفع':'انخفض'} السعر بعد ${b.h} أيام في <b class="num">${x.pct}%</b> من ${x.n} حالة، مقابل ${base}% في الأيام العادية${edge<5?'، أي أن أفضلية الإشارة هنا ضعيفة':''}.</p>`;}
  function weeklyTxt(a,A){const w=API().weekly(a.id);if(!w||!w.cur){let z=null;try{z=A&&PRO.weekZone(A.data['1d'],a.pro);}catch(_){}return z?`<div class="bw"><span>توقع إغلاق الأسبوع</span><b>بين ${nf(z.lo,dp(z.lo))} و ${nf(z.hi,dp(z.hi))}</b><small>${z.hit!=null?`أصابت الطريقة ${z.hit}% من الأسابيع على هذا الأصل`:''}</small></div>`:'';}
    return`<div class="bw"><span>توقع إغلاق الأسبوع (${esc(w.end)})</span><b>بين ${esc(w.cur.low!=null?w.fmt(w.cur.low):'—')} و ${esc(w.fmt(w.cur.high))}</b><small>الميل: ${BIAS[w.cur.bias]||'—'} · أصابت الطريقة ${w.hits} من ${w.n} أسبوعًا في الاختبار</small></div>`;}
  async function brief(a,tf,mode){const A=await an(a,tf);if(!A)return fail(a);
    const {conf,sc,au,scores}=A,cur=scores[A.tf];
    let h=head(a,A)+meter(conf,sc.eff);
    if(mode==='act')h=`<p>لا أقدّم توصيات شراء أو بيع، لكن هذا ما تقوله المؤشرات الآن عن <b>${esc(a.name)}</b>، والقرار لك:</p>`+h;
    if(A.tf!=='1d')h+=`<p class="mut">القراءة على إطار ${TFN[A.tf]}.</p>`;
    h+=scenTxt(a,A);
    if(cur&&cur.rsi!=null)h+=`<p>RSI ${TFN[A.tf]} <b class="num">${cur.rsi.toFixed(0)}</b>${cur.rsi>70?' (تشبع شراء)':cur.rsi<30?' (تشبع بيع)':''} · MACD ${cur.hist>0?'موجب':'سالب'} · ${conf.agree} من ${conf.total} أطر تتفق على الاتجاه.</p>`;
    if(au.length)h+=`<div class="bx"><span>ما يعاكس هذه القراءة</span><ul>${au.slice(0,3).map(x=>`<li>${x}</li>`).join('')}</ul></div>`;
    h+=btTxt(A)+weeklyTxt(a,A);
    if(window.NEWSAI){try{const nw=await NEWSAI.forAsset(a.id);if(nw.n){const v=NEWSAI.verdict(A.conf,nw);h+=`<div class="bw"><span>قراءة الأخبار: ${NEWSAI.LAB[nw.label]} (${nw.n} خبر)</span><small>${v.txt}</small></div>`;}}catch(_){}}
    h+=`<div class="bas">${act('وين أشتري ووين أبيع؟','وين اشتري ووين ابيع '+a.name)}${act('فهّمني الوضع','وش الوضع '+a.name)}${openBtn(a,'pro','التحليل الكامل')}${act('الدعم والمقاومة','دعم ومقاومة '+a.name)}${a.weekly?act('إغلاق الأسبوع','إغلاق '+a.name+' هذا الأسبوع'):act('النطاق الأسبوعي','نطاق '+a.name+' الأسبوع')}${A.tf!=='4h'&&A.data['4h']?act('إطار 4 ساعات',a.name+' 4 ساعات'):''}</div>`;
    return h+DISC;}
  async function levels(a,tf){const A=await an(a,tf);if(!A)return fail(a);const {lv,vp,I,b}=A,n=b.length-1;
    const row=(k,x)=>x?`<li><span>${k} · ${esc(x.src)}</span>${P(x.p,a)}</li>`:'';
    let h=head(a,A)+`<ul class="bk">${row('مقاومة ثانية',lv.R2)}${row('المقاومة الأقرب',lv.R)}<li class="now"><span>السعر الآن</span>${P(lastOf(A).c,a)}</li>${row('الدعم الأقرب',lv.S)}${row('دعم ثانٍ',lv.S2)}</ul>`;
    if(vp)h+=`<p>السيولة الأكبر (POC) عند ${P(vp.poc,a)}، ومنطقة القيمة بين ${P(vp.val,a)} و ${P(vp.vah,a)}.</p>`;
    if(I.atr[n])h+=`<p class="mut">الحركة المعتادة لكل شمعة ${TFN[A.tf]} نحو ${P(I.atr[n],a)} (ATR).</p>`;
    return h+`<div class="bas">${openBtn(a,'pro','افتح الشارت')}${act('الأهداف','أهداف '+a.name)}</div>`+DISC;}
  async function targets(a,tf){const A=await an(a,tf);if(!A)return fail(a);const {sc}=A;
    return head(a,A)+`<ul class="bk"><li><span>إذا أغلق فوق ${nf(sc.bull.trig,dp(sc.bull.trig))}</span>${P(sc.bull.t1,a)} ثم ${P(sc.bull.t2,a)}</li>
      <li><span>إذا كسر ${nf(sc.bear.trig,dp(sc.bear.trig))}</span>${P(sc.bear.t1,a)} ثم ${P(sc.bear.t2,a)}</li>
      <li><span>صدمة مفاجئة (3×ATR)</span>${P(sc.bear.shock,a)}</li></ul>`+scenTxt(a,A)+`<p class="mut">الأهداف مسافات محسوبة بالتذبذب (ATR) من مستويات الدعم والمقاومة، وليست وعدًا بالوصول.</p>`+DISC;}
  async function momentum(a){const A=await an(a,'1d');if(!A)return fail(a);const {scores,div}=A;
    const rows=['1M','1w','1d','4h','1h'].filter(t=>scores[t]).map(t=>{const x=scores[t];return`<li><span>${TFN[t]}</span><b class="${x.dir}">${DIR[x.dir]}</b> · RSI <b class="num">${x.rsi!=null?x.rsi.toFixed(0):'—'}</b> · MACD ${x.hist>0?'موجب':'سالب'}</li>`;}).join('');
    return head(a,A)+`<ul class="bk">${rows}</ul>`+(div.length?`<div class="bx"><span>انحرافات على اليومي</span><ul>${div.map(d=>`<li>${d.txt}</li>`).join('')}</ul></div>`:'<p class="mut">لا يوجد انحراف واضح على اليومي في آخر 80 شمعة.</p>')+DISC;}
  async function weekly(a){const w=API().weekly(a.id);
    if(w&&w.cur){let h=`<div class="bh2"><b>${esc(a.name)}</b><span class="tk">${esc(a.id)}</span></div>
      <p>آخر إغلاق <b class="num">${esc(w.fmt(w.last))}</b> <span class="mut">· ${esc(w.lastDay)}</span></p>
      <div class="bw"><span>المنطقة المتوقعة لإغلاق الأسبوع (${esc(w.end)})</span><b>بين ${esc(w.fmt(w.cur.low))} و ${esc(w.fmt(w.cur.high))}</b><small>الميل: ${BIAS[w.cur.bias]||'—'}</small></div>`;
      const pos=w.last>w.cur.high?'فوق المنطقة، وليصدق التوقع يجب أن ينزل ويغلق داخلها':w.last<w.cur.low?'تحت المنطقة، وليصدق التوقع يجب أن يرتفع ويغلق داخلها':'داخل المنطقة الآن';
      h+=`<p>السعر ${pos}.</p><p class="mut">طُبّقت الطريقة على آخر ${w.n} أسبوعًا فأغلق ${w.hits} منها داخل المنطقة (${w.n?Math.round(w.hits/w.n*10):0} من كل 10).</p>`;
      if(w.next)h+=`<p class="mut">الأسبوع التالي (${esc(w.nextEnd)})${w.next.provisional?' · مبدئي':''}: بين ${esc(w.fmt(w.next.low))} و ${esc(w.fmt(w.next.high))}.</p>`;
      return h+`<div class="bas">${openBtn(a,'now','افتح الرسم')}${act('الاتجاه العام','توقع '+a.name)}</div>`+DISC;}
    const A=await an(a,'1w');if(!A)return fail(a);const wb=A.data['1w'],at=QE.atr(wb),n=wb.length-1,c=lastOf(A).c,x=at[n];
    if(!x)return brief(a,'1w');
    return head(a,A)+`<p>لا يوجد لهذا الأصل توقع أسبوعي رسمي في الموقع. تقدير من تذبذبه المعتاد: الحركة الأسبوعية المعتادة نحو ${P(x,a)}، أي أن نطاقًا معقولًا للأسبوع بين ${P(c-x,a)} و ${P(c+x,a)}.</p>`+meter(A.conf,A.sc.eff)+scenTxt(a,A)+`<p class="mut">هذا نطاق تقديري من ATR الأسبوعي وليس توقعًا مختبرًا.</p>`+DISC;}
  async function news(a){if(window.NEWSAI){try{const nw=await NEWSAI.forAsset(a.id);if(nw.n){const A=await an(a,'1d');return`<div class="bh2"><b>${esc(a.name)}</b></div>`+NEWSAI.html(nw,A?A.conf:null,{max:5})+`<div class="bas">${openBtn(a,'news','كل الأخبار')}${act('التحليل الآن','توقع '+a.name)}</div>`;}}catch(_){}}
    const it=API().news(a.id);
    if(!it.length)return`<p>لا توجد أخبار محفوظة عن <b>${esc(a.name)}</b> في الموقع حاليًا.</p><div class="bas">${act('التحليل الآن','توقع '+a.name)}</div>`;
    return`<p>آخر أخبار <b>${esc(a.name)}</b>:</p><ul class="bn">${it.map(n=>`<li><a href="${esc(n.u)}" target="_blank" rel="noopener noreferrer">${esc(n.t)}</a><small>${esc(n.d)} · ${esc(n.s)}</small></li>`).join('')}</ul><div class="bas">${openBtn(a,'news','كل الأخبار')}</div>`;}
  async function compare(ids){const L=ids.slice(0,3).map(i=>BY[i]),R=await Promise.all(L.map(a=>an(a,'1d')));
    if(R.some(x=>!x))return'<p>تعذر جلب بيانات أحد الأصلين الآن. حاول بعد قليل.</p>';
    const sg=A=>(A.conf.dir==='up'?1:A.conf.dir==='down'?-1:0)*A.sc.eff;
    const pick={bull:'صعود',bear:'هبوط',side:'تذبذب'};
    let h=`<div class="bt"><table><thead><tr><th></th>${L.map(a=>`<th>${esc(a.btn||a.name)}</th>`).join('')}</tr></thead><tbody>
      <tr><td>التغير اليومي</td>${R.map(A=>{const x=lastOf(A).ch;return`<td class="num ${x>=0?'up':'down'}">${x>=0?'+':''}${x.toFixed(2)}%</td>`;}).join('')}</tr>
      <tr><td>الاتجاه</td>${R.map(A=>`<td class="${A.conf.dir}">${DIR[A.conf.dir]}</td>`).join('')}</tr>
      <tr><td>التوافق</td>${R.map(A=>`<td class="num">${A.conf.pct}%</td>`).join('')}</tr>
      <tr><td>بعد التدقيق</td>${R.map(A=>`<td class="num">${A.sc.eff}%</td>`).join('')}</tr>
      <tr><td>RSI اليومي</td>${R.map(A=>`<td class="num">${A.scores['1d']&&A.scores['1d'].rsi!=null?A.scores['1d'].rsi.toFixed(0):'—'}</td>`).join('')}</tr>
      <tr><td>الأرجح</td>${R.map(A=>`<td>${pick[A.sc.pick]}</td>`).join('')}</tr>
      <tr><td>أدلة معاكسة</td>${R.map(A=>`<td class="num">${A.au.length}</td>`).join('')}</tr></tbody></table></div>`;
    const best=L.map((a,i)=>({a,s:sg(R[i])})).sort((x,y)=>y.s-x.s);
    h+=best[0].s-best[best.length-1].s<10?'<p>القراءتان متقاربتان ولا تميّز المؤشرات أحدهما بوضوح.</p>':`<p>قراءة المؤشرات أفضل نسبيًا في <b>${esc(best[0].a.name)}</b>${best[0].s<0?' (ضغط هابط أخف)':''}، وأضعف في <b>${esc(best[best.length-1].a.name)}</b>.</p>`;
    return h+`<div class="bas">${L.map(a=>act(a.btn||a.name,'توقع '+a.name)).join('')}</div>`+DISC;}
  const CATW=[['sa',/(سعودي|السعوديه|تداول|الاسهم السعوديه)/],['cx',/(عمل|كريبتو|مشفر|رقمي)/],['us',/(امريك|الامريكيه|عالمي)/],['ix',/(مؤشر|سلع|معادن)/]];
  async function rank(t,el){const cat=(CATW.find(([,r])=>r.test(t))||[])[0];const L=AS.filter(a=>!cat||a.pro===cat);
    let done=0;const out=[];const tick=()=>{if(el)el.innerHTML=`<p class="mut">أفحص ${L.length} أصلًا… <b class="num">${done}</b> / ${L.length}</p>`;};tick();
    const q=L.slice();await Promise.all([0,1,2,3,4].map(async()=>{while(q.length){const a=q.shift();const A=await an(a,'1d').catch(()=>null);done++;tick();if(A)out.push({a,A,s:(A.conf.dir==='up'?1:A.conf.dir==='down'?-1:0)*A.sc.eff});}}));
    if(!out.length)return'<p>تعذر جلب البيانات الآن. حاول بعد قليل.</p>';
    out.sort((x,y)=>y.s-x.s);const weak=/(اضعف|اسوا)/.test(t);
    const li=x=>`<li><button class="ba bq" data-q="${esc('توقع '+x.a.name)}">${esc(x.a.name)}</button><span class="${x.A.conf.dir}">${DIR[x.A.conf.dir]}</span><b class="num">${x.A.sc.eff}%</b></li>`;
    const top=out.filter(x=>x.s>0).slice(0,5),bot=out.filter(x=>x.s<0).reverse().slice(0,5);
    let h=`<p>ترتيب ${cat?{sa:'الأسهم السعودية',cx:'العملات المشفرة',us:'الأسهم الأمريكية',ix:'المؤشرات والسلع'}[cat]:'كل الأصول'} حسب قوة المؤشرات بعد التدقيق المعاكس:</p>`;
    const up=`<div class="br"><span>الأقوى صعودًا</span><ul>${top.map(li).join('')||'<li class="mut">لا يوجد أصل بتوافق صاعد الآن</li>'}</ul></div>`;
    const dn=`<div class="br"><span>الأقوى هبوطًا</span><ul>${bot.map(li).join('')||'<li class="mut">لا يوجد أصل بتوافق هابط الآن</li>'}</ul></div>`;
    h+=weak?dn+up:up+dn;
    return h+`<p class="mut">الترتيب يقيس اتفاق المؤشرات فقط، ولا يعني أن الأصل الأول سيربح أكثر.</p>`+DISC;}
  function listAll(){const g={sa:'السوق السعودي',cx:'العملات المشفرة',us:'الأسهم الأمريكية',ix:'المؤشرات والسلع'};
    return'<p>أحلل كل الأصول الموجودة في الموقع:</p>'+Object.entries(g).map(([k,v])=>`<div class="bl"><span>${v}</span><div>${AS.filter(a=>a.pro===k).map(a=>`<button class="ba" data-q="${esc('توقع '+a.name)}">${esc(a.btn||a.name)}</button>`).join('')}</div></div>`).join('');}
  const fail=a=>`<p>تعذر الوصول إلى بيانات <b>${esc(a.name)}</b> الآن. حاول بعد قليل.</p>`;
  const WELCOME=()=>{const c=BY[API().current()];
    return`<p>أهلًا بك 👋 أنا السلحفاة الذكية، مساعدك في التحليل. تكلّم معي بطريقتك: «وش وضع أرامكو؟»، «وين أشتري البيتكوين؟»، «ليش؟»، «ولو نزل؟»، أو «وين ألقى المكعب؟».</p><p>اسألني عن أي سهم أو عملة أو مؤشر في الموقع، وأرد فورًا من آخر البيانات: الاتجاه، والدعم والمقاومة، والأهداف، وإغلاق الأسبوع، والمقارنة بين أصلين.</p>
      <div class="bas">${c?act('توقع '+(c.btn||c.name),'توقع '+c.name):''}${act('الذهب هذا الأسبوع','الذهب هذا الأسبوع')}${act('أقوى الأصول الآن','أقوى الأصول الآن')}${act('قارن البيتكوين والإيثريوم','قارن البيتكوين والإيثريوم')}${act('ما هو RSI؟','ما هو RSI؟')}</div>`;};
  const MORE=()=>`<div class="bas">${act('عرض الأصول المتاحة','وش الأصول المتاحة')}${act('أقوى الأصول الآن','أقوى الأصول الآن')}</div>`;
  const POLICY='<p class="bpol">حفاظًا على دقة المعلومات وحماية حقوق المحتوى، يقتصر نطاق المساعد على الأصول والتحليلات المنشورة في المنصة، ولا يصل إلى أي مصادر خارجية.</p>';
  const UNAVAIL=n=>`<p>نعتذر، ${n?`«<b>${esc(n)}</b>»`:'الأصل المطلوب'} غير متوفر حاليًا ضمن الأصول المغطاة في منصة التحليل الخاص.</p>`+POLICY+MORE();
  const OUTSCOPE=()=>`<p>نعتذر، هذا الطلب خارج نطاق خدمة المساعد.</p><p>صُمّم المساعد للإجابة عن تحليلات الأسهم والعملات والمؤشرات المنشورة في المنصة فقط، ولا يقدّم معلومات عامة أو محتوى من خارجها، التزامًا بسياسة الاستخدام.</p>`+MORE();
  const NOTFOUND=()=>UNAVAIL('');
  const ABOUT=()=>`<p>أنا السلحفاة الذكية، مساعدك في التحليل، جزء من منصة <b>التحليل الخاص · شيبان</b>. أجيب من بيانات المنصة وتحليلاتها مباشرة.</p><p class="bpol">التفاصيل التقنية للمنصة ومصادرها الداخلية محمية بحقوق الملكية ولا يُفصح عنها.</p>`+MORE();
  const STOP=new Set('اكتب قصيده قصيدة شعر نكته طقس ترجم اغنيه وصفه قصه وش ايش شو ما ماذا هل كم كيف متي وين اين ليش لماذا في عن من الي علي مع او ثم هو هي له لها فيه فيها هذا هذه ذا الحين الان اليوم بكره غدا رايك رايكم توقعك توقعاتك توقع تتوقع تحليل حلل اتجاه سعر اسعار سهم اسهم عمله عملات عملة شركه مؤشر اسبوع شهر يا انت ابي ابغي اريد عطني اعطني ممكن لو سمحت طيب يطلع ينزل يرتفع ينخفض صعود هبوط حركه السوق قيمه كوين حالي قادم جاي بعد قبل شراء بيع اشتري ابيع ادخل هدف اهداف دعم مقاومه وضع الوضع كذا زين يستاهل تنصح تنصحني نصيحه اخبار خبر مستقبل ايضا كمان بس'.split(' '));
  const MK=/(توقع|سهم|اسهم|عمله|عملات|كوين|سعر|اسعار|اتجاه|تحليل|حلل|شراء|بيع|اشتري|ابيع|يطلع|ينزل|صعود|هبوط|مقاوم|هدف|تداول|استثمار|شارت|chart|token|توكن)/;
  const WHO=/(من صنعك|من برمجك|من سواك|من طورك|وش النموذج|ايش النموذج|اي نموذج|من انت|مين انت|هل انت|ذكاء اصطناعي|الذكاء الاصطناعي|بوت مين|انت بوت|كيف برمجت|كيف تشتغل|مصدر بياناتك|من وين تجيب)/;
  function candidate(q,t){const toks=t.split(' ').filter(w=>{if(w.length<2)return false;const b=w.replace(/^(و|ف|ب|ل|ك)?(ال)?/,'');return !STOP.has(w)&&!STOP.has(b)&&!STOP.has(w.replace(/^ال/,''))&&!/^\d+$/.test(w)&&!Object.values(I).some(r=>r.test(w))&&!TFR.some(([,r])=>r.test(w));});
    if(!toks.length)return'';const c=toks[0];const orig=String(q).split(/\s+/).find(w=>norm(w)===c);return(orig||c).replace(/[؟?!.,،]+$/,'');}

  /* ---------- site guide: answers questions about where things are in the site ---------- */
  const SITE=[
    [/(المكعب|سجل الصفقات|الصفقات|المحفظه|محفظه الارباح|راس المال)/,'سجل الصفقات (المكعب)','المكعب الذهبي أسفل الصفحة الرئيسية. اضغطه واكتب الرمز السري لترى محفظة رأس المال ومحفظة الأرباح وجدول الصفقات المفتوحة والمغلقة، ويمكنك تنزيل الشيت منه.','cube'],
    [/(تريدنج|تيكودينغ|تيكو دينغ|تيكودنق|المنصه|الشارت الكامل|شارت متقدم|منصه التداول|ارسم|الرسم|ادوات الرسم)/,'منصة تيكودينغ شارت','الصندوق فوق المكعب يفتح منصة «تيكودينغ شارت» بملء الشاشة. فيها الفريمات من الساعة إلى الشهري، وأدوات الرسم (خط الدعم والمقاومة، فيبوناتشي، الفرشاة…)، وأزرار المؤشرات المضيئة، وزر التراجع ↶.','tv'],
    [/(فيبو|فايبو|فيبوناتشي|فايبوناتشي)/,'فيبوناتشي','في تيكودينغ شارت: اضغط زر القلم لإظهار الأدوات، اختر فيبوناتشي، ثم اضغط على القاع واسحب إلى القمة. تظهر القمم والقيعان مرقّمة لتلتصق بها. لحذفه: المسه مرة ثم اضغط سلة المهملات، والتراجع ↶ يعيده.','tv'],
    [/(تراجع|الغاء|undo|حذف الخط|احذف|امسح)/,'التراجع والحذف','زر ↶ في الشريط العلوي لتيكودينغ شارت يرجع آخر خطوة. لحذف أي رسم: المسه مرة لتحديده ثم اضغط سلة المهملات في الشريط السفلي.','tv'],
    [/(المؤشرات|مؤشر rsi|ازرار|اظهر rsi|اخفي|شارت صافي)/,'إظهار المؤشرات','في تيكودينغ شارت شريط أزرار مضيئة تحت الشريط العلوي: اضغط RSI أو MACD أو غيرها لتظهر فورًا، واضغط مرة ثانية لإخفائها. زر «شارت صافٍ» يخفي الكل.','tv'],
    [/(التوقع الاسبوعي|اغلاق الاسبوع|التوقعات الاسبوعيه|الاختبار الرجعي|دقه التوقع|نسبه الصواب|دقه)/,'التوقعات الأسبوعية','لكل أصل توقع لإغلاق الأسبوع في صفحته ضمن «التحليل المتقدم»، ومعه نسبة إصابته الفعلية، وجدول اختبار رجعي منذ مارس 2025 يقارن كل أسبوع بالإغلاق الحقيقي.',null],
    [/(كيف اقرا|كيف افهم|المؤشر الدائري|الاطر|نقاط الاطر|بعد التدقيق|التوافق)/,'كيف تقرأ التحليل','المؤشر الدائري = نسبة اتفاق المؤشرات على الاتجاه (فوق 60% واضح، قرب 50% حيرة). نقاط الأطر: أخضر صاعد وأحمر هابط. «بعد التدقيق» = النسبة بعد خصم الأدلة المعاكسة، وكلما قلّت ضعفت الثقة.',null],
    [/(الاخبار|وين الاخبار|قراءه الاخبار)/,'الأخبار','في صفحة كل أصل تبويب «الأخبار» مع قراءة آلية: إيجابية أو سلبية أو محايدة، ومقارنتها بقراءة الأرقام. وفي تيكودينغ شارت تبويب «الأخبار» في اللوحة الجانبية.',null],
    [/(كيف استخدم الموقع|وش في الموقع|ايش في الموقع|اقسام الموقع|الموقع فيه|وين القوائم)/,'أقسام الموقع','اختر الأصل من القائمة أعلى الصفحة، ثم تنقّل بين التبويبات: الآن، التحليل المتقدم، الأسابيع، الأخبار. تحتها منصة «تيكودينغ شارت» للشارت الكامل، ثم المكعب لسجل الصفقات، وأنا هنا في الزاوية للأسئلة.',null]];
  const siteHit=t=>SITE.find(([r])=>r.test(t));
  const siteAns=x=>`<div class="bh2"><b>${x[1]}</b></div><p>${x[2]}</p><div class="bas">${x[3]==='cube'?'<button class="ba pr" data-go="cube">افتح المكعب</button>':x[3]==='tv'?`<button class="ba pr" data-go="tv">افتح تيكودينغ شارت</button>`:''}${act('كيف أقرأ التحليل','كيف اقرا التحليل')}</div>`;

  /* ---------- educational trade plan: where a technical trader would look to buy / sell ---------- */
  /* ---------- the professor plan: top-down levels + final audit (rules from pro/rules.json) ---------- */
  let RULES=null,EVTS=null;const RAWB='https://raw.githubusercontent.com/shaibanor/Wave/main/';
  async function rules(){if(RULES)return RULES;RULES={min_rr:2,stop_buffer_atr:.25,min_room_r:1,cap:6,stop_atr:1.2,min_risk_atr:.75,max_risk_atr:3,wick:.5};
    for(const b of [RAWB,'']){try{const r=await fetch(b+'pro/rules.json?v='+Math.floor(Date.now()/36e5));if(r.ok){const j=await r.json(),h=j.horizons.D;
      Object.assign(RULES,{mode:j.mode,roll:j.rolling,min_rr:j.auditor.min_rr,stop_buffer_atr:j.levels.stop_buffer_atr,min_room_r:j.levels.min_room_r,cap:h.target_cap_atr,stop_atr:h.stop_atr,min_risk_atr:h.min_risk_atr,max_risk_atr:h.max_risk_atr,wick:j.traps.failed_breakout_wick});break;}}catch(_){}}
    for(const b of [RAWB,'']){try{const r=await fetch(b+'pro/events.json?v='+Math.floor(Date.now()/36e5));if(r.ok){EVTS=(await r.json()).events||[];break;}}catch(_){}}return RULES;}
  function swingsOf(b,k){const H=[],L=[];if(!b)return{H,L};for(let i=k;i<b.length-k;i++){let h=true,l=true;for(let j=1;j<=k;j++){if(!(b[i-j].h<b[i].h&&b[i+j].h<=b[i].h))h=false;if(!(b[i-j].l>b[i].l&&b[i+j].l>=b[i].l))l=false;}if(h)H.push(b[i].h);if(l)L.push(b[i].l);}return{H,L};}
  async function planRoll(a){const RL=await rules(),O=RL.roll;const A=await an(a,'4h');if(!A||!A.data||!A.data['4h']||A.b.length<60)return null;
    const {I,b,scores}=A,n=b.length-1,L=b[n],c=L.c,atr=I.atr[n],e50=I.e50[n],rs=I.rsi[n];if(!atr||e50==null||rs==null)return null;
    const sD=scores['1d'],sW=scores['1w'],sM=scores['1M'];
    const sp=Math.min(Math.max(O.stop.atr_k*atr/c*100,O.stop.min_pct),O.stop.max_pct),stop=c*(1-sp/100),tgt=c*(1+O.target_pct/100),be=c*(1+O.breakeven_at_target_frac*O.target_pct/100);
    const sw=swingsOf(b.slice(-180),3),above=sw.H.filter(x=>x>c*1.0005),r1=above.length?Math.min(...above):null;
    const rg=Math.max(1e-12,L.h-L.l),uw=(L.h-Math.max(L.o,L.c))/rg,trap=sw.H.slice(-6).some(p=>L.h>p&&L.c<p)&&uw>=RL.wick;
    const today=new Date(),ev=(EVTS||[]).find(e=>{const d=(new Date(e.d+'T00:00:00Z')-Date.UTC(today.getUTCFullYear(),today.getUTCMonth(),today.getUTCDate()))/864e5;return d>=0&&d<=1&&(e.scope==='all'||e.scope===a.pro);});
    const sig=c>e50&&rs<O.trigger.rsi_below&&L.c>L.o;
    const ck=[
      ['السياق: الشهري والأسبوعي ليسا هابطين، واليومي صاعد',!!(sM&&sW&&sD)&&sM.dir!=='down'&&sW.dir!=='down'&&sD.dir==='up',`الشهري ${sM?DIR[sM.dir]:'—'}، الأسبوعي ${sW?DIR[sW.dir]:'—'}، اليومي ${sD?DIR[sD.dir]:'—'}`],
      ['لا مقاومة 4 ساعات قبل الهدف',!r1||r1>=tgt,r1?`أقرب مقاومة ${P(r1,a)} والهدف ${P(tgt,a)}`:'لا مقاومة قريبة'],
      ['الفخاخ والأخبار',!trap&&!ev,trap?'اختراق كاذب بذيل علوي':ev?`حدث كبير قريب: ${esc(ev.t)} ${esc(ev.d)}`:'لا فخ ظاهر · القرار لا يعتمد على الأخبار'],
      ['إشارة الدخول على 4 ساعات',sig,`السعر ${c>e50?'فوق':'تحت'} متوسط 50 · RSI ${rs.toFixed(0)} ${rs<O.trigger.rsi_below?'(تهدئة)':'(مرتفع)'} · الشمعة ${L.c>L.o?'خضراء':'حمراء'}`]];
    const ok=ck.every(x=>x[1]),need=(sp/(O.target_pct+sp)*100).toFixed(0);
    let h=head(a,A)+`<div class="pa"><div class="pa-h">التدقيق النهائي · 4 ساعات (صفقات متحركة)</div>${ck.map(([q,y,d])=>`<div class="pa-r ${y?'y':'n'}"><b>${y?'✓ نعم':'✗ لا'}</b><span>${q}</span><small>${d}</small></div>`).join('')}</div>`;
    h+=ok?`<p><b>القرار: الإعداد صالح تعليميًا الآن.</b></p>`:`<p><b>القرار: لا صفقة الآن.</b> أي «لا» تلغي القرار.</p>`;
    h+=`<div class="bpl"><div class="bpl-r buy"><span>الدخول (إغلاق آخر شمعة 4 ساعات)</span>${P(c,a)}</div><div class="bpl-r sell"><span>الهدف (+${O.target_pct}%)</span>${P(tgt,a)}</div>
      <div class="bpl-r stop"><span>وقف الخسارة (−${sp.toFixed(1)}%)</span>${P(stop,a)}</div><div class="bpl-r rr"><span>نقل الوقف للتعادل عند</span>${P(be,a)}</div></div>
      <p class="mut">هذه الصفقة تربح فقط إذا نجحت ${need}% من المحاولات أو أكثر، لأن الوقف (${sp.toFixed(1)}%) أبعد من الهدف (${O.target_pct}%). البروفيسور في المكعب يقيس ذلك ويوقف الدخول إذا هبطت النسبة.</p>`;
    CTX.topic='plan';
    return h+`<div class="bas">${act('ليش هذي المستويات؟','ليش')}${act('ولو نزل؟','ولو نزل')}${openBtn(a,'pro','افتح الشارت')}</div>`+DISC;}
  async function plan(a,tf){const RL0=await rules();if(RL0.mode==='h4_rolling'&&RL0.roll&&(!tf||tf==='4h')){const r=await planRoll(a);if(r)return r;}
    const A=await an(a,tf);if(!A)return fail(a);const RL=await rules();const {lv,I,b,scores}=A,n=b.length-1,atr=I.atr[n],c=lastOf(A).c;
    if(!lv||!atr)return brief(a,tf);
    const D=A.data||{},sw=swingsOf(b.slice(-250),3),sW=swingsOf(D['1w']&&D['1w'].slice(-156),3),sM=swingsOf(D['1M']&&D['1M'].slice(-120),2);
    const sup=[...sw.L,...sW.L].filter(x=>x&&x<c-.3*atr).sort((x,y)=>y-x);
    const res=[...sw.H,...sW.H,...sM.H].filter(x=>x&&x>c*1.0005).sort((x,y)=>x-y);
    const m=scores['1M'],w=scores['1w'];
    // levels
    let S1=sup[0]||null,stop=S1?S1-RL.stop_buffer_atr*atr:c-RL.stop_atr*atr,risk=c-stop;if(risk<RL.min_risk_atr*atr){stop=c-RL.stop_atr*atr;risk=c-stop;}
    const R1=res[0]||null,cap=c+RL.cap*atr,within=res.filter(x=>x<=cap);let tgt=within.length?Math.max(...within)-.1*atr:cap;if(tgt<=c)tgt=cap;
    const rr=(tgt-c)/Math.max(1e-9,risk);
    // traps
    const L=b[n],rg=Math.max(1e-12,L.h-L.l),uw=(L.h-Math.max(L.o,L.c))/rg,prevH=sw.H.slice(-6),prevL=sw.L.slice(-6);
    const trap=prevH.some(p=>L.h>p&&L.c<p)&&uw>=RL.wick,sweep=prevL.some(p=>L.l<p&&L.c>p);
    const today=new Date(),ev=(EVTS||[]).find(e=>{const d=(new Date(e.d+'T00:00:00Z')-Date.UTC(today.getUTCFullYear(),today.getUTCMonth(),today.getUTCDate()))/864e5;return d>=0&&d<=1&&(e.scope==='all'||e.scope===a.pro);});
    const ck=[
      ['الشهري والمسار التاريخي',!!m&&m.dir!=='down'&&!(w&&w.dir==='down'),m?`الشهري ${DIR[m.dir]}${w?`، الأسبوعي ${DIR[w.dir]}`:''}${m.dir==='down'?' · لا شراء عكس الشهري':w&&w.dir==='down'?' · الأسبوعي هابط':''}`:'لا يوجد شهري كافٍ'],
      ['الدعم والمقاومة والسيولة',(!R1||R1-c>=RL.min_room_r*risk)&&risk<=RL.max_risk_atr*atr,`الدعم ${S1?P(S1,a):'—'} · أول مقاومة ${R1?P(R1,a):'لا توجد (قمة تاريخية)'}${R1&&R1-c<RL.min_room_r*risk?' · المقاومة أقرب من مسافة الوقف':''}`],
      ['الفخاخ والأخبار',!trap&&!ev,trap?'اختراق كاذب: ذيل علوي فوق قمة سابقة وإغلاق تحتها':ev?`حدث كبير قريب: ${esc(ev.t)} ${esc(ev.d)}`:(sweep?'لا فخ · سحب سيولة تحت قاع سابق ثم عودة (إيجابي)':'لا فخ ظاهر · القرار لا يعتمد على الأخبار')],
      [`العائد إلى المخاطرة 1:${RL.min_rr} أو أعلى`,rr>=RL.min_rr,`1:${rr.toFixed(2)}`]];
    const ok=ck.every(x=>x[1]);
    let h=head(a,A)+`<div class="pa"><div class="pa-h">التدقيق النهائي · ${TFN[tf||'1d']||'اليومي'}</div>${ck.map(([q,y,d])=>`<div class="pa-r ${y?'y':'n'}"><b>${y?'✓ نعم':'✗ لا'}</b><span>${q}</span><small>${d}</small></div>`).join('')}</div>`;
    if(ok){h+=`<p><b>القرار: الخطة صالحة تعليميًا.</b></p><div class="bpl"><div class="bpl-r buy"><span>الدخول (السعر الحالي)</span>${P(c,a)}</div>
      <div class="bpl-r stop"><span>وقف الخسارة (تحت الدعم بربع ATR)</span>${P(stop,a)}</div>
      <div class="bpl-r sell"><span>الهدف (أعلى مقاومة قوية في المتناول)</span>${P(tgt,a)}</div>
      <div class="bpl-r rr"><span>العائد إلى المخاطرة</span><b class="num">1 : ${rr.toFixed(2)}</b></div></div>
      <p class="mut">عند ربح يساوي مسافة الوقف (${P(c+risk,a)}) يُنقل الوقف إلى سعر الدخول. تُلغى الفكرة بإغلاق تحت ${P(stop,a)}.</p>`;}
    else{const ePx=(tgt+RL.min_rr*stop)/(1+RL.min_rr);
      h+=`<p><b>القرار: لا صفقة الآن.</b> فشل ${ck.filter(x=>!x[1]).length} من 4 شروط، والقاعدة: أي «لا» تلغي القرار.</p>`;
      if(ck[3][1]===false&&ck[0][1]&&ePx>stop&&ePx<c)h+=`<p class="mut">ليصبح العائد 1:${RL.min_rr} بنفس الوقف والهدف، يلزم دخول عند ${P(ePx,a)} أو أقل.</p>`;
      if(!ck[0][1]&&sc_bull(A))h+=`<p class="mut">بديل: انتظار إغلاق فوق ${P(A.sc.bull.trig,a)} يؤكد تغيّر الاتجاه، ثم إعادة التدقيق.</p>`;}
    CTX.topic='plan';
    return h+`<div class="bas">${act('ليش هذي المستويات؟','ليش')}${act('ولو نزل؟','ولو نزل')}${act('ولو طلع؟','ولو طلع')}${openBtn(a,'pro','افتح الشارت')}</div>`+DISC;}
  const sc_bull=A=>A.sc&&A.sc.bull&&A.sc.bull.trig;
  async function situation(a,tf){const A=await an(a,tf);if(!A)return fail(a);const {lv,I,b,conf,sc,scores}=A,n=b.length-1,atr=I.atr[n],c=lastOf(A).c;
    const tr=conf.dir==='up'?'صاعد':conf.dir==='down'?'هابط':'متذبذب بلا اتجاه واضح';
    const agree=['1M','1w','1d'].filter(t=>scores[t]).map(t=>`${TFN[t]} ${DIR[scores[t].dir]}`).join('، ');
    let pos='';if(lv&&lv.S&&lv.R){const span=lv.R.p-lv.S.p,f=span>0?(c-lv.S.p)/span:.5;pos=f<.25?'قريب من الدعم':f>.75?'قريب من المقاومة':'في منتصف المسافة بين الدعم والمقاومة';}
    let h=head(a,A)+`<p>باختصار: <b>${esc(a.name)}</b> في اتجاه <b>${tr}</b> (${agree}).</p>`;
    if(pos)h+=`<p>السعر الآن ${pos}: الدعم ${P(lv.S.p,a)} والمقاومة ${P(lv.R.p,a)}.</p>`;
    if(atr)h+=`<p>يتحرك عادةً نحو ${P(atr,a)} في اليوم، فلا تستغرب حركة بهذا الحجم.</p>`;
    let z=null;try{z=PRO.weekZone(A.data['1d'],a.pro);}catch(_){}
    if(z)h+=`<p>والتوقع لإغلاق هذا الأسبوع بين ${P(z.lo,a)} و ${P(z.hi,a)}${z.hit!=null?` (أصابت هذه الطريقة ${z.hit}% من الأسابيع على هذا الأصل)`:''}.</p>`;
    h+=scenTxt(a,A);CTX.topic='sit';
    return h+`<div class="bas">${act('وين أشتري ووين أبيع؟','وين اشتري ووين ابيع')}${act('ليش؟','ليش')}${act('الدعم والمقاومة','دعم ومقاومة')}</div>`+DISC;}
  async function why(a,tf){const A=await an(a,tf);if(!A)return fail(a);const {scores,au,conf,lv}=A;
    const rows=['1M','1w','1d','4h'].filter(t=>scores[t]).map(t=>{const x=scores[t];return`<li><span>${TFN[t]}</span><b class="${x.dir}">${DIR[x.dir]}</b>${x.rsi!=null?` · RSI ${x.rsi.toFixed(0)}`:''} · MACD ${x.hist>0?'موجب':'سالب'}</li>`;}).join('');
    let h=`<p>أبني القراءة على اتفاق المؤشرات في عدة أطر زمنية. هذه أسباب قراءة <b>${esc(a.name)}</b>:</p><ul class="bk">${rows}</ul>`;
    h+=`<p>النتيجة: ${conf.agree} من ${conf.total} أطر تتفق، والتوافق ${conf.pct}%.</p>`;
    if(lv&&lv.S)h+=`<p>المستويات تأتي من أماكن ارتد منها السعر سابقًا: الدعم ${P(lv.S.p,a)} (${esc(lv.S.src)})، والمقاومة ${P(lv.R.p,a)} (${esc(lv.R.src)}). ووقف الخسارة يوضع تحت الدعم بمسافة تذبذب يومي (ATR) حتى لا تخرجك حركة عادية.</p>`;
    if(au.length)h+=`<div class="bx"><span>وما يعاكس القراءة</span><ul>${au.slice(0,3).map(x=>`<li>${x}</li>`).join('')}</ul></div>`;
    return h+`<div class="bas">${act('وش يعني RSI؟','وش يعني rsi')}${act('وش يعني ATR؟','وش يعني atr')}${act('وين أشتري؟','وين اشتري')}</div>`;}
  async function ifMove(a,tf,up){const A=await an(a,tf);if(!A)return fail(a);const {sc}=A;
    const h=up?`<p><b>لو طلع ${esc(a.name)}:</b> الإشارة المهمة إغلاق فوق ${P(sc.bull.trig,a)}. عندها يُتوقع الوصول إلى ${P(sc.bull.t1,a)} ثم ${P(sc.bull.t2,a)}، وتفشل الفكرة إذا رجع وأغلق تحت ${P(sc.bull.inv,a)}.</p><p class="mut">نصيحة تعليمية: الاختراق الحقيقي يكون بإغلاق شمعة كاملة فوق المستوى، لا بلمسه فقط.</p>`
      :`<p><b>لو نزل ${esc(a.name)}:</b> المستوى الحاسم ${P(sc.bear.trig,a)}. كسره بإغلاق يفتح الطريق إلى ${P(sc.bear.t1,a)} ثم ${P(sc.bear.t2,a)}، وفي صدمة مفاجئة قد يصل ${P(sc.bear.shock,a)}. يعود الأمل إذا أغلق فوق ${P(sc.bear.inv,a)}.</p><p class="mut">نصيحة تعليمية: هنا يفيد وقف الخسارة، فهو يحميك من الاستمرار في الهبوط.</p>`;
    return h+`<div class="bas">${act(up?'ولو نزل؟':'ولو طلع؟',up?'ولو نزل':'ولو طلع')}${act('وين أشتري؟','وين اشتري')}</div>`+DISC;}

  /* ---------- router ---------- */
  const CTX={last:null};
  async function answer(q,el){const t=norm(q);if(!t)return OUTSCOPE();
    const ids=findAssets(t),tf=tfOf(t);
    const follow=has(t,I.plan)||has(t,I.why)||has(t,I.bull)||has(t,I.bear)||has(t,I.sit)||(has(t,I.yes)&&t.split(' ').length<=3);
    if(!ids.length&&!follow){const sh=siteHit(t);if(sh&&!MK.test(t.replace(/(تحليل|شارت)/g,'')))return siteAns(sh);}
    if(!ids.length&&CTX.last&&follow){ids.push(CTX.last);}
    if(!ids.length&&follow&&!CTX.last)return`<p>عن أي أصل تقصد؟ اكتب اسمه، مثل: «وين أشتري أرامكو» أو «وش وضع البيتكوين».</p>`+MORE();
    const gl=GLOSS.find(([r])=>r.test(t));
    if(!ids.length){
      if(has(t,I.thanks))return'<p>العفو، في الخدمة دائمًا. اسأل متى شئت.</p>';
      if(WHO.test(t))return ABOUT();
      if(gl&&has(t,I.define))return`<div class="bh2"><b>${gl[1]}</b></div><p>${gl[2]}</p>`;
      if(has(t,I.rank))return rank(t,el);
      if(has(t,I.list))return listAll();
      if(has(t,I.greet)||has(t,I.help))return WELCOME();
      const cand=candidate(q,t),nt=t.split(' ').length;
      const after=(t.match(/(?:^| )(?:في|عن|بخصوص) (\S+)/)||[])[1];
      if(cand&&!gl&&(MK.test(t)||nt<=2||/[a-z]/.test(norm(cand))||(after&&norm(cand)===after&&/(رايك|تشوف|تنصح|توقع|وضع|اعرف|معلومات|تحليل)/.test(t))))return UNAVAIL(cand);
      if(CTX.last&&!cand&&(has(t,I.levels)||has(t,I.target)||has(t,I.mom)||has(t,I.weekly)||has(t,I.act)||has(t,I.news)||tf||/(وش رايك|طيب|وبعد|كمان|ايضا|و هو|وهو|له|لها)/.test(t)))ids.push(CTX.last);
      else if(gl)return`<div class="bh2"><b>${gl[1]}</b></div><p>${gl[2]}</p>`;
      else if(MK.test(t))return UNAVAIL('');
      else return OUTSCOPE();}
    if(has(t,I.rank)&&ids.length===1&&ids[0]==='TASI'&&/(اسهم|سهم|شركات)/.test(t))return rank(t,el);
    const a=BY[ids[0]];const same=CTX.last===a.id;CTX.last=a.id;
    if(ids.length>1)return compare(ids);
    if(has(t,I.why))return why(a,tf);
    if(has(t,I.bear))return ifMove(a,tf,false);
    if(has(t,I.bull))return ifMove(a,tf,true);
    if(has(t,I.plan))return plan(a,tf);
    if(has(t,I.sit))return situation(a,tf);
    if(has(t,I.yes)&&same&&t.split(' ').length<=3)return CTX.topic==='plan'?why(a,tf):plan(a,tf);
    if(has(t,I.news))return news(a);
    if(has(t,I.define)&&gl)return`<div class="bh2"><b>${gl[1]}</b></div><p>${gl[2]}</p>`+await brief(a,tf);
    if(has(t,I.levels))return levels(a,tf);
    if(has(t,I.target))return targets(a,tf);
    if(has(t,I.mom))return momentum(a);
    if(has(t,I.weekly)&&!tf)return weekly(a);
    if(has(t,I.act))return plan(a,tf);
    CTX.topic='brief';return brief(a,tf);}

  /* ---------- ui ---------- */
  const btn=$('botBtn'),panel=$('botPanel'),log=$('botLog'),form=$('botForm'),inp=$('botIn'),tip=$('botTip');
  const LS={get(k){try{return localStorage.getItem(k)}catch(_){return null}},set(k,v){try{localStorage.setItem(k,v)}catch(_){}}};
  let busy=false;
  function add(cls,html){const d=document.createElement('div');d.className='bmsg '+cls;d.innerHTML=html;log.appendChild(d);log.scrollTop=log.scrollHeight;return d;}
  async function ask(q){q=String(q||'').trim().slice(0,200);if(!q||busy)return;busy=true;add('me',esc(q));
    const d=add('bot','<span class="btyp"><i></i><i></i><i></i></span>');const t0=Date.now();let h;
    try{h=await answer(q,d);}catch(e){console.error(e);h='<p>حدث خطأ أثناء التحليل. حاول مرة أخرى.</p>';}
    const w=350-(Date.now()-t0);if(w>0)await new Promise(r=>setTimeout(r,w));
    d.innerHTML=h;log.scrollTop=Math.max(0,d.offsetTop-8);busy=false;}
  function open(){panel.hidden=false;btn.setAttribute('aria-expanded','true');document.documentElement.classList.add('bot-on');tip.hidden=true;LS.set('bot-seen','1');
    if(!log.children.length)add('bot',WELCOME());setTimeout(()=>{if(matchMedia('(min-width:700px)').matches)inp.focus();},60);}
  function close(){panel.hidden=true;btn.setAttribute('aria-expanded','false');document.documentElement.classList.remove('bot-on');btn.focus();}
  btn.addEventListener('click',()=>panel.hidden?open():close());
  $('botClose').addEventListener('click',close);
  document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!panel.hidden)close();});
  form.addEventListener('submit',e=>{e.preventDefault();const v=inp.value;inp.value='';ask(v);});
  log.addEventListener('click',e=>{const q=e.target.closest('[data-q]');if(q){ask(q.dataset.q);return;}
    const g=e.target.closest('[data-go]');if(g){if(g.dataset.go==='cube'){const c=$('vxCube');if(c){close();c.scrollIntoView({behavior:'smooth',block:'center'});setTimeout(()=>c.click(),500);}}else if(g.dataset.go==='tv'&&window.CHARTX){close();CHARTX.open(CTX.last||API().current());}return;}
    const o=e.target.closest('[data-open]');if(o){const [id,tab]=o.dataset.open.split(':');API().open(id,tab);if(!matchMedia('(min-width:700px)').matches)close();}});
  window.WAVE_ASK={ask,answer,findAssets:q=>findAssets(norm(q))};
})();
