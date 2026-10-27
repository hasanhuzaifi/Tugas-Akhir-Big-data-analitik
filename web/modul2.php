<?php require __DIR__ . '/layout.php'; head('Modul 2', 'modul2.php');
if (!ready()) { foot(); exit; }
$s = (int)($_GET['s'] ?? 1); $s = $s >= 1 && $s <= 3 ? $s : 1;
$J = jenis_list(); $J[] = 'LAINNYA';
$prof = array_column(q('SELECT * FROM a_type_profile'), null, 'jenis');
usort($J, fn($a, $b) => ($prof[$b]['n'] ?? 0) <=> ($prof[$a]['n'] ?? 0));
$cor = array_combine($J, array_map('warna', $J));
$meta = array_column(q('SELECT k,v FROM a_meta'), 'v', 'k');
$kpi = array_column(q('SELECT k,v FROM kpi'), 'v', 'k');
$pilih = fn($v, $d) => in_array($v, $J, true) ? $v : $d;
$st = [1 => ['Di mana', 'Peta panas lokasi'], 2 => ['Apa dan kapan', 'Bandingkan jenis'], 3 => ['Besok', 'Prakiraan ML']]; ?>
<nav class="jalur" aria-label="Tiga analisis utama">
<?php foreach ($st as $n => [$t, $d]): ?><a href="?s=<?= $n ?>" data-n="<?= $n ?>" class="<?= $n < $s ? 'lalu' : '' ?>" <?= $n === $s ? 'aria-current="page"' : '' ?>><?= $t ?><small><?= $d ?></small></a><?php endforeach ?></nav>
<script>const WARNA=<?= json_encode($cor) ?>,PROFIL=<?= json_encode($prof, JSON_NUMERIC_CHECK) ?>;
const nm=j=>j==='SEMUA'?'Semua jenis':j.charAt(0)+j.slice(1).toLowerCase();
const nf=(n,d=0)=>Number(n).toLocaleString('id-ID',{maximumFractionDigits:d,minimumFractionDigits:d});
const qs=o=>{const u=new URLSearchParams(location.search);for(const k in o)o[k]?u.set(k,o[k]):u.delete(k);history.replaceState(null,'','?'+u)};
const HARI=['Min','Sen','Sel','Rab','Kam','Jum','Sab'];</script>

<?php if ($s === 1): $A = $_GET['jenis'] ?? 'SEMUA'; $A = $A === 'SEMUA' ? 'SEMUA' : $pilih($A, 'THEFT'); $B = $pilih($_GET['banding'] ?? '', ''); $mode = ($_GET['mode'] ?? '') === 'selisih' && $B ? 'selisih' : 'padat'; ?>
<h1>Di mana kejahatan terjadi</h1>
<div class="kes" id="kes" aria-live="polite"><h2>Kesimpulan</h2><ul id="kesl"><li>Memuat...</li></ul></div>
<details class="cara"><summary>Cara membaca peta ini</summary><p>Chicago dibagi menjadi sel sekitar 0,5 km. Makin merah dan gelap, makin banyak laporan di sel itu. Geser dan zoom dengan mouse atau jari, klik tombol layar penuh untuk memperbesar. <b>Halus</b> menggabungkan sel menjadi gradasi yang mulus, <b>Kotak</b> menampilkan tiap sel apa adanya (arahkan kursor untuk angkanya). Pilih jenis kedua lalu <b>Selisih</b> untuk melihat di mana dua jenis kejahatan berbeda pola. <?= nf($meta['rows_mapped']) ?> dari <?= nf($meta['rows']) ?> kejadian punya koordinat; <?= nf($meta['rows_no_coord']) ?> tanpa koordinat tidak dipetakan.</p></details>
<div class="ctl">
 <label class="f">Jenis kejahatan<select id="A"><option value="SEMUA">Semua jenis</option><?php foreach ($J as $j): ?><option value="<?= h($j) ?>" <?= $j === $A ? 'selected' : '' ?>><?= nama($j) ?></option><?php endforeach ?></select></label>
 <label class="f">Bandingkan dengan<select id="B"><option value="">(tidak ada)</option><?php foreach ($J as $j): ?><option value="<?= h($j) ?>" <?= $j === $B ? 'selected' : '' ?>><?= nama($j) ?></option><?php endforeach ?></select></label>
 <div role="group" aria-label="Mode peta" style="display:flex"><button class="btn" id="mP" aria-pressed="<?= $mode === 'padat' ? 'true' : 'false' ?>">Kepadatan</button><button class="btn" id="mS" aria-pressed="<?= $mode === 'selisih' ? 'true' : 'false' ?>" <?= $B ? '' : 'disabled' ?>>Selisih A lawan B</button></div>
 <div class="seg" role="group" aria-label="Gaya peta"><button class="btn" id="gH" aria-pressed="true">Halus</button><button class="btn" id="gK" aria-pressed="false">Kotak</button></div>
 <label class="rng">Jari-jari sebaran<input type="range" id="rad" min="8" max="40" value="18"></label>
 <label class="rng">Ambang tampil<input type="range" id="amb" min="0" max="60" value="0"></label>
 <button class="btn" id="reset">Reset</button>
