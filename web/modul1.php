<?php require __DIR__ . '/layout.php'; head('Modul 1', 'modul1.php');
$pre = ready() ? q('SELECT * FROM preprocess ORDER BY rows_in DESC') : [];
$nama = ['crime' => 'Kejahatan', 'crashes' => 'Kecelakaan', '311' => 'Layanan 311'];
$tot_in = array_sum(array_column($pre, 'rows_in')); $tot_out = array_sum(array_column($pre, 'rows_final')); ?>
<h1>Modul 1: Import data dan preprocessing</h1>
<p class="muted" style="max-width:70ch">Tempel link API Chicago Data Portal. NiFi mengunduhnya ke HDFS, MapReduce di YARN membersihkannya, lalu Spark menyiapkan Parquet untuk analisis.</p>

<ol class="alur" id="alur" aria-label="Tahap pipeline">
<?php foreach (['web' => 'Link dari web', 'nifi' => 'NiFi unduh', 'hdfs' => 'HDFS raw', 'prep' => 'MapReduce prep', 'parquet' => 'Parquet', 'analisis' => 'Analisis', 'ml' => 'ML', 'export' => 'MySQL'] as $k => $t): ?><li data-k="<?= $k ?>"><?= $t ?></li><?php endforeach ?></ol>

<section class="panel" style="margin-top:16px"><h3>1. Pilih data yang diambil (NiFi)</h3>
<p class="small muted">Tidak perlu mengetik link. Pilih satu dataset atau <b>Semua dataset</b>, lalu satu bulan atau rentang kustom; web menyusun link API Chicago Data Portal untuk Anda, lalu NiFi mengunduhnya ke HDFS. Memilih bulan yang sudah ada berarti baris yang sama dibuang saat deduplikasi.</p>
<div class="seg" role="radiogroup" aria-label="Dataset" id="dsp" style="margin-top:8px;flex-wrap:wrap">
 <button class="btn" data-ds="crime" aria-pressed="true">Kejahatan</button><button class="btn" data-ds="crashes" aria-pressed="false">Kecelakaan lalu lintas</button><button class="btn" data-ds="311" aria-pressed="false">Layanan 311</button><button class="btn" data-ds="all" aria-pressed="false">Semua dataset (3)</button></div>
<div class="seg" role="radiogroup" aria-label="Mode periode" id="mdp" style="margin-top:8px"><button class="btn" data-m="bulan" aria-pressed="true">Satu bulan</button><button class="btn" data-m="kustom" aria-pressed="false">Rentang kustom</button></div>
<div class="ctl" id="pb"><label class="f">Bulan<select id="bulan" style="min-height:40px"></select></label></div>
<div id="pk" hidden><div class="ctl"><label class="f">Dari tanggal<input id="dari" type="date" min="2023-10-25" max="2026-10-15" style="min-height:40px;border:1px solid var(--aspal);padding:6px 10px;font:inherit"></label>
<label class="f">Sampai (tidak termasuk)<input id="sampai" type="date" min="2023-10-26" max="2026-10-16" style="min-height:40px;border:1px solid var(--aspal);padding:6px 10px;font:inherit"></label></div>
<p class="small muted" style="margin:0">Rentang kustom untuk uji coba: maksimal 366 hari per dataset, atau 92 hari bila memilih Semua dataset. Dataset 311 sangat besar, jadi rentang panjang memakan waktu dan memori.</p></div>
<p class="small muted" style="margin:8px 0 0">Link yang akan dikirim:</p><div id="url" class="small" style="word-break:break-all"></div>
<div class="ctl"><button class="btn pri" id="kirim">Kirim ke NiFi</button><button class="btn pri" id="proses" disabled>Proses (pipeline)</button></div>
<div id="info" class="small" aria-live="polite"></div>
<div class="ctl"><a class="btn" href="https://localhost:8443/nifi" target="_blank" rel="noopener">Buka NiFi</a><a class="btn" href="http://localhost:9870" target="_blank" rel="noopener">Buka HDFS UI</a><button class="btn" data-job="hdfs">Cek ukuran HDFS</button></div>
<?php if ($pre): ?><div class="grid g3"><?php foreach ($pre as $r): ?>
<div style="border-left:4px solid var(--danau);padding-left:12px"><div class="small muted"><?= $nama[$r['dataset']] ?? $r['dataset'] ?></div><div class="big"><?= nf($r['hdfs_mb'], 1) ?> MB</div><div class="small muted">/data/raw/<?= h($r['dataset']) ?></div></div><?php endforeach ?></div>
<p class="small">Total mentah: <b><?= nf(array_sum(array_column($pre, 'hdfs_mb')) / 1000, 2) ?> GB</b> (syarat 1,5 sampai 3 GB).</p><?php endif ?></section>

