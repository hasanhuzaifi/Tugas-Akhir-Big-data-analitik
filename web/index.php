<?php require __DIR__ . '/layout.php'; head('Beranda', 'index.php');
$k = ready() ? array_column(q('SELECT k,v FROM kpi'), 'v', 'k') : [];
$steps = [
 ['Akuisisi', 'NiFi + PutHDFS', 'API Socrata ditarik per bulan oleh NiFi lalu ditulis ke HDFS.'],
 ['Penyimpanan', 'HDFS', 'Tiga dataset mentah di /data/raw, hasil bersih Parquet di /data/processed.'],
 ['Preprocessing', 'PySpark', 'Dedup, buang hari parsial, standardisasi kolom.'],
 ['Pemrosesan', 'MapReduce di YARN', 'Hadoop Streaming menghitung kejadian per district, hari, jam.'],
 ['Analisis BI', 'PySpark SQL', 'Sebaran lokasi, perbandingan jenis, korelasi, tren.'],
 ['Machine learning', 'Spark MLlib', 'RandomForest dan GBT memprediksi kejadian per district per hari.'],
 ['Tampilan', 'MySQL Laragon + web', 'Hasil disimpan ke MySQL; web membaca database.']]; ?>
<section class="hero">
 <div>
  <h1>Di mana kejahatan di Chicago biasanya terjadi?</h1>
  <p class="muted" style="max-width:52ch;margin:16px 0">Pilih jenis kejahatan, lihat sebarannya di peta, bandingkan dengan jenis lain, lalu lihat prakiraan hari berikutnya. Data <?= $k ? nf($k['total']) : '' ?> laporan, 25 Okt 2023 sampai 15 Okt 2026.</p>
  <div style="display:flex;gap:8px;flex-wrap:wrap"><a class="btn pri" href="modul2.php?s=1">Buka peta panas</a><a class="btn" href="modul2.php?s=2">Bandingkan jenis</a><a class="btn" href="modul1.php">Lihat proses data</a></div>
 </div>
 <div id="mini" role="img" aria-label="Peta panas semua kejahatan"></div>
</section>
<?php if ($k): ?><section class="grid g3" style="margin-top:0">
<?php foreach ([[nf($k['total']), 'laporan kejahatan bersih'], [nf($k['total_raw_gb'], 2) . ' GB', 'data mentah di HDFS (3 dataset)'], [nf($k['arrest_rate'] * 100, 1) . '%', 'berujung penangkapan']] as [$a, $b]): ?>
<div class="panel"><div class="big"><?= $a ?></div><div class="small muted"><?= $b ?></div></div><?php endforeach ?></section><?php endif ?>
<h2 style="margin-top:40px">Alur big data</h2>
<ol style="list-style:none;padding:0;margin:8px 0 0"><?php foreach ($steps as $i => [$n, $t, $d]): ?>
<li class="step"><b class="n"><?= $i + 1 ?></b><div><b><?= $n ?></b> <span class="muted">(<?= $t ?>)</span><div class="small muted"><?= $d ?></div></div></li><?php endforeach ?></ol>
<p class="small muted">Langkah 1 sampai 3 adalah Modul 1 (import dan preprocessing); langkah 4 sampai 7 adalah Modul 2 (analisis BI dan ML).</p>
<script>
(async()=>{const m=Peta.buat('mini');m.dragging.disable();m.scrollWheelZoom.disable();
const a=await (await fetch('api.php?a=grid&j=SEMUA')).json(),v=a.map(c=>c.n).sort((x,y)=>x-y),p=v[Math.floor(v.length*.98)]||1;
Peta.gambar(m,a,c=>Peta.panas(Math.sqrt(c.n/p)),null)})();
</script>
<?php foot();
