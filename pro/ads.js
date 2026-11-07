(function(){
  /* Ad spaces. Until real advertisers are booked they show clearly-labelled sample ads from fictional brands
     and an "advertise here" card. To book a slot later, replace the entries in ADS. */
  const SITE='https://shaibanor.github.io/Wave/';
  const ADS=[
    {t:'تيكودينغ شارت',d:'منصة شارت كاملة بأدوات الرسم وفيبوناتشي و19 مؤشرًا · جرّبها الآن',c:'افتح الموقع',g:'#2962FF',i:'M4 18l5-6 4 3 7-9'},
    {t:'أخبار السلحفاة',d:'اكتتابات وإدراجات ونتائج وتوزيعات لكل سوق في مكان واحد',c:'افتح الموقع',g:'#FF8C2A',i:'M5 5h14v14H5zM8 9h8M8 13h8M8 17h5'},
    {t:'التحليل الشامل',d:'40 سهمًا وعملة وسلعة في جدول واحد: الاتجاه والقوة وتوقع الأسبوع',c:'افتح الموقع',g:'#C9A55C',i:'M3 5h18v14H3zM3 10h18M3 15h18M9 5v14M15 5v14'}];
  const HERE={t:'منصة تيكو',d:'تحليل يومي وأسبوعي للأسهم السعودية والأمريكية والعملات والسلع · shaibanor.github.io/Wave',c:'زيارة الموقع',g:'#E9CF8F',i:'M12 3l9 5v8l-9 5-9-5V8z',here:1};
  let k=0;
  function card(a){return`<a class="ad-card${a.here?' here':''}" href="${SITE}" target="_blank" rel="noopener" style="--ag:${a.g}"><span class="ad-tag">إعلان</span><span class="ad-ic"><svg viewBox="0 0 24 24"><path d="${a.i}"/></svg></span><span class="ad-tx"><b>${a.t}</b><small>${a.d}</small></span><span class="ad-cta">${a.c}</span></a>`;}
  function fill(){document.querySelectorAll('.adslot:not([data-ok])').forEach(el=>{const a=el.dataset.ad==='mid'?HERE:ADS[k++%ADS.length];el.innerHTML=card(a);el.dataset.ok='1';});}
  document.readyState==='loading'?document.addEventListener('DOMContentLoaded',fill):fill();
  window.ADSLOTS={fill};
})();