</div>
<div class="grid side" style="margin-top:0">
 <div><div id="peta" role="img" aria-label="Peta panas kejadian kejahatan Chicago"></div><div class="legend" id="leg"></div></div>
 <div class="grid" style="margin-top:0;align-content:start">
  <section class="panel"><h3 id="jd">Ringkasan</h3><div class="kv" id="kv"></div><div id="ins"></div></section>
  <section class="panel"><h3>Titik terpanas</h3><p class="small muted" style="margin:0 0 4px">Klik untuk terbang ke lokasinya.</p><ol class="hot" id="hot"></ol></section>
  <section class="panel"><h3>District teratas</h3><div class="scroll"><table class="t" id="td"></table></div></section>
 </div>
</div>
<script>
const st={A:'<?= h($A) ?>',B:'<?= h($B) ?>',mode:'<?= $mode ?>',gaya:'halus'};
const map=Peta.buat('peta',{fs:true});
const cache={};
const ambil=async j=>cache[j]||(cache[j]=await (await fetch('api.php?a=grid&j='+encodeURIComponent(j))).json());
async function ringkas(){
  const js=[st.A,st.B].filter(x=>x&&x!=='SEMUA');
  const el=document.getElementById('td'),kv=document.getElementById('kv'),ins=document.getElementById('ins');
  document.getElementById('jd').textContent=nm(st.A)+(st.B?' lawan '+nm(st.B):'');
  let h='';for(const j of js){const p=PROFIL[j];h+=`<div><div class="big" style="color:${WARNA[j]}">${nf(p.n)}</div><div class="small muted">${nm(j)}, laporan</div></div>`}
  if(st.A==='SEMUA')h+=`<div><div class="big">${nf(<?= (int)$kpi['total'] ?>)}</div><div class="small muted">Semua jenis, laporan</div></div>`;
  kv.innerHTML=h;
  const q=js.length?js:Object.keys(WARNA);
  const d=await (await fetch('api.php?a=cmp&j='+encodeURIComponent(q.join(',')))).json();
  const by={};d.district.forEach(r=>{if(r.district!==null){(by[r.district]=by[r.district]||{})[r.jenis]=r.n}});
  const rows=Object.entries(by).map(([k,v])=>[k,v]);
  const val=v=>js.length?js.map(j=>v[j]||0):[Object.values(v).reduce((a,b)=>a+b,0)];
  rows.sort((a,b)=>val(b[1])[0]-val(a[1])[0]);
  const cols=js.length?js:['SEMUA'];
  el.innerHTML='<thead><tr><th>District</th>'+cols.map(j=>`<th class="r"><span class="dot" style="--c:${WARNA[j]||'#16202B'}"></span> ${nm(j)}</th>`).join('')+'</tr></thead><tbody>'+rows.slice(0,8).map(([k,v])=>`<tr><td>${k}</td>`+val(v).map(x=>`<td class="r">${nf(x)}</td>`).join('')+'</tr>').join('')+'</tbody>';
  let t='';
  js.forEach(j=>{const p=PROFIL[j];t+=`<p class="ins"><b>${nm(j)}</b>: terbanyak di district ${p.top_district} (${nf(p.top_share*100,1)}% dari semuanya), ${nf(p.arrest_rate*100,1)}% berujung penangkapan, ${nf(p.domestic_pct*100,1)}% kasus domestik.</p>`});
  ins.innerHTML=t||'<p class="muted small">Pilih satu jenis untuk melihat profilnya.</p>';
}
async function gambar(){
  qs({jenis:st.A==='SEMUA'?'':st.A,banding:st.B,mode:st.mode==='selisih'?'selisih':''});
  const leg=document.getElementById('leg');
  const a=await ambil(st.A);
  if(st.mode==='selisih'&&st.B){
    const b=await ambil(st.B),sa=a.reduce((x,c)=>x+c.n,0),sb=b.reduce((x,c)=>x+c.n,0),M={};
    a.forEach(c=>{M[c.la+'|'+c.lo]={la:c.la,lo:c.lo,a:c.n/sa,b:0,na:c.n,nb:0}});
    b.forEach(c=>{const k=c.la+'|'+c.lo;const m=M[k]=M[k]||{la:c.la,lo:c.lo,a:0,b:0,na:0,nb:0};m.b=c.n/sb;m.nb=c.n});
    const L=Object.values(M),mx=L.reduce((x,c)=>Math.max(x,Math.abs(c.a-c.b)),0)||1;
    Peta.gambar(map,L,c=>Peta.selisih(Math.sign(c.a-c.b)*Math.sqrt(Math.abs(c.a-c.b)/mx)),c=>`${nm(st.A)}: ${nf(c.na)}<br>${nm(st.B)}: ${nf(c.nb)}`);
    kes(a,b,sa,sb,L);
    leg.innerHTML=`<span>${nm(st.B)} lebih padat</span><i style="background:linear-gradient(90deg,#1478B5,#ECEFF2,#C4262E)"></i><span>${nm(st.A)} lebih padat</span>`;
  }else{
    const v=a.map(c=>c.n).sort((x,y)=>x-y),p=v[Math.floor(v.length*.98)]||1,amb=+document.getElementById('amb').value/100*p,aa=a.filter(c=>c.n>=amb);
    if(st.gaya==='halus')Peta.halus(map,aa.map(c=>[c.la,c.lo,Math.min(1,Math.sqrt(c.n/p))]),+document.getElementById('rad').value,Math.round(+document.getElementById('rad').value*1.1));
    else Peta.gambar(map,aa,c=>Peta.panas(Math.sqrt(c.n/p)),c=>`${nf(c.n)} laporan`);
    leg.innerHTML=`<span>sedikit</span><i style="background:linear-gradient(90deg,${Peta.STOPS.join(',')})"></i><span>${nf(p)}+ per sel</span>`;
    kes(a,null,0,0,null);hotspot(a);
  }
  ringkas();
}
function hotspot(a){
  const t=[...a].sort((x,y)=>y.n-x.n),tot=a.reduce((s,c)=>s+c.n,0),pk=[];
  for(const c of t){if(pk.every(q=>Math.hypot(q.la-c.la,(q.lo-c.lo)*.75)>.02))pk.push(c);if(pk.length>=5)break}
  document.getElementById('hot').innerHTML=pk.map((c,i)=>`<li><button data-la="${c.la}" data-lo="${c.lo}"><b class="n">${i+1}</b><span class="w">${nf(c.n)} laporan<small>${nf(c.n/tot*100,1)}% dari semua sel &middot; ${c.la.toFixed(3)}, ${c.lo.toFixed(3)}</small></span></button></li>`).join('');
  document.querySelectorAll('#hot button').forEach(b=>b.onclick=()=>map.flyTo([+b.dataset.la,+b.dataset.lo],15,{duration:.8}));
}
function kes(a,b,sa,sb,L){
  const el=document.getElementById('kesl'),tot=a.reduce((s,c)=>s+c.n,0),t=[...a].sort((x,y)=>y.n-x.n);
  let k=[];
  if(b){const dl=L.map(c=>[c,c.a-c.b]),ta=dl.sort((x,y)=>y[1]-x[1])[0],tb=dl[dl.length-1];
    k.push(`<b>${nm(st.A)}</b> dan <b>${nm(st.B)}</b> tidak menumpuk di tempat yang sama. Merah = ${nm(st.A)} lebih dominan, biru = ${nm(st.B)} lebih dominan.`);
    k.push(`Selisih terbesar: ${nm(st.A)} unggul di sekitar ${ta[0].la.toFixed(3)}, ${ta[0].lo.toFixed(3)}; ${nm(st.B)} unggul di sekitar ${tb[0].la.toFixed(3)}, ${tb[0].lo.toFixed(3)}.`);
  }else{
    const n10=Math.max(1,Math.ceil(a.length*.1)),s10=t.slice(0,n10).reduce((s,c)=>s+c.n,0);
    k.push(`<b>${nm(st.A)}</b>: ${nf(tot)} laporan di ${nf(a.length)} sel peta.`);
    k.push(`Terkonsentrasi: <b>10% sel teratas menampung ${nf(s10/tot*100,0)}%</b> dari seluruh laporan. Sisanya tersebar tipis.`);
    k.push(`Titik terpanas ada di sekitar ${t[0].la.toFixed(3)}, ${t[0].lo.toFixed(3)} (${nf(t[0].n)} laporan dalam satu sel). Klik daftar "Titik terpanas" di kanan untuk melihatnya.`);
  }
  el.innerHTML=k.map(x=>`<li>${x}</li>`).join('');
}
const sync=()=>{document.getElementById('mP').setAttribute('aria-pressed',st.mode!=='selisih');document.getElementById('mS').setAttribute('aria-pressed',st.mode==='selisih');document.getElementById('mS').disabled=!st.B};
document.getElementById('A').onchange=e=>{st.A=e.target.value;gambar()};
document.getElementById('B').onchange=e=>{st.B=e.target.value;if(!st.B)st.mode='padat';sync();gambar()};
document.getElementById('mP').onclick=()=>{st.mode='padat';sync();gambar()};
document.getElementById('mS').onclick=()=>{st.mode='selisih';sync();gambar()};
document.getElementById('reset').onclick=()=>{location.href='?s=1'};
const gs=()=>{document.getElementById('gH').setAttribute('aria-pressed',st.gaya==='halus');document.getElementById('gK').setAttribute('aria-pressed',st.gaya==='kotak');document.getElementById('rad').disabled=st.gaya!=='halus'};
document.getElementById('gH').onclick=()=>{st.gaya='halus';gs();gambar()};
document.getElementById('gK').onclick=()=>{st.gaya='kotak';gs();gambar()};
let tr;['rad','amb'].forEach(i=>document.getElementById(i).oninput=()=>{clearTimeout(tr);tr=setTimeout(gambar,120)});
gambar();
</script>

