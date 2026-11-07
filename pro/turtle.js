(function(){
  /* «السلحفاة الذكية»: a shaded, animated 3D-looking robot turtle drawn on canvas for the assistant button and its panel avatar. */
  const RM=matchMedia('(prefers-reduced-motion: reduce)').matches;
  const look={x:0,y:0,tx:0,ty:0};let blinkAt=0,happy=0;
  function el(g,x,y,rx,ry,rot){g.beginPath();g.ellipse(x,y,Math.max(.1,rx),Math.max(.1,ry),rot||0,0,Math.PI*2);}
  /* robot turtle: same silhouette, brushed-metal skin, armoured shell with LED panels, visor eyes and an antenna */
  const metal=(g,x0,y0,x1,y1,a,b)=>{const m=g.createLinearGradient(x0,y0,x1,y1);m.addColorStop(0,a||'#F4FAF8');m.addColorStop(.45,'#B9D3CB');m.addColorStop(.55,'#E3EFEB');m.addColorStop(1,b||'#6E8F86');return m;};
  function bolt(g,x,y,r){const b=g.createRadialGradient(x-r*.3,y-r*.3,0,x,y,r);b.addColorStop(0,'#FFFFFF');b.addColorStop(1,'#7A8C88');g.fillStyle=b;g.beginPath();g.arc(x,y,r,0,7);g.fill();g.strokeStyle='rgba(40,60,56,.55)';g.lineWidth=.35;g.beginPath();g.moveTo(x-r*.6,y);g.lineTo(x+r*.6,y);g.stroke();}
  function draw(g,S,t,o){o=o||{};const k=S/100;g.save();g.scale(k,k);
    const bob=RM?0:Math.sin(t*2.1)*2.2,pad=RM?0:Math.sin(t*3.2),hx=look.x*3,hy=look.y*2,pulse=RM?.7:.55+.45*Math.sin(t*3.4);
    g.fillStyle='rgba(0,0,0,.28)';el(g,54,92,30-bob*.8,4.5);g.fill();
    g.translate(0,bob);
    /* back flipper (metal) */
    g.save();g.translate(70,74);g.rotate(.5+pad*.12);g.fillStyle=metal(g,-8,-4,12,8,'#D6E6E1','#5E7E76');el(g,6,4,13,6,.2);g.fill();g.strokeStyle='rgba(40,70,64,.5)';g.lineWidth=.6;g.beginPath();g.moveTo(-2,4);g.lineTo(14,6);g.stroke();bolt(g,0,3,1.6);g.restore();
    /* body chassis */
    g.fillStyle=metal(g,0,60,0,84,'#CFE3DC','#5F8077');el(g,58,74,30,10);g.fill();
    g.strokeStyle='rgba(30,60,55,.35)';g.lineWidth=.6;g.beginPath();g.moveTo(32,76);g.lineTo(86,76);g.stroke();
    /* armoured shell */
    const sx=60,sy=58,sr=31;
    g.save();g.beginPath();g.ellipse(sx,sy+6,sr,sr*.92,0,Math.PI,0);g.lineTo(sx+sr,sy+8);g.quadraticCurveTo(sx,sy+18,sx-sr,sy+8);g.closePath();
    const sh=g.createRadialGradient(sx-12,sy-22,4,sx,sy,sr*1.25);sh.addColorStop(0,'#FFD09A');sh.addColorStop(.32,'#FF8C2A');sh.addColorStop(.75,'#C4500A');sh.addColorStop(1,'#7A3005');g.fillStyle=sh;g.fill();g.clip();
    /* plate seams */
    g.strokeStyle='rgba(90,30,0,.55)';g.lineWidth=.9;[[sx-sr,sy-6,sx+sr,sy-6],[sx-sr,sy+3,sx+sr,sy+3],[sx-10,sy-30,sx-14,sy+14],[sx+10,sy-30,sx+14,sy+14]].forEach(([a,b,c,d])=>{g.beginPath();g.moveTo(a,b);g.lineTo(c,d);g.stroke();});
    /* LED hex panels with circuit traces */
    const hex=(x,y,r)=>{g.beginPath();for(let q=0;q<6;q++){const a=Math.PI/3*q+Math.PI/6;q?g.lineTo(x+r*Math.cos(a),y+r*Math.sin(a)*.8):g.moveTo(x+r*Math.cos(a),y+r*Math.sin(a)*.8);}g.closePath();
      const hg=g.createRadialGradient(x-r*.3,y-r*.3,1,x,y,r);hg.addColorStop(0,`rgba(170,255,220,${.75+.25*pulse})`);hg.addColorStop(1,'#14805A');g.fillStyle=hg;g.fill();g.strokeStyle='rgba(220,255,240,.8)';g.lineWidth=.7;g.stroke();
      g.strokeStyle=`rgba(200,255,235,${.35+.4*pulse})`;g.lineWidth=.55;g.beginPath();g.moveTo(x-r*.45,y);g.lineTo(x,y);g.lineTo(x+r*.25,y-r*.35);g.moveTo(x,y);g.lineTo(x+r*.2,y+r*.35);g.stroke();g.fillStyle='#E9FFF6';g.beginPath();g.arc(x,y,.9,0,7);g.fill();};
    hex(sx+1,sy-15,10.5);hex(sx-17,sy-1,7);hex(sx+19,sy-1,7);hex(sx+1,sy+5,6);
    g.restore();
    /* rim with rivets */
    const rim=g.createLinearGradient(0,sy+4,0,sy+16);rim.addColorStop(0,'#E8EEF0');rim.addColorStop(.5,'#9BA9AE');rim.addColorStop(1,'#5E6B70');g.fillStyle=rim;g.beginPath();g.moveTo(sx-sr-2,sy+7);g.quadraticCurveTo(sx,sy+21,sx+sr+2,sy+7);g.quadraticCurveTo(sx,sy+15,sx-sr-2,sy+7);g.fill();
    for(let q=0;q<7;q++){const u=q/6,x=(1-u)*(1-u)*(sx-sr)+2*u*(1-u)*sx+u*u*(sx+sr),y=(1-u)*(1-u)*(sy+8)+2*u*(1-u)*(sy+17)+u*u*(sy+8);bolt(g,x,y+1.3,1.15);}
    /* specular */
    g.fillStyle='rgba(255,255,255,.5)';el(g,sx-12,sy-19,7,3,-.5);g.fill();g.fillStyle='rgba(255,255,255,.95)';g.beginPath();g.arc(sx-6,sy-12,1.5,0,7);g.fill();
    /* front flipper with hinge */
    g.save();g.translate(48,78);g.rotate(-.15-pad*.18);g.fillStyle=metal(g,-10,-4,14,8,'#F0F7F4','#6C8C83');el(g,4,3,14,6.5,.15);g.fill();g.strokeStyle='rgba(40,70,64,.45)';g.lineWidth=.6;g.beginPath();g.moveTo(-6,3);g.lineTo(14,5);g.stroke();bolt(g,-6,2,1.8);g.restore();
    /* neck segments */
    const nx=28+hx,ny=52+hy+(RM?0:Math.sin(t*2.1+.6)*1.2);
    g.fillStyle=metal(g,30,56,44,72,'#DCEBE6','#6E8F86');el(g,36,66,10,9,-.5);g.fill();g.strokeStyle='rgba(40,70,64,.45)';g.lineWidth=.7;[[0,0],[2.5,2.2]].forEach(([dx,dy])=>{g.beginPath();g.ellipse(36+dx,66+dy,7,6,-.5,Math.PI*.9,Math.PI*1.9);g.stroke();});
    /* antenna */
    const ax=nx+2+hx*.3,ay=ny-16;g.strokeStyle='#8FA7A0';g.lineWidth=1.3;g.beginPath();g.moveTo(nx+1,ny-14);g.quadraticCurveTo(ax+3,ay-4,ax+2,ay-9);g.stroke();
    const ag=g.createRadialGradient(ax+2,ay-10,0,ax+2,ay-10,5);ag.addColorStop(0,`rgba(255,214,120,${.9*pulse+.1})`);ag.addColorStop(1,'rgba(255,170,60,0)');g.fillStyle=ag;g.beginPath();g.arc(ax+2,ay-10,5,0,7);g.fill();g.fillStyle='#FFC24A';g.beginPath();g.arc(ax+2,ay-10,1.8,0,7);g.fill();
    /* metal head */
    const hd=g.createRadialGradient(nx-7,ny-9,2,nx,ny,22);hd.addColorStop(0,'#FFFFFF');hd.addColorStop(.5,'#CFE6DE');hd.addColorStop(1,'#71958A');g.fillStyle=hd;el(g,nx,ny,19,17,-.1);g.fill();
    g.strokeStyle='rgba(40,70,64,.35)';g.lineWidth=.6;g.beginPath();g.ellipse(nx,ny,19,17,-.1,Math.PI*1.05,Math.PI*1.65);g.stroke();bolt(g,nx+15,ny+2,1.7);
    /* visor + LED eyes */
    g.save();g.translate(hx*.6,hy*.5);g.beginPath();g.moveTo(nx-17,ny-6);g.quadraticCurveTo(nx-2,ny-12,nx+13,ny-6);g.lineTo(nx+12,ny+4);g.quadraticCurveTo(nx-2,ny+1,nx-16,ny+4);g.closePath();
    const vz=g.createLinearGradient(0,ny-12,0,ny+4);vz.addColorStop(0,'#24323A');vz.addColorStop(1,'#0B1216');g.fillStyle=vz;g.fill();g.strokeStyle='rgba(200,240,230,.5)';g.lineWidth=.6;g.stroke();
    const now=t*1000;if(now>blinkAt+4200)blinkAt=now;const bl=RM?1:Math.max(.15,Math.min(1,Math.abs(now-blinkAt-90)/90));
    [[nx-8,ny-2,4.6],[nx+4,ny-1,5.4]].forEach(([ex,ey,er])=>{const eg=g.createRadialGradient(ex,ey,0,ex,ey,er*1.6);eg.addColorStop(0,'rgba(120,255,230,.95)');eg.addColorStop(1,'rgba(40,200,255,0)');g.fillStyle=eg;g.beginPath();g.arc(ex,ey,er*1.6,0,7);g.fill();
      g.fillStyle='#BFFFF2';el(g,ex,ey,er*.75,er*.75*bl);g.fill();if(bl>.5){g.fillStyle='#fff';g.beginPath();g.arc(ex-er*.25,ey-er*.25,er*.22,0,7);g.fill();}});
    g.fillStyle='rgba(255,255,255,.18)';g.beginPath();g.moveTo(nx-15,ny-6);g.quadraticCurveTo(nx-4,ny-10,nx+6,ny-8);g.lineTo(nx+4,ny-6);g.quadraticCurveTo(nx-4,ny-8,nx-14,ny-4);g.fill();
    g.restore();
    /* LED mouth grill */
    for(let q=0;q<4;q++){g.fillStyle=happy?'#7DFFD8':`rgba(90,230,200,${.5+.4*pulse})`;g.fillRect(nx-6+q*3+hx*.6,ny+8+hy*.4+(happy&&(q===0||q===3)?-1:0),2,1.4);}
    g.restore();}
  window.TURTLE={draw};
  /* the platform logo: every .tlogo canvas shows the turtle */
  (function bands(){const go=()=>{const I=document.querySelectorAll('img.tkb-t');if(!I.length)return;const c=document.createElement('canvas');c.width=c.height=96;draw(c.getContext('2d'),96,.4);const u=c.toDataURL('image/png');I.forEach(i=>{i.src=u;});};
    document.readyState==='loading'?document.addEventListener('DOMContentLoaded',go):go();})();
  (function logos(){const go=()=>{const L=[...document.querySelectorAll('canvas.tlogo')];if(!L.length)return;const d=Math.min(2.5,devicePixelRatio||1);
      L.forEach(c=>{const s=c.getBoundingClientRect().width||parseInt(getComputedStyle(c).width)||96;c.width=c.height=Math.round(s*d);});
      let last=0;const f=now=>{if(now-last>40&&!document.hidden){last=now;L.forEach(c=>{if(!c.offsetParent&&!c.closest('.gate'))return;const g=c.getContext('2d');g.setTransform(1,0,0,1,0,0);g.clearRect(0,0,c.width,c.height);draw(g,c.width,RM?0:now/1000);});}requestAnimationFrame(f);};requestAnimationFrame(f);};
    document.readyState==='loading'?document.addEventListener('DOMContentLoaded',go):go();})();
  function mount(){const btn=document.getElementById('botBtn');if(!btn)return;
    const st=btn.querySelector('.bot-st');if(st)st.remove();
    const cv=document.createElement('canvas');cv.className='tt-cv';cv.setAttribute('aria-hidden','true');btn.insertBefore(cv,btn.querySelector('.bot-sh'));const sg=document.createElement('span');sg.className='tt-sig';sg.setAttribute('aria-hidden','true');btn.appendChild(sg);
    const av=document.querySelector('.bp-av');let ac=null;if(av){av.innerHTML='';av.classList.add('tt-av');ac=document.createElement('canvas');av.appendChild(ac);}
    const fit=(c,s)=>{const d=Math.min(2.5,devicePixelRatio||1);c.width=s*d;c.height=s*d;c.style.width=c.style.height=s+'px';return c.getContext('2d');};
    const g=fit(cv,84),ga=ac?fit(ac,38):null,d=Math.min(2.5,devicePixelRatio||1);
    let raf=0,t0=performance.now(),last=0;
    const frame=now=>{raf=0;if(now-last<33){raf=requestAnimationFrame(frame);return;}last=now;const t=(now-t0)/1000;look.x+=(look.tx-look.x)*.12;look.y+=(look.ty-look.y)*.12;happy=Math.max(0,happy-.02);
      g.setTransform(1,0,0,1,0,0);g.clearRect(0,0,cv.width,cv.height);draw(g,84*d,t);
      if(ga&&!document.getElementById('botPanel').hidden){ga.setTransform(1,0,0,1,0,0);ga.clearRect(0,0,ac.width,ac.height);draw(ga,38*d,t);}
      if(!document.hidden&&!RM)raf=requestAnimationFrame(frame);};
    const kick=()=>{if(!raf)raf=requestAnimationFrame(frame);};
    addEventListener('pointermove',e=>{const r=cv.getBoundingClientRect();const dx=e.clientX-(r.left+r.width/2),dy=e.clientY-(r.top+r.height/2),m=Math.hypot(dx,dy)||1;look.tx=dx/m*Math.min(1,m/200);look.ty=dy/m*Math.min(1,m/200);},{passive:true});
    btn.addEventListener('pointerdown',()=>{happy=1;},{passive:true});
    document.addEventListener('visibilitychange',kick);
    if(RM){draw(g,84*d,0);if(ga)draw(ga,38*d,0);}else kick();
    new MutationObserver(()=>{if(ga&&RM)draw(ga,38*d,0);kick();}).observe(document.getElementById('botPanel'),{attributes:true,attributeFilter:['hidden']});}
  document.readyState==='loading'?document.addEventListener('DOMContentLoaded',mount):mount();
})();