<section class="panel" style="margin-top:16px"><h3>2. Preprocessing (MapReduce di YARN)</h3>
<p class="small muted">Mapper membaca CSV, mengubah tipe, membuat fitur waktu, dan membuang baris di luar rentang. Reducer menyisakan satu baris per ID (versi terbaru) dan menghitung duplikat lewat counter Hadoop. Hasil TSV di /data/clean, lalu Spark menyimpannya sebagai Parquet di /data/processed tanpa hari terakhir yang belum lengkap.</p>
<div class="ctl"><button class="btn" data-job="prep" data-ds="all">Jalankan MapReduce prep</button><button class="btn" data-job="parquet" data-ds="all">TSV ke Parquet</button><a class="btn" href="http://localhost:18088" target="_blank" rel="noopener">YARN UI</a></div>
<?php if ($pre): ?><div class="scroll" style="margin-top:12px"><table class="t"><thead><tr><th>Dataset</th><th class="r">Baris masuk</th><th class="r">Duplikat</th><th>Hari parsial dibuang</th><th class="r">Baris akhir</th></tr></thead><tbody>
<?php foreach ($pre as $r): ?><tr><td><?= $nama[$r['dataset']] ?? h($r['dataset']) ?></td><td class="r"><?= nf($r['rows_in']) ?></td><td class="r"><?= nf($r['dup_identical'] + $r['dup_key']) ?></td><td><?= h($r['dropped_day']) ?></td><td class="r"><?= nf($r['rows_final']) ?></td></tr><?php endforeach ?>
<tr style="font-weight:600"><td>Total</td><td class="r"><?= nf($tot_in) ?></td><td></td><td></td><td class="r"><?= nf($tot_out) ?></td></tr></tbody></table></div>
<p class="small muted">Selisih <?= nf($tot_in - $tot_out) ?> baris adalah duplikat dan hari parsial yang dibuang agar hitungan harian tidak menipu.</p><?php endif ?></section>

<section class="panel" style="margin-top:16px"><h3>3. Simpan ke database</h3>
<p class="small muted">Hasil diekspor dari WSL lalu diimpor ke MySQL Laragon (database <code>chicago_bigdata</code>).</p>
<div class="ctl"><button class="btn" data-job="export">Ekspor dari Spark</button><button class="btn" id="sync">Impor ke MySQL</button></div></section>