<?php elseif ($s === 2): $sel = array_values(array_filter(array_map(fn($x) => in_array($x, $J, true) ? $x : null, explode(',', $_GET['j'] ?? 'THEFT,BATTERY,ROBBERY')))); $sel = array_slice(array_unique($sel), 0, 4) ?: ['THEFT']; ?>
<h1>Apa dan kapan: bandingkan jenis</h1>
<div class="kes" aria-live="polite"><h2>Kesimpulan</h2><ul id="kesl"><li>Memuat...</li></ul></div>
<details class="cara"><summary>Cara membaca halaman ini</summary><p>Pilih 1 sampai 4 jenis kejahatan, atau pakai pilihan cepat. <b>Tren</b> diindeks 100 pada bulan penuh pertama supaya jenis besar dan kecil bisa dibandingkan: garis di atas 100 berarti lebih banyak dari awal. <b>Peta jam</b> menunjukkan kapan jenis itu paling sering dilaporkan (baris = hari, kolom = jam; arahkan kursor untuk angkanya). <b>Korelasi</b> mengukur apakah dua jenis naik turun bersamaan di hari yang sama (1 = selalu bersamaan); korelasi bukan sebab-akibat.</p></details>
<div class="ctl" style="margin-bottom:0"><span class="small muted">Pilihan cepat:</span>
 <button class="btn" data-pre="THEFT,BATTERY,ROBBERY">Pencurian dan kekerasan</button>
 <button class="btn" data-pre="NARCOTICS,CRIMINAL DAMAGE,DECEPTIVE PRACTICE">Narkotika, perusakan, penipuan</button>
 <button class="btn" data-pre="BURGLARY,MOTOR VEHICLE THEFT,THEFT">Properti dan kendaraan</button></div>
