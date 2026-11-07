(function(){
  /* Tiko turtle.
     1) Brand mark: a clean geometric turtle seen from above; its shell is the platform cube (three shaded faces).
     2) Mascot «السلحفاة الذكية»: a 3D-looking robot turtle with several outfits and moves (idle, wave, hover, scan, dance). */
  const RM=matchMedia('(prefers-reduced-motion: reduce)').matches;
  const look={x:0,y:0,tx:0,ty:0};let blinkAt=0,happy=0;
  function el(g,x,y,rx,ry,rot){g.beginPath();g.ellipse(x,y,Math.max(.1,rx),Math.max(.1,ry),rot||0,0,Math.PI*2);}

  /* ---------- brand mark (SVG) ---------- */
  let MK=0;
  function mark(){const u='tm'+(MK++);return`<svg viewBox="0 0 64 64" class="tm-svg" aria-hidden="true" focusable="false">
<defs><linearGradient id="${u}a" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#FBE7B0"/><stop offset="1" stop-color="#D9B465"/></linearGradient>
<linearGradient id="${u}b" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#C9A55C"/><stop offset="1" stop-color="#8E6B2C"/></linearGradient>
<linearGradient id="${u}c" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#A4823F"/><stop offset="1" stop-color="#5E4519"/></linearGradient>
<linearGradient id="${u}h" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#F3FBF9"/><stop offset="1" stop-color="#8FB7AC"/></linearGradient>
<linearGradient id="${u}s" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff" stop-opacity=".55"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
<clipPath id="${u}k"><path d="M32 19L46.7 27.5V44.5L32 53L17.3 44.5V27.5Z"/></clipPath></defs>
<g fill="url(#${u}h)"><ellipse cx="15.5" cy="25" rx="6.4" ry="3.3" transform="rotate(-38 15.5 25)" class="tm-f1"/><ellipse cx="48.5" cy="25" rx="6.4" ry="3.3" transform="rotate(38 48.5 25)" class="tm-f2"/>
<ellipse cx="16.5" cy="48" rx="5.6" ry="3" transform="rotate(34 16.5 48)"/><ellipse cx="47.5" cy="48" rx="5.6" ry="3" transform="rotate(-34 47.5 48)"/><path d="M29.4 52.5L32 59L34.6 52.5Z"/></g>
<circle cx="32" cy="13.2" r="6.6" fill="url(#${u}h)"/><circle cx="29.5" cy="12.4" r="1.25" fill="#2FD3C2" class="tm-eye"/><circle cx="34.5" cy="12.4" r="1.25" fill="#2FD3C2" class="tm-eye"/>
<path d="M32 19L46.7 27.5L32 36L17.3 27.5Z" fill="url(#${u}a)"/><path d="M17.3 27.5L32 36V53L17.3 44.5Z" fill="url(#${u}b)"/><path d="M46.7 27.5V44.5L32 53V36Z" fill="url(#${u}c)"/>
<g clip-path="url(#${u}k)"><rect class="tm-sheen" x="-30" y="14" width="22" height="44" fill="url(#${u}s)" transform="skewX(-20)"/></g>
<path d="M32 19L46.7 27.5V44.5L32 53L17.3 44.5V27.5Z M32 36V53 M32 36L17.3 27.5 M32 36L46.7 27.5" fill="none" stroke="rgba(255,248,225,.55)" stroke-width=".8" stroke-linejoin="round"/>
</svg>`;}
  function markURL(){return'data:image/svg+xml;charset=utf-8,'+encodeURIComponent(mark().replace('<svg ','<svg xmlns="http://www.w3.org/2000/svg" '));}

  /* ---------- mascot outfits ---------- */
  const SKINS={
    classic:{n:'كلاسيك',sh:['#FFD09A','#FF8C2A','#C4500A','#7A3005'],seam:'rgba(90,30,0,.55)',led:['170,255,220','#14805A','rgba(220,255,240,.8)'],eye:['120,255,230','#BFFFF2'],mt:['#F4FAF8','#B9D3CB','#E3EFEB','#6E8F86'],ant:'255,200,90',vis:['#24323A','#0B1216']},
    chrome:{n:'كروم',sh:['#FFFFFF','#C9D6DE','#7C8E99','#3E4B54'],seam:'rgba(30,45,55,.5)',led:['150,210,255','#1D5FA8','rgba(210,235,255,.85)'],eye:['120,200,255','#D6EEFF'],mt:['#FFFFFF','#C3CDD3','#EDF2F5','#6B7A83'],ant:'120,200,255',vis:['#1B2530','#070B10']},
    neon:{n:'نيون',sh:['#4A4F66','#25283A','#14161F','#07080C'],seam:'rgba(255,60,200,.55)',led:['255,90,220','#6A1B7A','rgba(255,170,240,.9)'],eye:['80,255,240','#C8FFFA'],mt:['#5C6178','#30344A','#454A63','#15171F'],ant:'255,80,210',vis:['#0A0C14','#000'],glow:'255,60,200'},
    gold:{n:'ذهبي',sh:['#FFF1C2','#E9C770','#B88A2E','#6B4C12'],seam:'rgba(80,55,10,.55)',led:['255,236,170','#8C6A1C','rgba(255,245,210,.9)'],eye:['255,215,120','#FFF3CC'],mt:['#3A3A40','#1E1E22','#2C2C32','#0C0C0E'],ant:'255,210,110',vis:['#141416','#000']},
    arctic:{n:'جليدي',sh:['#FFFFFF','#E4F2FA','#A9C9DC','#5F86A0'],seam:'rgba(60,100,130,.45)',led:['140,230,255','#2386B8','rgba(225,248,255,.9)'],eye:['110,230,255','#E3FAFF'],mt:['#FFFFFF','#D5E4EC','#F1F7FA','#7E99A8'],ant:'120,220,255',vis:['#1A2A36','#060D13']}};
  const SK=Object.keys(SKINS),MOVES=['idle','wave','hover','scan','dance'];

  function draw(g,S,t,o){o=o||{};const P=SKINS[o.skin]||SKINS.classic,mv=o.move||'idle',mp=o.mp==null?0:o.mp,k=S/100;
    const env=Math.sin(Math.PI*Math.min(1,Math.max(0,mp)));/* 0→1→0 over a move */
    const metal=(x0,y0,x1,y1)=>{const m=g.createLinearGradient(x0,y0,x1,y1);m.addColorStop(0,P.mt[0]);m.addColorStop(.45,P.mt[1]);m.addColorStop(.55,P.mt[2]);m.addColorStop(1,P.mt[3]);return m;};
    const bolt=(x,y,r)=>{const b=g.createRadialGradient(x-r*.3,y-r*.3,0,x,y,r);b.addColorStop(0,'#FFFFFF');b.addColorStop(1,P.mt[3]);g.fillStyle=b;g.beginPath();g.arc(x,y,r,0,7);g.fill();};
    g.save();g.scale(k,k);
    let bob=RM?0:Math.sin(t*2.1)*2.2,lift=0,tilt=0,pad=RM?0:Math.sin(t*3.2),wave=0;const pulse=RM?.7:.55+.45*Math.sin(t*3.4);
    if(!RM){if(mv==='hover'){lift=-9*env;bob*=.5;}if(mv==='dance'){tilt=Math.sin(t*7)*.16*env;bob=Math.abs(Math.sin(t*7))*-3*env+bob*.3;}if(mv==='wave'){wave=env;}}
    const hx=look.x*3,hy=look.y*2;
    g.fillStyle='rgba(0,0,0,'+(.28-.14*env*(mv==='hover'?1:0))+')';el(g,54,92,30-bob*.8+lift*.8,4.5);g.fill();
    g.translate(54,80);g.rotate(tilt);g.translate(-54,-80);g.translate(0,bob+lift);
    /* hover jets */
    if(mv==='hover'&&env>.05&&!RM){[[40,82],[70,82]].forEach(([x,y])=>{const L=8+10*env+Math.sin(t*40)*1.5;const jg=g.createLinearGradient(0,y,0,y+L);jg.addColorStop(0,'rgba(255,250,220,.95)');jg.addColorStop(.35,'rgba('+P.ant+',.8)');jg.addColorStop(1,'rgba('+P.ant+',0)');g.fillStyle=jg;g.beginPath();g.moveTo(x-3,y);g.quadraticCurveTo(x,y+L*1.2,x+3,y);g.fill();});}
    /* back flipper */
    g.save();g.translate(70,74);g.rotate(.5+pad*.12);g.fillStyle=metal(-8,-4,12,8);el(g,6,4,13,6,.2);g.fill();bolt(0,3,1.6);g.restore();
    /* chassis */
    g.fillStyle=metal(0,60,0,84);el(g,58,74,30,10);g.fill();
    if(P.glow){g.strokeStyle='rgba('+P.glow+','+(.5+.4*pulse)+')';g.lineWidth=1.1;g.beginPath();g.moveTo(32,77);g.lineTo(86,77);g.stroke();}
    /* shell */
    const sx=60,sy=58,sr=31;
    g.save();g.beginPath();g.ellipse(sx,sy+6,sr,sr*.92,0,Math.PI,0);g.lineTo(sx+sr,sy+8);g.quadraticCurveTo(sx,sy+18,sx-sr,sy+8);g.closePath();
    const sh=g.createRadialGradient(sx-12,sy-22,4,sx,sy,sr*1.25);sh.addColorStop(0,P.sh[0]);sh.addColorStop(.32,P.sh[1]);sh.addColorStop(.75,P.sh[2]);sh.addColorStop(1,P.sh[3]);g.fillStyle=sh;g.fill();g.clip();
    g.strokeStyle=P.seam;g.lineWidth=.9;[[sx-sr,sy-6,sx+sr,sy-6],[sx-sr,sy+3,sx+sr,sy+3],[sx-10,sy-30,sx-14,sy+14],[sx+10,sy-30,sx+14,sy+14]].forEach(([a,b,c,d])=>{g.beginPath();g.moveTo(a,b);g.lineTo(c,d);g.stroke();});
    const hex=(x,y,r,ph)=>{const pz=RM?.8:.55+.45*Math.sin(t*3.4+ph);g.beginPath();for(let q=0;q<6;q++){const a=Math.PI/3*q+Math.PI/6;q?g.lineTo(x+r*Math.cos(a),y+r*Math.sin(a)*.8):g.moveTo(x+r*Math.cos(a),y+r*Math.sin(a)*.8);}g.closePath();
      const hg=g.createRadialGradient(x-r*.3,y-r*.3,1,x,y,r);hg.addColorStop(0,`rgba(${P.led[0]},${.7+.3*pz})`);hg.addColorStop(1,P.led[1]);g.fillStyle=hg;g.fill();g.strokeStyle=P.led[2];g.lineWidth=.7;g.stroke();
      g.strokeStyle=`rgba(${P.led[0]},${.35+.45*pz})`;g.lineWidth=.55;g.beginPath();g.moveTo(x-r*.45,y);g.lineTo(x,y);g.lineTo(x+r*.25,y-r*.35);g.moveTo(x,y);g.lineTo(x+r*.2,y+r*.35);g.stroke();};
    hex(sx+1,sy-15,10.5,0);hex(sx-17,sy-1,7,1.2);hex(sx+19,sy-1,7,2.4);hex(sx+1,sy+5,6,3.6);
    /* scan: a light bar sweeps across the shell */
    if(mv==='scan'&&!RM){const xx=sx-sr+(2*sr)*((t*.9)%1);const sg=g.createLinearGradient(xx-6,0,xx+6,0);sg.addColorStop(0,'rgba(255,255,255,0)');sg.addColorStop(.5,`rgba(${P.eye[0]},${.55*env})`);sg.addColorStop(1,'rgba(255,255,255,0)');g.fillStyle=sg;g.fillRect(xx-6,sy-40,12,60);}
    g.restore();
    const rim=g.createLinearGradient(0,sy+4,0,sy+16);rim.addColorStop(0,P.mt[0]);rim.addColorStop(.5,P.mt[1]);rim.addColorStop(1,P.mt[3]);g.fillStyle=rim;g.beginPath();g.moveTo(sx-sr-2,sy+7);g.quadraticCurveTo(sx,sy+21,sx+sr+2,sy+7);g.quadraticCurveTo(sx,sy+15,sx-sr-2,sy+7);g.fill();
    for(let q=0;q<7;q++){const u=q/6,x=(1-u)*(1-u)*(sx-sr)+2*u*(1-u)*sx+u*u*(sx+sr),y=(1-u)*(1-u)*(sy+8)+2*u*(1-u)*(sy+17)+u*u*(sy+8);bolt(x,y+1.3,1.15);}
    g.fillStyle='rgba(255,255,255,.45)';el(g,sx-12,sy-19,7,3,-.5);g.fill();g.fillStyle='rgba(255,255,255,.95)';g.beginPath();g.arc(sx-6,sy-12,1.5,0,7);g.fill();
    /* front flipper (waves on the "wave" move) */
    g.save();g.translate(48,78);g.rotate(-.15-pad*.18-wave*(1.25+Math.sin(t*12)*.35));g.fillStyle=metal(-10,-4,14,8);el(g,4,3,14,6.5,.15);g.fill();bolt(-6,2,1.8);g.restore();
    /* neck */
    const nx=28+hx,ny=52+hy+(RM?0:Math.sin(t*2.1+.6)*1.2)-(mv==='dance'?Math.sin(t*7)*1.5*env:0);
    g.fillStyle=metal(30,56,44,72);el(g,36,66,10,9,-.5);g.fill();g.strokeStyle='rgba(0,0,0,.25)';g.lineWidth=.7;[[0,0],[2.5,2.2]].forEach(([dx,dy])=>{g.beginPath();g.ellipse(36+dx,66+dy,7,6,-.5,Math.PI*.9,Math.PI*1.9);g.stroke();});
    /* antenna (spins its light while scanning) */
    const ax=nx+2+hx*.3,ay=ny-16;g.strokeStyle=P.mt[3];g.lineWidth=1.3;g.beginPath();g.moveTo(nx+1,ny-14);g.quadraticCurveTo(ax+3,ay-4,ax+2,ay-9);g.stroke();
    const ap=mv==='scan'?.6+.4*Math.sin(t*14):pulse;const ag=g.createRadialGradient(ax+2,ay-10,0,ax+2,ay-10,5+2*env);ag.addColorStop(0,`rgba(${P.ant},${.9*ap+.1})`);ag.addColorStop(1,`rgba(${P.ant},0)`);g.fillStyle=ag;g.beginPath();g.arc(ax+2,ay-10,5+2*env,0,7);g.fill();g.fillStyle=`rgb(${P.ant})`;g.beginPath();g.arc(ax+2,ay-10,1.8,0,7);g.fill();
    /* head */
    const hd=g.createRadialGradient(nx-7,ny-9,2,nx,ny,22);hd.addColorStop(0,P.mt[0]);hd.addColorStop(.5,P.mt[2]);hd.addColorStop(1,P.mt[3]);g.fillStyle=hd;el(g,nx,ny,19,17,-.1);g.fill();bolt(nx+15,ny+2,1.7);
    /* visor + eyes */
    g.save();g.translate(hx*.6,hy*.5);g.beginPath();g.moveTo(nx-17,ny-6);g.quadraticCurveTo(nx-2,ny-12,nx+13,ny-6);g.lineTo(nx+12,ny+4);g.quadraticCurveTo(nx-2,ny+1,nx-16,ny+4);g.closePath();
    const vz=g.createLinearGradient(0,ny-12,0,ny+4);vz.addColorStop(0,P.vis[0]);vz.addColorStop(1,P.vis[1]);g.fillStyle=vz;g.fill();g.strokeStyle='rgba(255,255,255,.35)';g.lineWidth=.6;g.stroke();
    const now=t*1000;if(now>blinkAt+4200)blinkAt=now;const bl=RM?1:Math.max(.15,Math.min(1,Math.abs(now-blinkAt-90)/90));
    const sc=mv==='scan'&&!RM?Math.sin(t*5)*3*env:0;
    if(mv==='scan'&&!RM){g.fillStyle=`rgba(${P.eye[0]},.9)`;g.fillRect(nx-14+((Math.sin(t*5)+1)/2)*24,ny-5,2.2,8);}
    [[nx-8+sc,ny-2,4.6],[nx+4+sc,ny-1,5.4]].forEach(([ex,ey,er])=>{const eg=g.createRadialGradient(ex,ey,0,ex,ey,er*1.6);eg.addColorStop(0,`rgba(${P.eye[0]},.95)`);eg.addColorStop(1,`rgba(${P.eye[0]},0)`);g.fillStyle=eg;g.beginPath();g.arc(ex,ey,er*1.6,0,7);g.fill();
      const hap=happy||(mv==='wave'||mv==='dance')&&env>.3;g.fillStyle=P.eye[1];if(hap){g.lineWidth=1.6;g.strokeStyle=P.eye[1];g.beginPath();g.arc(ex,ey+1.2,er*.6,Math.PI*1.1,Math.PI*1.9);g.stroke();}else{el(g,ex,ey,er*.75,er*.75*bl);g.fill();if(bl>.5){g.fillStyle='#fff';g.beginPath();g.arc(ex-er*.25,ey-er*.25,er*.22,0,7);g.fill();}}});
    g.fillStyle='rgba(255,255,255,.16)';g.beginPath();g.moveTo(nx-15,ny-6);g.quadraticCurveTo(nx-4,ny-10,nx+6,ny-8);g.lineTo(nx+4,ny-6);g.quadraticCurveTo(nx-4,ny-8,nx-14,ny-4);g.fill();
    g.restore();
    for(let q=0;q<4;q++){g.fillStyle=happy?`rgb(${P.eye[0]})`:`rgba(${P.eye[0]},${.5+.4*pulse})`;g.fillRect(nx-6+q*3+hx*.6,ny+8+hy*.4+(happy&&(q===0||q===3)?-1:0),2,1.4);}
    g.restore();}
  window.TURTLE={draw,mark,markURL,SKINS,MOVES};

  /* brand mark wherever the logo appears */
  (function logos(){const go=()=>{document.querySelectorAll('img.tkb-t').forEach(i=>{i.src=markURL();});
      document.querySelectorAll('canvas.tlogo').forEach(c=>{const s=document.createElement('span');s.className=c.className.replace('tlogo','tlogo tmark');s.setAttribute('role','img');s.setAttribute('aria-label',c.getAttribute('aria-label')||'شعار منصة تيكو');s.innerHTML=mark();c.replaceWith(s);});};
    document.readyState==='loading'?document.addEventListener('DOMContentLoaded',go):go();})();

  /* mascot: cycles moves, and changes outfit every few moves (a new outfit on each visit too) */
  function mount(){const btn=document.getElementById('botBtn');if(!btn)return;
    const st=btn.querySelector('.bot-st');if(st)st.remove();
    const cv=document.createElement('canvas');cv.className='tt-cv';cv.setAttribute('aria-hidden','true');btn.insertBefore(cv,btn.querySelector('.bot-sh'));const sg=document.createElement('span');sg.className='tt-sig';sg.setAttribute('aria-hidden','true');btn.appendChild(sg);
    const av=document.querySelector('.bp-av');let ac=null;if(av){av.innerHTML='';av.classList.add('tt-av');ac=document.createElement('canvas');av.appendChild(ac);}
    const fit=(c,s)=>{const d=Math.min(2.5,devicePixelRatio||1);c.width=s*d;c.height=s*d;c.style.width=c.style.height=s+'px';return c.getContext('2d');};
    const g=fit(cv,84),ga=ac?fit(ac,38):null,d=Math.min(2.5,devicePixelRatio||1);
    let si=0;try{si=(+localStorage.getItem('tiko-skin')+1)%SK.length;localStorage.setItem('tiko-skin',si);}catch(_){si=Math.floor(Math.random()*SK.length);}if(!isFinite(si))si=0;
    const M={skin:SK[si],move:'idle',t0:0,dur:2.6,n:0,swap:0};
    function next(t){M.n++;if(M.n%4===0){si=(si+1)%SK.length;M.skin=SK[si];M.swap=t;try{localStorage.setItem('tiko-skin',si);}catch(_){}}
      const L=MOVES.filter(m=>m!==M.move);M.move=M.n%2?L[Math.floor(Math.random()*L.length)]:'idle';M.t0=t;M.dur=M.move==='idle'?2.4+Math.random()*1.6:2.6;}
    let raf=0,t0=performance.now(),last=0;
    const frame=now=>{raf=0;if(now-last<33){raf=requestAnimationFrame(frame);return;}last=now;const t=(now-t0)/1000;look.x+=(look.tx-look.x)*.12;look.y+=(look.ty-look.y)*.12;happy=Math.max(0,happy-.02);
      if(t-M.t0>M.dur)next(t);const o={skin:M.skin,move:M.move,mp:(t-M.t0)/M.dur};
      g.setTransform(1,0,0,1,0,0);g.clearRect(0,0,cv.width,cv.height);draw(g,84*d,t,o);
      const sw=t-M.swap;if(M.swap&&sw<.6){const r=(10+sw*90)*d,a=1-sw/.6;g.setTransform(1,0,0,1,0,0);g.strokeStyle=`rgba(255,255,255,${a})`;g.lineWidth=2*d;g.beginPath();g.arc(cv.width/2,cv.height/2,r,0,7);g.stroke();g.fillStyle=`rgba(255,255,255,${a*.35})`;g.fillRect(0,0,cv.width,cv.height);}
      if(ga&&!document.getElementById('botPanel').hidden){ga.setTransform(1,0,0,1,0,0);ga.clearRect(0,0,ac.width,ac.height);draw(ga,38*d,t,o);}
      if(!document.hidden&&!RM)raf=requestAnimationFrame(frame);};
    const kick=()=>{if(!raf)raf=requestAnimationFrame(frame);};
    addEventListener('pointermove',e=>{const r=cv.getBoundingClientRect();const dx=e.clientX-(r.left+r.width/2),dy=e.clientY-(r.top+r.height/2),m=Math.hypot(dx,dy)||1;look.tx=dx/m*Math.min(1,m/200);look.ty=dy/m*Math.min(1,m/200);},{passive:true});
    btn.addEventListener('pointerdown',()=>{happy=1;M.move='wave';M.t0=(performance.now()-t0)/1000;M.dur=1.8;},{passive:true});
    document.addEventListener('visibilitychange',kick);
    if(RM){draw(g,84*d,0,{skin:M.skin});if(ga)draw(ga,38*d,0,{skin:M.skin});}else kick();
    new MutationObserver(()=>{if(ga&&RM)draw(ga,38*d,0,{skin:M.skin});kick();}).observe(document.getElementById('botPanel'),{attributes:true,attributeFilter:['hidden']});}
  document.readyState==='loading'?document.addEventListener('DOMContentLoaded',mount):mount();
})();