<div id="toast" aria-live="polite"></div>
<section style="margin-top:16px"><h3>Log job</h3><pre id="log" class="log" aria-live="polite">Belum ada job dijalankan.</pre>
<p class="small muted">Job butuh WSL dengan HDFS (dan YARN untuk MapReduce) hidup. Bila mati, web tetap menampilkan hasil tersimpan.</p></section>
<script>
const log=document.getElementById('log'),info=document.getElementById('info'),$=id=>document.getElementById(id);let tm,ds='crime';
const KOL={crime:'ijzp-q8t2',crashes:'85ca-t3if','311':'v6vf-nfxy'},KD={crime:'date',crashes:'crash_date','311':'created_date'},NM={crime:'Kejahatan',crashes:'Kecelakaan','311':'Layanan 311'};
const BLN=['Jan','Feb','Mar','Apr','Mei','Jun','Jul','Agu','Sep','Okt','Nov','Des'],pad=n=>String(n).padStart(2,'0');
function notif(t,jenis='info'){const d=document.createElement('div');d.className='tst '+jenis;d.setAttribute('role',jenis==='gagal'?'alert':'status');d.textContent=t;$('toast').appendChild(d);setTimeout(()=>d.remove(),jenis==='gagal'?9000:5000);const l=log.textContent;log.textContent=(l.startsWith('Belum ada')?'':l+'\n')+'['+new Date().toLocaleTimeString('id-ID')+'] '+t}
for(let y=2026,m=10;!(y===2023&&m<10);m--){if(m<1){m=12;y--}const o=document.createElement('option');o.value=y+'-'+pad(m);o.textContent=BLN[m-1]+' '+y+(y===2026&&m===10?' (sampai 15 Okt)':'');$('bulan').appendChild(o)}
$('bulan').value='2026-09';
let mode='bulan';
const daftar=()=>ds==='all'?['crime','crashes','311']:[ds];
const rentang=()=>{if(mode==='kustom')return $('dari').value&&$('sampai').value?[$('dari').value,$('sampai').value]:null;const[y,m]=$('bulan').value.split('-').map(Number);return[y+'-'+pad(m)+'-01',(m===12?y+1:y)+'-'+pad(m===12?1:m+1)+'-01']};
const urlFor=(k,[d,e])=>'https://data.cityofchicago.org/resource/'+KOL[k]+".csv?$where="+KD[k]+" >= '"+d+"T00:00:00' AND "+KD[k]+" < '"+e+"T00:00:00'";
function susun(){const rg=rentang();$('url').innerHTML=rg?daftar().map(k=>'<div><b>'+NM[k]+':</b> <code>'+urlFor(k,rg).replace(/</g,'&lt;')+'</code></div>').join(''):'<i>Isi tanggal dari dan sampai.</i>'}
document.querySelectorAll('#dsp [data-ds]').forEach(b=>b.onclick=()=>{document.querySelectorAll('#dsp [data-ds]').forEach(x=>x.setAttribute('aria-pressed',x===b));ds=b.dataset.ds;susun()});
document.querySelectorAll('#mdp [data-m]').forEach(b=>b.onclick=()=>{document.querySelectorAll('#mdp [data-m]').forEach(x=>x.setAttribute('aria-pressed',x===b));mode=b.dataset.m;$('pb').hidden=mode!=='bulan';$('pk').hidden=mode!=='kustom';susun()});
$('bulan').onchange=susun;
$('dari').onchange=$('sampai').onchange=()=>{if($('dari').value&&$('sampai').value&&$('sampai').value<=$('dari').value){notif('Tanggal akhir harus setelah tanggal awal.','gagal');$('sampai').value=''}susun()};
susun();
const nilai=k=>({url:urlFor(k,rentang()),dari:'',sampai:''});
const URUT=['web','nifi','hdfs','prep','parquet','analisis','ml','export'];
const warnai=(n,jalan)=>document.querySelectorAll('#alur li').forEach(li=>{const i=URUT.indexOf(li.dataset.k);li.className=i<n?'ok':(i===n&&jalan?'jalan':'')});
const seen={},TXT={prep:'MapReduce prep (YARN) membersihkan data',parquet:'Spark menyimpan Parquet',mapreduce:'MapReduce crime_dhh',bi:'Analisis BI (Spark)',analisis:'Analisis lokasi dan jenis',ml:'Machine learning (MLlib)',export:'Ekspor hasil ke web',selesai:'Semua tahap selesai'};
const MAP={prep:3,parquet:4,mapreduce:5,bi:5,analisis:5,ml:6,export:7,selesai:8};
const LV='http://localhost:8010/api'; // Laravel lapisan job (ADR 0008)
async function poll(j){const r=await (await fetch(LV+'/jobs/'+j+'/log')).json();log.textContent=r.log||'(menunggu keluaran)';
  const st=r.steps.map(x=>x.split(':')[0]),last=st[st.length-1];if(last)warnai(MAP[last]??3,!r.done);
  st.forEach(x=>{if(!(x in seen)){seen[x]=1;notif((TXT[x]||'Tahap '+x)+(x==='selesai'?'':' berjalan...'))}});
  if(!r.done)tm=setTimeout(()=>poll(j),2500);else{notif(r.ok?'Job '+j+' selesai.':'Job '+j+' gagal, lihat log.',r.ok?'ok':'gagal');if(r.ok&&j==='pipeline'){warnai(8,false);setTimeout(()=>location.reload(),1500)}}}