<fieldset class="ctl" style="border:0;padding:0" id="pil"><legend class="small muted">Jenis (maks. 4)</legend>
<?php foreach ($J as $j): ?><label class="chip" style="--c:<?= $cor[$j] ?>"><input type="checkbox" value="<?= h($j) ?>" <?= in_array($j, $sel, true) ? 'checked' : '' ?>><span class="dot"></span><?= nama($j) ?></label><?php endforeach ?></fieldset>
<div class="grid g2" style="margin-top:0">
 <section class="panel" style="grid-column:1/-1"><h3>Tren bulanan (indeks 100)</h3><div class="cv"><canvas id="cT" aria-label="Tren bulanan"></canvas></div></section>
 <section class="panel" style="grid-column:1/-1"><h3>Profil</h3><div class="scroll"><table class="t" id="tp"></table></div><div id="ins"></div></section>
 <div id="hms" style="display:contents"></div>
 <section class="panel" style="grid-column:1/-1"><h3>Korelasi harian antarjenis</h3><p class="small muted">1 = naik turun bersamaan. Dihitung dari jumlah harian di seluruh kota.</p><div class="scroll"><table class="t" id="tc"></table></div></section>
</div>
<script>
let ch;
const pilih=()=>[...document.querySelectorAll('#pil input:checked')].map(i=>i.value);
const boxes=[...document.querySelectorAll('#pil input')];
document.querySelectorAll('[data-pre]').forEach(x=>x.onclick=()=>{const w=x.dataset.pre.split(',');boxes.forEach(b=>b.checked=w.includes(b.value));muat()});
boxes.forEach(b=>b.onchange=()=>{if(pilih().length>4)b.checked=false;if(!pilih().length)b.checked=true;muat()});
async function muat(){
  const js=pilih();qs({j:js.join(',')});
  const d=await (await fetch('api.php?a=cmp&j='+encodeURIComponent(js.join(',')))).json();
  // tren: buang bulan pertama dan terakhir (parsial)
  const bl=[...new Set(d.bulan.map(r=>r.bulan))].sort().slice(1,-1);
  const ds=js.map(j=>{const m={};d.bulan.filter(r=>r.jenis===j).forEach(r=>m[r.bulan]=r.n);const b0=m[bl[0]]||1;return {label:nm(j),data:bl.map(x=>(m[x]||0)/b0*100),borderColor:WARNA[j],backgroundColor:WARNA[j],borderWidth:2.5,pointRadius:0,tension:.25}});
  if(ch)ch.destroy();
  ch=new Chart(document.getElementById('cT'),{type:'line',data:{labels:bl,datasets:ds},options:{maintainAspectRatio:false,animation:{duration:400},scales:{x:{ticks:{maxTicksLimit:8}},y:{title:{display:true,text:'indeks (bulan pertama = 100)'}}},plugins:{legend:{position:'bottom'}}}});
  // profil
  const P=js.map(j=>d.profil.find(p=>p.jenis===j));
  document.getElementById('tp').innerHTML='<thead><tr><th>Jenis</th><th class="r">Laporan</th><th class="r">Penangkapan</th><th class="r">Domestik</th><th class="r">District teratas</th></tr></thead><tbody>'+P.map(p=>`<tr><td><span class="dot" style="--c:${WARNA[p.jenis]}"></span> ${nm(p.jenis)}</td><td class="r">${nf(p.n)}</td><td class="r">${nf(p.arrest_rate*100,1)}%</td><td class="r">${nf(p.domestic_pct*100,1)}%</td><td class="r">${p.top_district} (${nf(p.top_share*100,1)}%)</td></tr>`).join('')+'</tbody>';
  // heatmap jam x hari per jenis
  document.getElementById('hms').innerHTML=js.map(j=>`<section class="panel"><h3 style="color:${WARNA[j]}">${nm(j)}: jam dan hari</h3><div class="hm" id="h_${js.indexOf(j)}"></div></section>`).join('');
  const puncak=[],kesA=[];
  js.forEach((j,i)=>{const g=Array.from({length:8},()=>Array(24).fill(0));d.jam.filter(r=>r.jenis===j).forEach(r=>g[r.dow][r.hr]=r.n);
    const tot=g.flat().reduce((a,b)=>a+b,0);let mx=0,pd=1,ph=0;for(let a=1;a<=7;a++)for(let b=0;b<24;b++)if(b!==0&&g[a][b]>mx){mx=g[a][b];pd=a;ph=b}
    const mj=Math.max(...g.flat().filter((_,k)=>k%24!==0));
    let h='<div></div>'+Array.from({length:24},(_,k)=>`<div style="text-align:center">${k%3?'':k}</div>`).join('');
    for(let a=1;a<=7;a++){h+=`<div>${HARI[a-1]}</div>`;for(let b=0;b<24;b++){const v=g[a][b];h+=`<div class="c" title="${HARI[a-1]} ${b}.00: ${nf(v)}" style="background:${Peta.panas(Math.sqrt(v/mj))}"></div>`}}
    document.getElementById('h_'+i).innerHTML=h;
    const jm=Array(24).fill(0);for(let a=1;a<=7;a++)for(let b=1;b<24;b++)jm[b]+=g[a][b];const sore=[16,17,18,19,20,21].reduce((s,b)=>s+jm[b],0),all=jm.reduce((a,b)=>a+b,0)||1;
    kesA.push({j,pd,ph,sore:sore/all});
    puncak.push(`<b>${nm(j)}</b> paling sering ${['','Minggu','Senin','Selasa','Rabu','Kamis','Jumat','Sabtu'][pd]} pukul ${ph}.00 (lonjakan 00.00 diabaikan: itu waktu bawaan data).`)});
  document.getElementById('ins').innerHTML=puncak.map(x=>`<p class="ins">${x}</p>`).join('');
  // kesimpulan
  const HR=['','Minggu','Senin','Selasa','Rabu','Kamis','Jumat','Sabtu'],kl=[];
  const tr=js.map(j=>{const m={};d.bulan.filter(r=>r.jenis===j).forEach(r=>m[r.bulan]=r.n);return {j,v:(m[bl[bl.length-1]]||0)/(m[bl[0]]||1)*100}});
  kesA.forEach(k=>{const p=P.find(x=>x.jenis===k.j),t=tr.find(x=>x.j===k.j).v;
    kl.push(`<b>${nm(k.j)}</b>: puncak ${HR[k.pd]} pukul ${k.ph}.00; ${nf(k.sore*100,0)}% laporan terjadi jam 16-21; penangkapan ${nf(p.arrest_rate*100,1)}%; tren ${t>=105?'naik':t<=95?'turun':'datar'} (indeks ${nf(t,0)} dibanding awal).`)});
  if(js.length>1){const ar=[...P].sort((a,b)=>b.arrest_rate-a.arrest_rate);kl.push(`Penangkapan tertinggi: <b>${nm(ar[0].jenis)}</b> (${nf(ar[0].arrest_rate*100,1)}%), terendah <b>${nm(ar[ar.length-1].jenis)}</b> (${nf(ar[ar.length-1].arrest_rate*100,1)}%).`)}
  document.getElementById('kesl').innerHTML=kl.map(x=>`<li>${x}</li>`).join('');
  // korelasi
  const C=(a,b)=>(d.korelasi.find(r=>r.a===a&&r.b===b)||{}).corr;
  document.getElementById('tc').innerHTML='<thead><tr><th></th>'+js.map(j=>`<th class="r">${nm(j)}</th>`).join('')+'</tr></thead><tbody>'+js.map(a=>`<tr><td>${nm(a)}</td>`+js.map(b=>{const c=C(a,b);return `<td class="r" style="background:${Peta.panas(Math.max(0,c))};color:${c>.6?'#fff':'inherit'}">${nf(c,2)}</td>`}).join('')+'</tr>').join('')+'</tbody>';
}
muat();
</script>

