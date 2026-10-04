# -*- coding: utf-8 -*-
"""Render data.json (+ report.md written by Claude) into the dashboard page.
The page is generated — nothing to hand-edit per run. Publish the output with the Artifact tool
(capabilities: {downloads: true}) together with data/latest.csv as a supporting file."""
import argparse, json, html, re

TEMPLATE = r"""<title>مرصد جدة العقاري</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Arabic:wght@400;500;600;700&family=Reem+Kufi:wght@500;700&display=swap">
<style>
:root{
  --ground:#F2F5F5; --surface:#FFFFFF; --sunk:#E8EEEE; --ink:#10262D; --muted:#5B6E73; --line:#D8E1E2;
  --accent:#0B7A83; --accent-soft:#D5ECEE; --coral:#B8573A; --coral-soft:#F3E0D8; --sand:#A8925F; --sand-soft:#EFE8D6;
  --good:#2E7D4F; --warn:#A8740C; --crit:#B3261E; --warn-soft:#F6ECD2; --crit-soft:#F6DAD7;
  --display:"Reem Kufi","IBM Plex Sans Arabic",system-ui,sans-serif;
  --body:"IBM Plex Sans Arabic","Segoe UI",Tahoma,system-ui,sans-serif;
}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){color-scheme:dark;
  --ground:#0D171A; --surface:#142226; --sunk:#1A2B30; --ink:#E3ECED; --muted:#93A6AA; --line:#24363B;
  --accent:#39B3BC; --accent-soft:#12383C; --coral:#E0845F; --coral-soft:#3A2419; --sand:#C9B585; --sand-soft:#2E2A1E;
  --good:#5CC08A; --warn:#E0AE45; --crit:#F07A70; --warn-soft:#342A12; --crit-soft:#3B1C19;}}
:root[data-theme="dark"]{color-scheme:dark;
  --ground:#0D171A; --surface:#142226; --sunk:#1A2B30; --ink:#E3ECED; --muted:#93A6AA; --line:#24363B;
  --accent:#39B3BC; --accent-soft:#12383C; --coral:#E0845F; --coral-soft:#3A2419; --sand:#C9B585; --sand-soft:#2E2A1E;
  --good:#5CC08A; --warn:#E0AE45; --crit:#F07A70; --warn-soft:#342A12; --crit-soft:#3B1C19;}
*{box-sizing:border-box}
body{background:var(--ground);color:var(--ink);font-family:var(--body);font-size:15px;line-height:1.65;direction:rtl;
  padding-inline:16px;padding-block:20px 48px}
.wrap{max-width:1180px;margin-inline:auto;display:flex;flex-direction:column;gap:28px}
h1,h2,h3{font-family:var(--display);font-weight:700;text-wrap:balance;margin:0;line-height:1.3}
h1{font-size:clamp(26px,4vw,36px);letter-spacing:0}
h2{font-size:21px}
h3{font-size:16px;font-family:var(--body);font-weight:600}
.num{font-variant-numeric:tabular-nums;font-feature-settings:"tnum"}
.muted{color:var(--muted)}
.small{font-size:13px}
a{color:var(--accent)}
a:focus-visible,button:focus-visible,input:focus-visible,select:focus-visible,th:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
header.top{display:flex;flex-wrap:wrap;align-items:flex-end;justify-content:space-between;gap:12px 24px;
  padding-bottom:16px;border-bottom:1px solid var(--line)}
.eyebrow{font-size:12px;letter-spacing:.06em;color:var(--muted);text-transform:none}
.stamp{display:flex;flex-wrap:wrap;gap:8px}
.chip{display:inline-flex;align-items:center;gap:6px;padding:3px 10px;border-radius:999px;background:var(--sunk);
  color:var(--ink);font-size:12.5px;white-space:nowrap}
.chip.srem{background:var(--coral-soft);color:var(--coral)} .chip.aqar{background:var(--sand-soft);color:var(--sand)}
.chip.ok{background:var(--accent-soft);color:var(--accent)} .chip.warn{background:var(--warn-soft);color:var(--warn)}
.chip.crit{background:var(--crit-soft);color:var(--crit)}
.banner{padding:12px 16px;border-radius:10px;background:var(--warn-soft);color:var(--ink);border:1px solid var(--warn)}
.kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:1px;background:var(--line);border:1px solid var(--line);border-radius:12px;overflow:hidden}
.kpi{background:var(--surface);padding:16px 18px;display:flex;flex-direction:column;gap:4px;min-width:0}
.kpi .v{font-size:28px;font-weight:700;line-height:1.2}
.kpi .src{margin-top:auto;padding-top:6px}
.delta{font-size:12.5px}
.delta.up{color:var(--good)} .delta.down{color:var(--crit)}
section{display:flex;flex-direction:column;gap:14px}
.sec-head{display:flex;flex-wrap:wrap;align-items:baseline;justify-content:space-between;gap:8px}
.grid2{display:grid;grid-template-columns:minmax(0,1.25fr) minmax(0,1fr);gap:20px}
.panel{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:18px}
.report{max-width:70ch}
.report p{margin:0 0 10px} .report ul{margin:0 0 10px;padding-inline-start:20px}
.opps{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px}
.opp{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:14px 16px;display:flex;flex-direction:column;gap:8px}
.opp .rank{font-family:var(--display);color:var(--accent);font-size:13px}
.opp ul{margin:0;padding-inline-start:18px;font-size:13.5px}
.tbl-wrap{overflow-x:auto;border:1px solid var(--line);border-radius:12px;background:var(--surface)}
table{border-collapse:collapse;width:100%;font-size:13.5px}
th,td{padding:9px 12px;text-align:right;border-bottom:1px solid var(--line);white-space:nowrap}
th{position:sticky;top:0;background:var(--sunk);font-weight:600;font-size:12.5px;cursor:pointer;user-select:none}
th[aria-sort="ascending"]::after{content:" ▲";font-size:9px} th[aria-sort="descending"]::after{content:" ▼";font-size:9px}
tbody tr:hover{background:var(--sunk)}
td.na{color:var(--muted)}
.bar{display:inline-block;height:8px;border-radius:4px;background:var(--accent);vertical-align:middle;margin-inline-start:6px}
.controls{display:flex;flex-wrap:wrap;gap:10px;align-items:center}
input[type=search],select{font:inherit;font-size:14px;padding:7px 10px;border:1px solid var(--line);border-radius:8px;background:var(--surface);color:var(--ink)}
button{font:inherit;font-size:14px;padding:8px 14px;border-radius:8px;border:1px solid var(--accent);background:var(--accent);color:var(--surface);cursor:pointer}
button.ghost{background:transparent;color:var(--accent)}
.chart svg{width:100%;height:auto;display:block}
.legend{display:flex;flex-wrap:wrap;gap:14px;font-size:12.5px;color:var(--muted)}
.sw{display:inline-block;width:10px;height:10px;border-radius:2px;margin-inline-end:5px;vertical-align:middle}
.gates{display:flex;flex-direction:column;gap:6px;font-size:13.5px}
.gate{display:flex;gap:10px;align-items:baseline}
.gate .mark{font-weight:700} .gate.ok .mark{color:var(--good)} .gate.bad .mark{color:var(--crit)}
details summary{cursor:pointer;font-weight:600}
dl.defs{display:grid;grid-template-columns:max-content 1fr;gap:6px 16px;margin:0;font-size:13.5px}
dl.defs dt{font-weight:600} dl.defs dd{margin:0;color:var(--muted)}
@media (max-width:860px){.kpis{grid-template-columns:repeat(2,minmax(0,1fr))}.grid2{grid-template-columns:1fr}}
@media (max-width:420px){.kpis{grid-template-columns:1fr}.kpi .v{font-size:24px}}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
</style>
<div class="wrap" id="app">
  <header class="top">
    <div>
      <div class="eyebrow">كوشان · تحليل السوق العقاري</div>
      <h1>مرصد جدة العقاري</h1>
    </div>
    <div class="stamp" id="stamp"></div>
  </header>
  <div id="banner" hidden class="banner"></div>
  <div class="kpis" id="kpis"></div>

  <div class="grid2">
    <section class="panel">
      <div class="sec-head"><h2>التقرير الموجز</h2><span class="muted small" id="rep-date"></span></div>
      <div class="report" id="report"></div>
    </section>
    <section class="panel">
      <div class="sec-head"><h2>الصفقات المنفذة يوميًا</h2><span class="chip srem">البورصة العقارية</span></div>
      <div class="chart" id="daily"></div>
      <div class="legend"><span><i class="sw" style="background:var(--coral)"></i>قيمة الصفقات (مليون ر.س)</span><span class="num" id="daily-note"></span></div>
    </section>
  </div>

  <section>
    <div class="sec-head"><h2>أبرز الفرص</h2><span class="muted small">مرشحة آليًا من الأرقام؛ السبب مذكور لكل فرصة</span></div>
    <div class="opps" id="opps"></div>
  </section>

  <section>
    <div class="sec-head"><h2>سعر المتر حسب نوع العقار</h2><span class="chip aqar">أسعار معروضة · aqar.fm</span></div>
    <div class="tbl-wrap"><table id="types"></table></div>
    <details id="types-rest" class="small"></details>
    <p class="muted small" id="types-note"></p>
  </section>

  <section>
    <div class="sec-head"><h2>الأحياء</h2>
      <div class="controls">
        <input type="search" id="q" placeholder="ابحث عن حي" aria-label="ابحث عن حي">
        <select id="sector" aria-label="القطاع"><option value="">كل القطاعات</option><option value="شمال-جدة">شمال جدة</option><option value="جنوب-جدة">جنوب جدة</option></select>
        <button class="ghost" id="dl" hidden>تنزيل بيانات التشغيل (CSV)</button>
      </div>
    </div>
    <div class="tbl-wrap" style="max-height:620px"><table id="dist"></table></div>
    <p class="muted small" id="dist-note"></p>
  </section>

  <section id="trend-sec">
    <div class="sec-head"><h2>الاتجاه عبر التشغيلات</h2></div>
    <div class="panel chart" id="trend"></div>
  </section>

  <div class="grid2">
    <section class="panel">
      <h2>جودة البيانات</h2>
      <div class="gates" id="gates"></div>
      <div id="dq" class="small"></div>
    </section>
    <section class="panel">
      <h2>التعريفات والمنهجية</h2>
      <dl class="defs" id="defs"></dl>
    </section>
  </div>
  <p class="muted small" id="foot"></p>
</div>
<script id="payload" type="application/json">__DATA__</script>
<script>
(function(){
const D=JSON.parse(document.getElementById('payload').textContent);
const $=id=>document.getElementById(id);
const fmt=(v,d=0)=>v==null||isNaN(v)?'غير متوفر':Number(v).toLocaleString('en-US',{maximumFractionDigits:d,minimumFractionDigits:d});
const pct=v=>v==null?'غير متوفر':(v*100).toFixed(1)+'%';
const mSAR=v=>v==null?'غير متوفر':(v/1e6).toLocaleString('en-US',{maximumFractionDigits:1})+' م';
const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const C=D.city||{}, P=D.diff||{}, W=D.period||{};
const delta=(cur,prev,good='up',f=v=>fmt(v))=>{ if(cur==null||prev==null) return ''; const d=cur-prev; if(!d) return '<span class="delta muted">دون تغيير</span>';
  const dir=d>0?'up':'down'; const cls=(dir===good)?'up':'down'; return `<span class="delta ${cls}">${d>0?'▲':'▼'} ${f(Math.abs(d))} عن التشغيل السابق</span>`;};

// header
const arDate=s=>{if(!s)return '؟'; const [y,m,d]=s.slice(0,10).split('-').map(Number); return d+' '+['يناير','فبراير','مارس','أبريل','مايو','يونيو','يوليو','أغسطس','سبتمبر','أكتوبر','نوفمبر','ديسمبر'][m-1]+' '+y;};
$('stamp').innerHTML=`<span class="chip">تحديث ${esc(arDate(D.run_at))} · <bdi>${esc((D.run_at||'').slice(11,16))}</bdi></span><span class="chip">الفترة ${esc(arDate(W.from))} – ${esc(arDate(W.to))}</span>`+
  (D.partial?'<span class="chip warn">تشغيل جزئي</span>':'<span class="chip ok">اجتاز كل الفحوص</span>');
const failed=(D.gates||[]).filter(g=>!g.ok);
if(failed.length){$('banner').hidden=false;$('banner').innerHTML='<strong>تنبيه:</strong> '+failed.map(g=>esc(g.source+' — '+g.gate+' ('+g.detail+')')).join('؛ ')+'. الأرقام المعروضة صحيحة لما جُمع، لكنها قد لا تغطي السوق كاملًا.';}

// KPIs
const k=[
 ['صفقات منفذة · آخر 7 أيام',fmt(C.srem_deals),`قيمتها ${mSAR(C.srem_value)} ر.س`+'<br>'+delta(C.srem_deals,P.srem_deals_prev),'srem'],
 ['متوسط سعر المتر المنفذ',fmt(C.srem_avg_ppm)+' <span class="small muted">ر.س/م²</span>','كل أنواع العقار مجتمعة'+'<br>'+delta(C.srem_avg_ppm,P.srem_avg_ppm_prev),'srem'],
 ['نسبة المعروض',pct(C.supply_ratio),'إعلانات البيع ÷ (إعلانات البيع + الصفقات)'+'<br>'+delta(C.supply_ratio,P.supply_prev,'down',v=>(v*100).toFixed(1)+' نقطة'),'mix'],
 ['إعلانات نشطة في جدة',fmt(C.active),`بيع ${fmt(C.sale)} · إيجار ${fmt(C.rent)}`+(P.new_listings!=null?`<br><span class="delta">+${fmt(P.new_listings)} جديد · −${fmt(P.removed_listings)} اختفى</span>`:''),'aqar']];
$('kpis').innerHTML=k.map(([l,v,s,src])=>`<div class="kpi"><div class="small muted">${l}</div><div class="v num">${v}</div><div class="small muted num">${s}</div><div class="src">${src==='srem'?'<span class="chip srem">البورصة العقارية</span>':src==='aqar'?'<span class="chip aqar">aqar.fm</span>':'<span class="chip srem">البورصة</span> <span class="chip aqar">aqar</span>'}</div></div>`).join('');

// report (markdown-lite from Claude)
const md=(D.report||'').trim();
$('report').innerHTML=md?md.split(/\n{2,}/).map(b=>/^\s*[-•]/.test(b)?'<ul>'+b.split('\n').map(l=>'<li>'+esc(l.replace(/^\s*[-•]\s*/,'')).replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>')+'</li>').join('')+'</ul>':'<p>'+esc(b).replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>').replace(/\n/g,'<br>')+'</p>').join(''):'<p class="muted">لم يُكتب التقرير لهذا التشغيل.</p>';
$('rep-date').textContent=(D.run_at||'').slice(0,10);

// daily chart (SVG, one scale)
(function(){const d=(D.srem&&D.srem.daily)||[]; if(!d.length){$('daily').innerHTML='<p class="muted">لا توجد بيانات يومية.</p>';return;}
 const w=560,h=230,pl=44,pr=10,pt=14,pb=40; const max=Math.max(...d.map(x=>x.value))/1e6||1; const step=(w-pl-pr)/d.length; const bw=Math.min(42,step*.62);
 const nice=Math.pow(10,Math.floor(Math.log10(max))); const top=Math.ceil(max/nice)*nice; const y=v=>pt+(h-pt-pb)*(1-v/top);
 let g=''; for(let i=0;i<=4;i++){const v=top*i/4; g+=`<line x1="${pl}" x2="${w-pr}" y1="${y(v)}" y2="${y(v)}" stroke="var(--line)" stroke-width="1"/><text x="${pl-6}" y="${y(v)+4}" text-anchor="start" font-size="11" fill="var(--muted)" direction="ltr">${fmt(v)}</text>`;}
 // x runs right→left to match reading direction of the page (dates are ordinal, not a map)
 d.forEach((x,i)=>{const cx=w-pr-step*(i+.5); const v=x.value/1e6; g+=`<rect x="${cx-bw/2}" y="${y(v)}" width="${bw}" height="${y(0)-y(v)}" rx="3" fill="var(--coral)"><title>${x.date}: ${fmt(x.count)} صفقة · ${fmt(v,1)} م ر.س</title></rect>`+
  `<text x="${cx}" y="${y(v)-5}" text-anchor="middle" font-size="11" fill="var(--ink)">${fmt(x.count)}</text>`+
  `<text x="${cx}" y="${h-pb+16}" text-anchor="middle" font-size="11" fill="var(--muted)">${x.date.slice(5)}</text>`;});
 $('daily').innerHTML=`<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="قيمة وعدد الصفقات اليومية">${g}</svg>`;
 $('daily-note').textContent='الرقم فوق العمود = عدد الصفقات';})();

// opportunities
const O=D.opportunities||[];
$('opps').innerHTML=O.length?O.map((o,i)=>`<article class="opp"><div class="rank">فرصة ${i+1}</div><h3>حي ${esc(o.district)}</h3>
 <div class="small muted num">وسيط متر الأرض المعروضة ${fmt(o.land_ppm_median)} ر.س (${fmt(o.land_n)} إعلان) · صفقات الأسبوع ${fmt(o.srem_deals)}</div>
 <ul>${(o.why||[]).map(w=>'<li>'+esc(w)+'</li>').join('')}</ul>${o.note?'<p class="small">'+esc(o.note)+'</p>':''}</article>`).join(''):'<p class="muted">لا توجد فرص تستوفي المعايير في هذا التشغيل.</p>';

// types
const T=(D.aqar&&D.aqar.by_type)||{};
const trows=Object.entries(T).sort((a,b)=>(b[1].sale_n+b[1].rent_n)-(a[1].sale_n+a[1].rent_n));
const cell=(s)=>s&&s.median!=null?`<td class="num">${fmt(s.median)}</td><td class="num">${fmt(s.mean)}</td>`:`<td class="na" colspan="2">${esc(s&&s.reason||'غير متوفر')}</td>`;
const main=trows.filter(([,v])=>v.sale_n+v.rent_n>=20), rest=trows.filter(([,v])=>v.sale_n+v.rent_n<20);
$('types').innerHTML='<thead><tr><th>نوع العقار</th><th>إعلانات بيع</th><th>وسيط متر البيع</th><th>متوسط متر البيع</th><th>إعلانات إيجار</th><th>وسيط الإيجار السنوي/م²</th><th>متوسط الإيجار السنوي/م²</th></tr></thead><tbody>'+
 main.map(([t,v])=>`<tr><td>${esc(t)}</td><td class="num">${fmt(v.sale_n)}</td>${cell(v.sale_ppm)}<td class="num">${fmt(v.rent_n)}</td>${cell(v.rent_ppm_year)}</tr>`).join('')+'</tbody>';
$('types-rest').innerHTML=rest.length?`<summary>${rest.length} أنواع أخرى بأقل من 20 إعلانًا</summary><p class="small muted">${rest.map(([t,v])=>esc(t)+' <span class="num">('+fmt(v.sale_n)+' بيع · '+fmt(v.rent_n)+' إيجار)</span>').join('، ')}</p>`:'';
$('types-note').textContent='الأسعار المعروضة ليست أسعار بيع منفذة. استُبعدت القيم الشاذة (أبعد من 3 أضعاف المدى الربيعي على مقياس لوغاريتمي) وعددها ظاهر في ملف البيانات. البورصة العقارية لا تنشر متوسطات حسب نوع العقار، لذا لا يوجد عمود منفذ هنا.';

// districts table
const DS=D.districts||[]; const maxSale=Math.max(1,...DS.map(d=>d.sale));
const cols=[['name','الحي',d=>esc(d.name)],['sector','القطاع',d=>esc((d.sector||'').replace('-',' '))],['active','نشطة',d=>fmt(d.active)],['sale','بيع',d=>fmt(d.sale)+`<span class="bar" style="width:${Math.round(40*d.sale/maxSale)}px"></span>`],
 ['rent','إيجار',d=>fmt(d.rent)],['land','وسيط متر الأرض',d=>d.land_ppm.median!=null?fmt(d.land_ppm.median):'<span class="muted">—</span>'],['apt','وسيط متر الشقة',d=>d.apt_ppm.median!=null?fmt(d.apt_ppm.median):'<span class="muted">—</span>'],
 ['srem_deals','صفقات البورصة',d=>fmt(d.srem_deals)],['srem_avg_ppm','متوسط المتر المنفذ',d=>d.srem_avg_ppm!=null?fmt(d.srem_avg_ppm):'<span class="muted">—</span>'],
 ['supply_ratio','نسبة المعروض',d=>d.supply_ratio!=null?pct(d.supply_ratio):'—'],['nb','مقابل الجوار',d=>d.land_vs_neighbours!=null?`<span class="${d.land_vs_neighbours>0?'delta up':'delta down'}">${d.land_vs_neighbours>0?'أرخص':'أغلى'} ${Math.abs(d.land_vs_neighbours*100).toFixed(0)}%</span>`:'—']];
const key={name:d=>d.name,sector:d=>d.sector,active:d=>d.active,sale:d=>d.sale,rent:d=>d.rent,land:d=>d.land_ppm.median??-1,apt:d=>d.apt_ppm.median??-1,srem_deals:d=>d.srem_deals,srem_avg_ppm:d=>d.srem_avg_ppm??-1,supply_ratio:d=>d.supply_ratio??-1,nb:d=>d.land_vs_neighbours??-9};
let sort={k:'active',dir:-1};
function renderDist(){const q=$('q').value.trim(), s=$('sector').value;
 const rows=DS.filter(d=>(!q||d.name.includes(q))&&(!s||d.sector===s)).sort((a,b)=>{const x=key[sort.k](a),y=key[sort.k](b);return (x>y?1:x<y?-1:0)*sort.dir;});
 $('dist').innerHTML='<thead><tr>'+cols.map(([k,l])=>`<th tabindex="0" data-k="${k}" aria-sort="${sort.k===k?(sort.dir>0?'ascending':'descending'):'none'}">${l}</th>`).join('')+'</tr></thead><tbody>'+
  rows.map(d=>'<tr>'+cols.map(([,,f])=>`<td class="num">${f(d)}</td>`).join('')+'</tr>').join('')+'</tbody>';
 $('dist').querySelectorAll('th').forEach(th=>{const go=()=>{const k=th.dataset.k; sort=sort.k===k?{k,dir:-sort.dir}:{k,dir:k==='name'||k==='sector'?1:-1}; renderDist();}; th.onclick=go; th.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();go();}};});
 $('dist-note').textContent=`${rows.length} حيًا معروضًا من ${DS.length}. صفقات البورصة مرتبطة بالحي عبر مطابقة الاسم؛ الأحياء غير المطابقة مذكورة في جودة البيانات. «—» تعني عينة أقل من ${D.min_sample||8} إعلانات.`;}
$('q').oninput=renderDist; $('sector').onchange=renderDist; renderDist();

// trend
(function(){const H=D.history||[]; if(H.length<2){$('trend').innerHTML='<p class="muted">يظهر الاتجاه بعد التشغيل الثاني. هذا أول تشغيل مسجّل.</p>';return;}
 const w=900,h=240,pl=52,pr=16,pt=16,pb=34; const ser=[['srem_avg_ppm','متوسط المتر المنفذ (البورصة)','var(--coral)'],['land_median','وسيط متر الأرض المعروضة (aqar)','var(--sand)'],['apt_median','وسيط متر الشقة المعروضة (aqar)','var(--accent)']];
 const vals=H.flatMap(r=>ser.map(s=>r[s[0]]).filter(v=>v!=null)); const mx=Math.max(...vals)*1.1, mn=0; const x=i=>w-pr-(w-pl-pr)*i/(H.length-1); const y=v=>pt+(h-pt-pb)*(1-(v-mn)/(mx-mn));
 let g=''; for(let i=0;i<=4;i++){const v=mn+(mx-mn)*i/4; g+=`<line x1="${pl}" x2="${w-pr}" y1="${y(v)}" y2="${y(v)}" stroke="var(--line)"/><text x="${pl-6}" y="${y(v)+4}" text-anchor="start" font-size="11" fill="var(--muted)">${fmt(v)}</text>`;}
 H.forEach((r,i)=>{g+=`<text x="${x(i)}" y="${h-10}" text-anchor="middle" font-size="11" fill="var(--muted)">${(r.run_at||'').slice(5,10)}</text>`;});
 ser.forEach(([k,,c])=>{const pts=H.map((r,i)=>r[k]!=null?[x(i),y(r[k])]:null).filter(Boolean); if(!pts.length)return; g+=`<polyline fill="none" stroke="${c}" stroke-width="2.2" points="${pts.map(p=>p.join(',')).join(' ')}"/>`; const e=pts[pts.length-1]; g+=`<circle cx="${pts[pts.length-1][0]}" cy="${pts[pts.length-1][1]}" r="4" fill="${c}"/>`;});
 $('trend').innerHTML=`<svg viewBox="0 0 ${w} ${h}" role="img" aria-label="اتجاه أسعار المتر">${g}</svg><div class="legend">${ser.map(s=>`<span><i class="sw" style="background:${s[2]}"></i>${s[1]}</span>`).join('')}</div>`;})();

// data quality
const GA={'daily rows sum to weekly total':'مجموع الأيام يطابق إجمالي الأسبوع','all rows are Jeddah':'كل الصفوف من جدة','district sum ≤ city total':'مجموع الأحياء لا يتجاوز إجمالي المدينة','market total read from aqar':'قراءة إجمالي إعلانات جدة','every row is a Jeddah URL':'كل الإعلانات من جدة','coverage ≥ 90%':'التغطية 90% فأكثر'};
$('gates').innerHTML=(D.gates||[]).map(g=>`<div class="gate ${g.ok?'ok':'bad'}"><span class="mark">${g.ok?'✓':'✕'}</span><span><strong>${esc(g.source)}</strong> — ${esc(GA[g.gate]||g.gate)}${g.detail?` <span class="muted num"><bdi>${esc(g.detail)}</bdi></span>`:''}</span></div>`).join('');
const um=D.srem_unmapped||[], dt=D.dates||{}, mism=DS.reduce((a,d)=>a+(d.mismatch||0),0), cf=D.conflicts||[];
$('dq').innerHTML=`<p>تغطية ربط صفقات البورصة بالأحياء: <strong class="num">${pct(D.srem_district_coverage)}</strong> من صفقات الأسبوع.${um.length?' أحياء في البورصة بلا مقابل في aqar: '+um.slice(0,12).map(u=>esc(u.name)+' ('+u.count+')').join('، ')+(um.length>12?' …':''):''}</p>
${(D.srem_duplicates||[]).length?'<p>أحياء في البورصة تُرجع نفس الرقم الإجمالي (عُدّت مرة واحدة): '+D.srem_duplicates.map(x=>esc(x.names.join(' = '))+(x.resolved?'':' (غير منسوبة لأنها في أحياء مختلفة)')).join('؛ ')+'.</p>':''}
<p>تاريخ الإعلان معروف لـ <strong class="num">${fmt(dt.known)}</strong> من ${fmt(dt.total)} إعلان (يُجلب من صفحة الإعلان تدريجيًا، ${fmt(dt.fetched_this_run)} في هذا التشغيل). الباقي «غير متوفر» حتى يُجلب.</p>
<p>إعلانات يختلف فيها الحي بين رابط الإعلان ونصه: <strong class="num">${fmt(mism)}</strong> (يُحتفظ بالاثنين في ملف البيانات).</p>
<p>${cf.length?'تعارضات بين المصدرين على نفس القطعة: '+cf.map(c=>`مخطط ${esc(c.srem.plan)} قطعة ${esc(c.srem.parcel)} — البورصة ${fmt(c.srem.amount)} ر.س، aqar ${fmt(c.aqar.price)} ر.س`).join('؛ '):'لم تُطابَق أي صفقة منفردة من البورصة مع إعلان في aqar (البورصة تنشر آخر 5 صفقات فقط منفردة).'}</p>`;
const defs=[['نسبة المعروض',(D.notes||{}).supply_definition||''],['سعر المتر المنفذ','إجمالي قيمة الصفقات ÷ إجمالي مساحتها، كما تنشره البورصة العقارية (مرجّح بالمساحة)'],['سعر المتر المعروض','السعر المطلوب في الإعلان ÷ مساحته؛ للإيجار السعر سنوي'],['الفرصة','حي وسيط متر الأرض فيه أقل بـ 15% فأكثر من وسيط أقرب 5 أحياء، أو صفقاته المنفذة مرتفعة مقابل معروض منخفض'],['الفترة','آخر 7 أيام تنشرها البورصة العقارية حتى تاريخ التشغيل'],['النطاق','مدينة جدة فقط (رمز المدينة 37528 في البورصة)']];
$('defs').innerHTML=defs.map(([t,d])=>`<dt>${t}</dt><dd>${esc(d)}</dd>`).join('');
$('foot').innerHTML='المصادر: <a href="https://srem.moj.gov.sa/" target="_blank" rel="noopener">البورصة العقارية — وزارة العدل</a> · <a href="https://sa.aqar.fm/%D8%B9%D9%82%D8%A7%D8%B1%D8%A7%D8%AA/%D8%AC%D8%AF%D8%A9" target="_blank" rel="noopener">aqar.fm — جدة</a>. يتحدث المرصد كل أحد وثلاثاء.';

// download (downloads capability; the CSV ships next to the page)
(async()=>{ if(!D.csv_path) return; let dl=null; try{dl=await (window.claude&&window.claude.use?window.claude.use('downloads'):null);}catch(e){} if(!dl) return; const b=$('dl'); b.hidden=false;
 b.onclick=async()=>{b.disabled=true; b.textContent='جارٍ التجهيز…'; try{const r=await fetch(D.csv_path); if(!r.ok) throw new Error(r.status); const blob=await r.blob(); await dl.save({filename:`jeddah-market-${(D.run_at||'').slice(0,10)}.csv`,data:blob}); b.textContent='تم التنزيل';}
 catch(e){b.textContent=e&&e.code==='declined'?'أُلغي التنزيل':'تعذّر التنزيل';} finally{b.disabled=false; setTimeout(()=>b.textContent='تنزيل بيانات التشغيل (CSV)',3000);} };})();
})();
</script>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--report", help="report.md written by Claude (Arabic, ~half page)")
    ap.add_argument("--opp-notes", help="json {district: one-line note} written by Claude")
    ap.add_argument("--csv-path", default="data/latest.csv")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    D = json.load(open(a.data))
    # the page needs districts/metrics, not every listing
    D.pop("ticker", None)
    D["report"] = open(a.report).read() if a.report else ""
    if a.opp_notes:
        notes = json.load(open(a.opp_notes))
        for o in D.get("opportunities", []):
            if notes.get(o["district"]):
                o["note"] = notes[o["district"]]
    D["csv_path"] = a.csv_path
    from config import MIN_SAMPLE
    D["min_sample"] = MIN_SAMPLE
    payload = json.dumps(D, ensure_ascii=False).replace("</", "<\\/")
    open(a.out, "w").write(TEMPLATE.replace("__DATA__", payload))
    print(a.out)


if __name__ == "__main__":
    main()