const jalan=async(j,d)=>{clearTimeout(tm);for(const k in seen)delete seen[k];log.textContent='';notif('Memulai job '+j+'...');await fetch(LV+'/jobs/'+j+'?ds='+(d||'all'),{method:'POST'});poll(j)};
document.querySelectorAll('[data-job]').forEach(b=>b.onclick=()=>jalan(b.dataset.job,b.dataset.ds));
async function cek(k){const q=new URLSearchParams({a:'cek',...nilai(k)});return await (await fetch('jobs.php?'+q)).json()}
let dsPipe='crime';
$('kirim').onclick=async()=>{const rg=rentang(),list=daftar();
  if(!rg){notif('Isi tanggal dari dan sampai.','gagal');return}
  const hari=(new Date(rg[1])-new Date(rg[0]))/864e5,maks=list.length>1?92:366;
  if(mode==='kustom'&&hari>maks){notif('Rentang kustom maksimal '+maks+' hari. Persempit rentang atau pilih satu dataset.','gagal');return}
  $('kirim').disabled=true;$('proses').disabled=true;warnai(1,true);const ok=[];
  for(const k of list){const c=await cek(k);if(!c.ok){notif(NM[k]+': '+c.pesan,'gagal');continue}
    notif(NM[k]+': link valid ('+c.nama.slice(0,10)+'), mengirim ke NiFi...');
    const r=await (await fetch('jobs.php',{method:'POST',body:new URLSearchParams({a:'ingest',...nilai(k)})})).json();
    notif(NM[k]+': '+r.pesan,r.ok?'ok':'gagal');if(r.ok)ok.push(r)}
  if(!ok.length){warnai(0,false);$('kirim').disabled=false;return}
  notif('NiFi mengunduh '+ok.length+' dataset dari portal...');warnai(2,true);
  dsPipe=list.length>1?'all':list[0];const sisa=new Set(ok.map(r=>r.dataset));let n=0,sibuk=false;
  const t=setInterval(async()=>{if(sibuk)return;sibuk=true;
    for(const r of ok){if(!sisa.has(r.dataset))continue;const q=await (await fetch('jobs.php?a=hdfsfile&ds='+r.dataset+'&nama='+encodeURIComponent(r.nama))).json();
      if(q.ada){sisa.delete(r.dataset);notif(NM[r.dataset]+' masuk HDFS ('+q.mb+' MB).','ok');info.innerHTML+=`<p class="ins">/data/raw/${r.dataset}/${r.dataset}_${r.nama}.csv (${q.mb} MB)</p>`}}
    sibuk=false;
    if(!sisa.size){clearInterval(t);warnai(3,false);notif('Semua berkas masuk HDFS. Siap diproses.','ok');$('proses').disabled=false;$('kirim').disabled=false}
    else if(++n>100){clearInterval(t);notif('Belum muncul di HDFS: '+[...sisa].map(x=>NM[x]).join(', ')+'. Cek NiFi.','gagal');$('kirim').disabled=false}},3000)};
$('proses').onclick=()=>jalan('pipeline',dsPipe);
$('sync').onclick=async()=>{notif('Mengimpor ke MySQL...');const r=await (await fetch('jobs.php?a=sync')).json();notif('Impor selesai ('+r.hasil.length+' tabel).','ok');log.textContent+='\nSumber: '+r.sumber+'\n'+r.hasil.join('\n');setTimeout(()=>location.reload(),1200)};
</script>
<?php foot();