<?php else:
$weeklyMeta = q('SELECT 1 FROM kpi LIMIT 1');
$lag = q('SELECT lg,corr FROM lag_corr ORDER BY lg');
$ext = q('SELECT factor,lg,corr FROM ext_corr WHERE lg IN (7,30) ORDER BY factor,lg'); $ext0 = []; foreach ($ext as $r) $ext0[$r['factor']][$r['lg']] = $r['corr'];
$models = q('SELECT * FROM model_metrics ORDER BY rmse');
$imp = q('SELECT fitur,nilai FROM importance ORDER BY nilai DESC LIMIT 8');
$pred = q('SELECT day, SUM(n) a, SUM(prediction) p FROM test_pred GROUP BY day ORDER BY day');
$risk = q('SELECT * FROM next_day WHERE district<>61 AND pred>5 ORDER BY pred DESC');
$mrT = (int)one('SELECT SUM(n) s FROM mr_dhh')['s']; $sparkT = (int)$kpi['total'];
$best = $models[0]; $base = array_values(array_filter($models, fn($m) => $m['model'] === 'baseline_mean7'))[0];
$gain = ($base['rmse'] - $best['rmse']) / $base['rmse'] * 100;
$lab = ['baseline_mean7' => 'Rata-rata 7 hari (pembanding)', 'rf_base' => 'RandomForest, kejahatan saja', 'rf_full' => 'RandomForest + 311 + kecelakaan', 'gbt_base' => 'GBT, kejahatan saja', 'gbt_full' => 'GBT + 311 + kecelakaan'];
$tinggi = count(array_filter($risk, fn($r) => $r['risk'] === 'Tinggi')); ?>
<h1>Besok: prakiraan per district</h1>
<div class="kes"><h2>Kesimpulan</h2><ul>
 <li>Model <b>RandomForest</b> memprakirakan jumlah kejadian per district per hari dengan kesalahan rata-rata sekitar <b><?= nf($best['mae'] ?? 0, 1) ?> kejadian</b>, lebih baik <b><?= nf($gain ?? 0, 1) ?>%</b> dari tebakan "sama dengan rata-rata 7 hari".</li>
 <li>Yang paling menentukan adalah <b>kebiasaan district itu sendiri</b>: rata-rata 30 hari terakhir. Data 311 dan kecelakaan <b>tidak</b> membantu, jadi model sederhana justru terbaik.</li>
 <li>Prakiraan besok dikelompokkan Rendah, Sedang, Tinggi dengan membandingkannya ke sejarah district itu sendiri, bukan ke district lain.</li></ul></div>
