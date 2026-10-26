<?php require __DIR__ . '/layout.php'; head('Kode', 'kode.php'); ?>
<h1>Kode analisis</h1>
<p>Semua skrip PySpark dan MapReduce, lokasinya di repo WSL <code>~/tugas-akhir-bigdata</code>, dan penjelasan sintaksnya. Sumber: Laravel <code>/api/kode</code>.</p>
<div id="daftar">Memuat...</div>
<script>
const e=s=>s.replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
fetch('http://localhost:8010/api/kode').then(r=>r.json()).then(d=>{
  document.getElementById('daftar').innerHTML=d.map(f=>`<details class="panel"><summary><code>${e(f.path)}</code></summary>
  <pre style="white-space:pre-wrap;overflow:auto">${e(f.penjelasan||'(tanpa penjelasan)')}</pre>
  <pre style="overflow:auto;max-height:480px">${e(f.isi)}</pre></details>`).join('');
}).catch(()=>document.getElementById('daftar').textContent='Laravel (port 8010) belum jalan: php artisan serve --port=8010');
</script>
<?php foot();
