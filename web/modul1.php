<?php require __DIR__ . '/layout.php'; head('Modul 1', 'modul1.php');
$pre = ready() ? q('SELECT * FROM preprocess ORDER BY rows_in DESC') : [];
$nama = ['crime' => 'Kejahatan', 'crashes' => 'Kecelakaan', '311' => 'Layanan 311'];
$tot_in = array_sum(array_column($pre, 'rows_in')); $tot_out = array_sum(array_column($pre, 'rows_final')); ?>
<h1>Modul 1: Import data dan preprocessing</h1>
<p class="muted" style="max-width:70ch">Tempel link API Chicago Data Portal. NiFi mengunduhnya ke HDFS, MapReduce di YARN membersihkannya, lalu Spark menyiapkan Parquet untuk analisis.</p>

<ol class="alur" id="alur" aria-label="Tahap pipeline">
<?php foreach (['web' => 'Link dari web', 'nifi' => 'NiFi unduh', 'hdfs' => 'HDFS raw', 'prep' => 'MapReduce prep', 'parquet' => 'Parquet', 'analisis' => 'Analisis', 'ml' => 'ML', 'export' => 'MySQL'] as $k => $t): ?><li data-k="<?= $k ?>"><?= $t ?></li><?php endforeach ?></ol>

<section class="panel" style="margin-top:16px"><h3>1. Ambil data dari API (NiFi)</h3>
<p class="small muted">Boleh: kejahatan <code>ijzp-q8t2</code>, kecelakaan <code>85ca-t3if</code>, 311 <code>v6vf-nfxy</code> di <code>data.cityofchicago.org</code>. Link <code>/resource/&lt;id&gt;.csv</code> dan link unduh <code>/api/views/&lt;id&gt;/rows.csv</code> sama-sama diterima. Memasukkan bulan yang sudah ada berarti baris dobel, dan MapReduce membuangnya.</p>
<label class="f" style="margin-top:8px">Link API<input id="url" type="url" placeholder="https://data.cityofchicago.org/resource/ijzp-q8t2.csv?$where=date >= '2026-09-01T00:00:00' AND date < '2026-10-01T00:00:00'" style="min-height:40px;border:1px solid var(--aspal);padding:6px 10px;font:inherit;width:100%"></label>
<div class="ctl"><label class="f">Dari (bila link tanpa $where)<input id="dari" type="date" style="min-height:40px;border:1px solid var(--aspal);padding:6px 10px;font:inherit"></label>
<label class="f">Sampai (tidak termasuk)<input id="sampai" type="date" style="min-height:40px;border:1px solid var(--aspal);padding:6px 10px;font:inherit"></label>
<button class="btn pri" id="kirim">Kirim ke NiFi</button><button class="btn" id="contoh">Isi contoh (crime Sep 2026)</button><button class="btn pri" id="proses" disabled>Proses (pipeline)</button></div>
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

<section style="margin-top:16px"><h3>Log job</h3><pre id="log" class="log" aria-live="polite">Belum ada job dijalankan.</pre>
<p class="small muted">Job butuh WSL dengan HDFS (dan YARN untuk MapReduce) hidup. Bila mati, web tetap menampilkan hasil tersimpan.</p></section>
<script>
const log=document.getElementById('log'),info=document.getElementById('info'),$=id=>document.getElementById(id);let tm,ds='all';
const nilai=()=>({url:$('url').value,dari:$('dari').value,sampai:$('sampai').value});
const URUT=['web','nifi','hdfs','prep','parquet','analisis','ml','export'];
const warnai=(n,jalan)=>document.querySelectorAll('#alur li').forEach(li=>{const i=URUT.indexOf(li.dataset.k);li.className=i<n?'ok':(i===n&&jalan?'jalan':'')});
const MAP={prep:3,parquet:4,mapreduce:5,bi:5,analisis:5,ml:6,export:7,selesai:8};
const LV='http://localhost:8010/api'; // Laravel lapisan job (ADR 0008)
async function poll(j){const r=await (await fetch(LV+'/jobs/'+j+'/log')).json();log.textContent=r.log||'(menunggu keluaran)';
  const st=r.steps.map(x=>x.split(':')[0]),last=st[st.length-1];if(last)warnai(MAP[last]??3,!r.done);
  if(!r.done)tm=setTimeout(()=>poll(j),2500);else{log.textContent+='\n'+(r.ok?'Selesai.':'Gagal, lihat log.');if(r.ok&&j==='pipeline'){warnai(8,false);setTimeout(()=>location.reload(),1500)}}}
const jalan=async(j,d)=>{clearTimeout(tm);log.textContent='Memulai '+j+'...';await fetch(LV+'/jobs/'+j+'?ds='+(d||'all'),{method:'POST'});poll(j)};
document.querySelectorAll('[data-job]').forEach(b=>b.onclick=()=>jalan(b.dataset.job,b.dataset.ds));
async function cek(){const q=new URLSearchParams({a:'cek',...nilai()});const r=await (await fetch('jobs.php?'+q)).json();
  info.innerHTML=r.ok?`<p class="ins">Dataset <b>${r.dataset}</b>, berkas <code>${r.nama}.csv</code>, filter <code>${r.where.replace(/</g,'&lt;')}</code></p>`:`<p class="ins" style="border-color:var(--bendera)">${r.pesan}</p>`;return r}
$('contoh').onclick=()=>{$('url').value="https://data.cityofchicago.org/resource/ijzp-q8t2.csv?$where=date >= '2026-09-01T00:00:00' AND date < '2026-10-01T00:00:00'";cek()};
$('url').onchange=cek;$('dari').onchange=$('sampai').onchange=()=>$('url').value&&cek();
$('kirim').onclick=async()=>{const c=await cek();if(!c.ok)return;warnai(1,true);
  const r=await (await fetch('jobs.php',{method:'POST',body:new URLSearchParams({a:'ingest',...nilai()})})).json();
  info.innerHTML+=`<p class="ins" style="border-color:${r.ok?'#2e7d46':'var(--bendera)'}">${r.pesan}</p>`;if(!r.ok){warnai(0,false);return}
  ds=r.dataset;warnai(2,true);let n=0;const t=setInterval(async()=>{const q=await (await fetch('jobs.php?a=hdfsfile&ds='+ds+'&nama='+encodeURIComponent(r.nama))).json();
    if(q.ada){clearInterval(t);warnai(3,false);info.innerHTML+=`<p class="ins">Berkas muncul di HDFS: /data/raw/${ds}/${ds}_${r.nama}.csv (${q.mb} MB)</p>`;$('proses').disabled=false}
    else if(++n>60){clearInterval(t);info.innerHTML+='<p class="ins" style="border-color:var(--bendera)">Belum muncul di HDFS. Cek NiFi.</p>'}},3000)};
$('proses').onclick=()=>jalan('pipeline',ds);
$('sync').onclick=async()=>{log.textContent='Mengimpor...';const r=await (await fetch('jobs.php?a=sync')).json();log.textContent='Sumber: '+r.sumber+'\n'+r.hasil.join('\n');setTimeout(()=>location.reload(),1200)};
</script>
<?php foot();