<details class="cara"><summary>Cara membaca halaman ini</summary><p>Model dilatih dengan <?= nf($kpi['train_rows']) ?> baris dan diuji pada <?= nf($kpi['test_rows']) ?> baris (12 bulan terakhir, dipisah menurut waktu supaya tidak "mengintip" masa depan). <b>Klik kartu district</b> untuk detailnya: posisi prakiraan terhadap kisaran normal, riwayat prakiraan lawan kenyataan, dan jam rawan. <b>Tebak dulu</b> mengajak Anda menebak lalu membandingkan dengan model. Prakiraan bukan kepastian.</p></details>
<div class="grid g3">
 <section class="panel"><div class="big" style="color:var(--bendera)"><?= nf($lag[0]['corr'], 2) ?></div><b>Kemarin menentukan hari ini</b><p class="small muted">Korelasi dengan 1 hari sebelumnya; 7 hari <?= nf($lag[6]['corr'], 2) ?>. Rata-rata 30 hari terakhir adalah fitur terpenting.</p></section>
 <section class="panel"><div class="big"><?= nf($gain, 1) ?>%</div><b>Lebih akurat dari tebakan rata-rata</b><p class="small muted">RMSE <?= nf($best['rmse'], 2) ?> lawan <?= nf($base['rmse'], 2) ?>. Menambah data 311 dan kecelakaan tidak membantu.</p></section>
 <section class="panel"><div class="big">District <?= $risk[0]['district'] ?></div><b>Prakiraan tertinggi pada <?= h($risk[0]['day']) ?></b><p class="small muted"><?= nf($risk[0]['pred'], 1) ?> kejadian, kategori <?= h($risk[0]['risk']) ?> (<?= $tinggi ?> district Tinggi). Kategori dibandingkan persentil 33 dan 66 sejarah district itu sendiri.</p></section>
</div>
<h2 style="margin-top:32px">Kartu risiko <span class="small muted">(klik untuk detail)</span></h2>
<div class="ctl" style="margin:12px 0 0"><div class="seg" role="group" aria-label="Saring risiko"><button class="btn" data-f="" aria-pressed="true">Semua</button><button class="btn" data-f="Tinggi" aria-pressed="false">Tinggi</button><button class="btn" data-f="Sedang" aria-pressed="false">Sedang</button><button class="btn" data-f="Rendah" aria-pressed="false">Rendah</button></div>
<label class="f">Urutkan<select id="urut"><option value="pred">Prakiraan tertinggi</option><option value="d">Nomor district</option></select></label></div>
<div class="grid" id="kartu" style="grid-template-columns:repeat(auto-fill,minmax(130px,1fr));margin-top:12px"><?php foreach ($risk as $r): ?>
<button class="rk rk-<?= h($r['risk']) ?>" data-d="<?= $r['district'] ?>" data-r="<?= h($r['risk']) ?>" data-p="<?= $r['pred'] ?>"><div class="small">District <?= $r['district'] ?></div><div class="big"><?= nf($r['pred'], 1) ?></div><div class="small"><b><?= h($r['risk']) ?></b></div></button><?php endforeach ?></div>
<p class="small muted">Prakiraan berbasis pola agregat historis, bukan kepastian.</p>
<section class="panel" id="det" style="margin-top:16px" hidden><h3 id="dj">District</h3>
 <div class="grid g2" style="margin-top:8px">
  <div><div class="mlab"><span>Rendah</span><span>Sedang</span><span>Tinggi</span></div><div class="meter" id="mt"></div><p id="dk" class="small"></p>
   <h3 style="font-size:18px;margin-top:12px">Jam rawan (semua hari)</h3><div class="cv" style="height:170px"><canvas id="cJ"></canvas></div></div>
  <div><h3 style="font-size:18px">Prakiraan lawan kenyataan (30 hari terakhir uji)</h3><div class="cv" style="height:260px"><canvas id="cS"></canvas></div></div>
 </div></section>
<section class="panel" style="margin-top:16px"><h3>Tebak dulu: Anda lawan model</h3>
 <p class="small muted">Pilih district. Anda lihat 7 hari sebelumnya pada hari acak dari periode uji, tebak jumlah kejadian hari itu, lalu bandingkan dengan model dan rata-rata 7 hari.</p>
 <div class="ctl" style="margin:8px 0"><label class="f">District<select id="gd"><?php foreach ($risk as $r): ?><option value="<?= $r['district'] ?>">District <?= $r['district'] ?></option><?php endforeach ?></select></label><button class="btn pri" id="gmulai">Soal baru</button></div>
 <div class="tebak" id="soal" hidden><div><span class="small muted">7 hari sebelumnya:</span><div class="hist" id="gh"></div></div>
  <div class="ctl" style="margin:0"><label class="f">Tebakan Anda (kejadian pada <span id="gtgl"></span>)<input type="number" id="gt" min="0" max="200" style="min-height:40px;padding:6px 10px;border:1px solid var(--aspal);border-radius:2px;width:140px"></label><button class="btn" id="gcek">Cek</button></div>
  <div id="gsk" class="small" aria-live="polite"></div></div></section>
<div class="grid g2">
 <section class="panel"><h3>Perbandingan model</h3><div class="scroll"><table class="t"><thead><tr><th>Model</th><th class="r">MAE</th><th class="r">RMSE</th><th class="r">R2</th></tr></thead><tbody>
 <?php foreach ($models as $i => $m): ?><tr style="<?= $i === 0 ? 'font-weight:600' : '' ?>"><td><?= $lab[$m['model']] ?? h($m['model']) ?></td><td class="r"><?= nf($m['mae'], 2) ?></td><td class="r"><?= nf($m['rmse'], 2) ?></td><td class="r"><?= nf($m['r2'], 3) ?></td></tr><?php endforeach ?></tbody></table></div></section>
 <section class="panel"><h3>Fitur terpenting (GBT)</h3><div class="cv"><canvas id="cI"></canvas></div></section>
 <section class="panel" style="grid-column:1/-1"><h3>Aktual lawan prediksi, 12 bulan uji</h3><div class="cv"><canvas id="cP"></canvas></div></section>
 <section class="panel"><h3>Pengaruh hari lampau</h3><div class="cv"><canvas id="cL"></canvas></div></section>
 <section class="panel"><h3>Data pendukung: 311 dan kecelakaan</h3><div class="cv"><canvas id="cE"></canvas></div><p class="small muted">Dua dataset ini diuji sebagai petunjuk tambahan (keluhan warga dan kecelakaan per district per hari). Hasilnya lemah (di bawah 0,35) dan tidak memperbaiki prakiraan, jadi dicatat sebagai temuan, bukan dipakai.</p></section>
 <section class="panel" style="grid-column:1/-1"><h3>MapReduce (YARN) dan PySpark</h3><div class="kv"><div><div class="big"><?= nf($mrT) ?></div><div class="small muted">Total MapReduce (37 map, 2 reduce)</div></div><div><div class="big"><?= nf($sparkT) ?></div><div class="small muted">Total PySpark</div></div><div><div class="big" style="color:var(--bendera)"><?= nf($mrT - $sparkT) ?></div><div class="small muted">Selisih = hari parsial yang dibuang Spark</div></div></div></section>
</div>
<h2 style="margin-top:32px">Jalankan ulang</h2>
<div class="ctl" style="margin-top:12px"><?php foreach (['bi' => 'BI', 'mapreduce' => 'MapReduce', 'analisis' => 'Analisis lokasi', 'ml' => 'Latih ML', 'export' => 'Ekspor'] as $j => $t): ?><button class="btn" data-job="<?= $j ?>"><?= $t ?></button><?php endforeach ?><button class="btn pri" id="sync">Muat ulang database</button></div>
<pre class="log" id="log" aria-live="polite">Belum ada job dijalankan.</pre>
<script>
const W=<?= json_encode(['L' => $lag, 'E' => $ext0, 'I' => $imp, 'P' => $pred], JSON_NUMERIC_CHECK) ?>;
const mk=(id,cfg)=>new Chart(document.getElementById(id),Object.assign({options:{}},cfg,{options:Object.assign({maintainAspectRatio:false},cfg.options)}));
mk('cL',{type:'bar',data:{labels:W.L.map(r=>r.lg),datasets:[{data:W.L.map(r=>r.corr),backgroundColor:'#C4262E'}]},options:{plugins:{legend:{display:false}},scales:{y:{min:0,max:.8},x:{title:{display:true,text:'hari sebelumnya'}}}}});
const F=Object.keys(W.E);mk('cE',{type:'bar',data:{labels:F,datasets:[{label:'lag 7',data:F.map(f=>W.E[f][7]),backgroundColor:'#00A1DE'},{label:'lag 30',data:F.map(f=>W.E[f][30]),backgroundColor:'#16202B'}]}});
mk('cI',{type:'bar',data:{labels:W.I.map(r=>r.fitur),datasets:[{data:W.I.map(r=>r.nilai),backgroundColor:'#C4262E'}]},options:{indexAxis:'y',plugins:{legend:{display:false}}}});
mk('cP',{type:'line',data:{labels:W.P.map(r=>r.day),datasets:[{label:'Aktual',data:W.P.map(r=>r.a),borderColor:'#7A8794',borderWidth:1.5,pointRadius:0},{label:'Prediksi',data:W.P.map(r=>r.p),borderColor:'#C4262E',borderWidth:2,pointRadius:0}]},options:{scales:{x:{ticks:{maxTicksLimit:8}}}}});
// ---- penjelajah district ----
let cJ,cS;
document.querySelectorAll('[data-f]').forEach(b=>b.onclick=()=>{document.querySelectorAll('[data-f]').forEach(x=>x.setAttribute('aria-pressed',x===b));const f=b.dataset.f;document.querySelectorAll('#kartu .rk').forEach(k=>k.hidden=!!f&&k.dataset.r!==f)});
document.getElementById('urut').onchange=e=>{const k=document.getElementById('kartu');[...k.children].sort((a,b)=>e.target.value==='d'?a.dataset.d-b.dataset.d:b.dataset.p-a.dataset.p).forEach(x=>k.appendChild(x))};
document.querySelectorAll('#kartu .rk').forEach(k=>k.onclick=()=>buka(k.dataset.d));
async function buka(d){
  const r=await (await fetch('api.php?a=district&d='+d)).json(),n=r.next,pan=document.getElementById('det');pan.hidden=false;
  document.getElementById('dj').textContent='District '+d+': prakiraan '+nf(n.pred,1)+' kejadian pada '+n.day;
  const hi=Math.max(n.p66*1.4,n.pred*1.15),pc=v=>Math.min(100,v/hi*100);
  document.getElementById('mt').innerHTML=`<i class="m1" style="width:${pc(n.p33)}%"></i><i class="m2" style="width:${pc(n.p66)-pc(n.p33)}%"></i><i class="m3" style="flex:1"></i><u style="left:calc(${pc(n.pred)}% - 2px)"></u>`;
  const tot=r.total;
  document.getElementById('dk').innerHTML=`Kisaran normal district ini: <b>${n.p33}</b> sampai <b>${n.p66}</b> kejadian per hari. Prakiraan <b>${nf(n.pred,1)}</b> berarti <b class="${n.risk==='Tinggi'?'lose':n.risk==='Rendah'?'win':''}">${n.risk}</b>. Sepanjang periode: ${nf(tot.n)} laporan, penangkapan ${nf(tot.arrest_rate*100,1)}%.`;
  const jm=Array(24).fill(0);r.jam.forEach(x=>{if(x.hr>0)jm[x.hr]+=x.n});const mx=Math.max(...jm.slice(1));
  if(cJ)cJ.destroy();cJ=new Chart(document.getElementById('cJ'),{type:'bar',data:{labels:jm.map((_,i)=>i),datasets:[{data:jm.map((v,i)=>i?v:null),backgroundColor:jm.map((v,i)=>i&&v===mx?'#C4262E':'#9fb3c4')}]},options:{maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{title:{display:true,text:'jam'}}}}});
  const sr=r.seri.slice(-30);if(cS)cS.destroy();
  cS=new Chart(document.getElementById('cS'),{type:'line',data:{labels:sr.map(x=>x.day.slice(5)),datasets:[{label:'Kenyataan',data:sr.map(x=>x.n),borderColor:'#16202B',borderWidth:2,pointRadius:2},{label:'Prakiraan model',data:sr.map(x=>x.p),borderColor:'#C4262E',borderWidth:2,pointRadius:0,borderDash:[5,3]}]},options:{maintainAspectRatio:false,plugins:{legend:{position:'bottom'}},scales:{x:{ticks:{maxTicksLimit:8}}}}});
  pan.scrollIntoView({behavior:'smooth',block:'nearest'});
}
// ---- tebak dulu ----
let soal=null;
document.getElementById('gmulai').onclick=async()=>{
  const d=document.getElementById('gd').value,r=await (await fetch('api.php?a=district&d='+d)).json(),s=r.seri,i=7+Math.floor(Math.random()*(s.length-7)),h=s.slice(i-7,i);
  soal={a:s[i].n,m:s[i].p,b:h.reduce((x,y)=>x+y.n,0)/7,t:s[i].day};
  document.getElementById('soal').hidden=false;document.getElementById('gtgl').textContent=soal.t;document.getElementById('gt').value='';document.getElementById('gsk').textContent='';
  document.getElementById('gh').innerHTML=h.map(x=>`<span>${x.day.slice(5)}: <b>${x.n}</b></span>`).join('');
};
document.getElementById('gcek').onclick=()=>{
  const gi=document.getElementById('gt');if(!soal||gi.value==='')return;const g=+gi.value;
  const e=[['Anda',Math.abs(g-soal.a)],['Model',Math.abs(soal.m-soal.a)],['Rata-rata 7 hari',Math.abs(soal.b-soal.a)]],mn=Math.min(...e.map(x=>x[1]));
  document.getElementById('gsk').innerHTML=`Kenyataan: <b>${soal.a}</b> kejadian. Tebakan Anda ${g} (selisih ${nf(e[0][1],1)}), model ${nf(soal.m,1)} (selisih ${nf(e[1][1],1)}), rata-rata 7 hari ${nf(soal.b,1)} (selisih ${nf(e[2][1],1)}). <b class="${e[0][1]===mn?'win':'lose'}">${e[0][1]===mn?'Anda terdekat!':'Terdekat: '+e.find(x=>x[1]===mn)[0]+'.'}</b>`;
};
const log=document.getElementById('log');let tm;
const LV='http://localhost:8010/api'; // Laravel lapisan job (ADR 0008)
async function poll(j){const r=await (await fetch(LV+'/jobs/'+j+'/log')).json();log.textContent=r.log||'(menunggu keluaran)';if(!r.done)tm=setTimeout(()=>poll(j),2500)}
document.querySelectorAll('[data-job]').forEach(b=>b.onclick=async()=>{clearTimeout(tm);log.textContent='Memulai...';await fetch(LV+'/jobs/'+b.dataset.job,{method:'POST'});poll(b.dataset.job)});
document.getElementById('sync').onclick=async()=>{log.textContent='Mengimpor...';await fetch('jobs.php?a=sync');location.reload()};
</script>
<?php endif;
foot();
