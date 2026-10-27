<?php
// Pemicu job di WSL (HDFS/Spark/NiFi tinggal di WSL). Job jalan di latar, log ke RUN.
require __DIR__ . '/lib.php';
// Skrip dan log ke folder tanpa spasi atau '&' (cmd.exe memecah perintah pada '&').
const RUN = 'C:/Temp/bigdata-web'; // harus sama dengan jalur /mnt/c/Temp/bigdata-web di bawah
const REPO = '~/tugas-akhir-bigdata';
const WSLWEB = '//wsl.localhost/Ubuntu/home/lenovo/tugas-akhir-bigdata/web_export';
$JOBS = [
 'hdfs'       => ['Cek ukuran HDFS',        'hdfs dfs -du -s -h /data/raw/crime /data/raw/crashes /data/raw/311'],
 'prep'       => ['Preprocessing MapReduce', 'bash src/mr/run_prep.sh DS'],
 'parquet'    => ['TSV ke Parquet (Spark)', '.venv/bin/python -m src.load_parquet DS'],
 'pipeline'   => ['Pipeline lengkap',       'bash src/pipeline.sh DS'],
 'preproses'  => ['Preprocessing (MapReduce + Parquet)', 'bash src/mr/run_prep.sh DS && echo __STEP__parquet && .venv/bin/python -m src.load_parquet DS && echo __STEP__selesai'],
 'analitik'   => ['Analisis dan ML',         'echo __STEP__mapreduce && bash src/mr/run_mr.sh && echo __STEP__bi && .venv/bin/python -m src.bi && echo __STEP__analisis && .venv/bin/python -m src.analisis && echo __STEP__ml && .venv/bin/python -m src.ml && echo __STEP__export && .venv/bin/python -m src.export_web && echo __STEP__selesai'],
 'hdfsls'     => ['Isi HDFS raw',           'hdfs dfs -ls /data/raw/DS | tail -5; hdfs dfs -ls /data/raw/DS | wc -l'],
 'bi'         => ['Analisis BI PySpark',    '.venv/bin/python -m src.bi'],
 'mapreduce'  => ['MapReduce di YARN',      'bash src/mr/run_mr.sh'],
 'analisis'   => ['Analisis lokasi dan jenis', '.venv/bin/python -m src.analisis'],
 'ml'         => ['Machine learning MLlib', '.venv/bin/python -m src.ml'],
 'export'     => ['Ekspor ke web',          '.venv/bin/python -m src.export_web'],
];
$a = $_REQUEST['a'] ?? '';
$j = $_GET['job'] ?? '';
$ds = in_array($_GET['ds'] ?? 'all', ['crime', 'crashes', '311', 'all'], true) ? ($_GET['ds'] ?? 'all') : 'all';
const DATASET = ['ijzp-q8t2' => 'crime', '85ca-t3if' => 'crashes', 'v6vf-nfxy' => '311'];

/** Validasi + normalisasi link API Socrata. Hanya host portal Chicago dan 3 resource; kembalikan [dataset, url] atau pesan galat (string). */
function normalisasi(string $in, string $dari = '', string $sampai = '') {
    $u = parse_url(trim($in));
    if (!$u || ($u['scheme'] ?? '') !== 'https' || strtolower($u['host'] ?? '') !== 'data.cityofchicago.org' || isset($u['user']) || isset($u['port'])) return 'Hanya link https://data.cityofchicago.org yang diterima.';
    if (!preg_match('#^/(?:resource|api/views)/([a-z0-9]{4}-[a-z0-9]{4})(?:\.(?:csv|json)|/rows\.csv)$#', $u['path'] ?? '', $m) || !isset(DATASET[$m[1]]))
        return 'Resource tidak dikenal. Boleh: ijzp-q8t2 (kejahatan), 85ca-t3if (kecelakaan), v6vf-nfxy (311).';
    $ds = DATASET[$m[1]]; parse_str($u['query'] ?? '', $q);
    $kol = ['crime' => 'date', 'crashes' => 'crash_date', '311' => 'created_date'][$ds];
    $where = trim($q['$where'] ?? '');
    if ($where === '' && $dari !== '' && $sampai !== '') {
        if (!preg_match('/^\d{4}-\d{2}-\d{2}$/', $dari . '') || !preg_match('/^\d{4}-\d{2}-\d{2}$/', $sampai)) return 'Tanggal harus berformat YYYY-MM-DD.';
        $where = "$kol >= '{$dari}T00:00:00' AND $kol < '{$sampai}T00:00:00'";
    }
    if ($where === '') return 'Link belum punya filter $where. Isi rentang tanggal supaya unduhan tidak sebesar seluruh dataset.';
    if (preg_match('/[|\r\n]/', $where)) return 'Filter $where memuat karakter tidak valid.';
    $nama = preg_match("/(\d{4}-\d{2}-\d{2})/", $where, $t) ? $t[1] : date('Ymd');
    $nama .= '_w' . substr(md5($where), 0, 6);
    $url = 'https://data.cityofchicago.org/resource/' . $m[1] . '.csv?%24where=' . rawurlencode($where) . '&%24limit=' . (int)($q['$limit'] ?? 2000000);
    return [$ds, $nama, $url, $where];
}
if ($a === 'cek') { $r = normalisasi($_GET['url'] ?? '', $_GET['dari'] ?? '', $_GET['sampai'] ?? ''); json_out(is_string($r) ? ['ok' => false, 'pesan' => $r] : ['ok' => true, 'dataset' => $r[0], 'nama' => $r[1], 'url' => $r[2], 'where' => $r[3]]); }
if ($a === 'ingest' && $_SERVER['REQUEST_METHOD'] === 'POST') {
    $r = normalisasi($_POST['url'] ?? '', $_POST['dari'] ?? '', $_POST['sampai'] ?? '');
    if (is_string($r)) json_out(['ok' => false, 'pesan' => $r]);
    $baris = "$r[0]|$r[1]|$r[2]";
    $c = curl_init('http://localhost:8081/ingest');
    curl_setopt_array($c, [CURLOPT_POST => true, CURLOPT_POSTFIELDS => $baris, CURLOPT_HTTPHEADER => ['Content-Type: text/plain'], CURLOPT_RETURNTRANSFER => true, CURLOPT_TIMEOUT => 10, CURLOPT_CONNECTTIMEOUT => 4]);
    curl_exec($c); $kode = curl_getinfo($c, CURLINFO_HTTP_CODE); $err = curl_error($c);
    json_out(['ok' => $kode >= 200 && $kode < 300, 'dataset' => $r[0], 'nama' => $r[1], 'baris' => $baris, 'http' => $kode, 'pesan' => $kode ? "NiFi membalas HTTP $kode" : "NiFi tidak terjangkau: $err"]);
}
if ($a === 'run' && isset($JOBS[$j])) {
    @mkdir(__DIR__ . '/logs');
    $log = RUN . "/$j.log";
    file_put_contents($log, '');
    db()->prepare('INSERT INTO job_runs(job,status,started,log_file) VALUES(?,?,NOW(),?)')->execute([$j, 'running', RUN . "/$j.log"]);
    // Perintah ditulis ke skrip .sh (menghindari masalah kutip cmd). .bashrc tidak dimuat shell non-interaktif, jadi PATH diset eksplisit.
    $sh = RUN . "/$j.sh";
    file_put_contents($sh, implode("\n", [
        '#!/bin/bash',
        'export JAVA_HOME=$(dirname $(dirname $(readlink -f $(which javac))))',
        'export HADOOP_HOME=/usr/local/hadoop SPARK_HOME=/usr/local/spark',
        'export PATH=$PATH:$HADOOP_HOME/bin:$HADOOP_HOME/sbin:$SPARK_HOME/bin',
        'cd ' . REPO,
        str_replace('DS', $ds, $JOBS[$j][1]),
        'echo __EXIT__$?', '']));
    // Jalur RUN tanpa spasi dan '&', jadi aman untuk cmd.exe. Latar via start /B; log ditulis ke file.
    pclose(popen('start /B cmd /c wsl -d Ubuntu -e bash /mnt/c/Temp/bigdata-web/' . $j . '.sh > ' . $log . ' 2>&1', 'r'));
    json_out(['job' => $j, 'started' => true]);
}
if ($a === 'hdfsfile') {
    $n = preg_replace('/[^A-Za-z0-9_.-]/', '', $_GET['nama'] ?? '');
    $o = $n !== '' && $ds !== 'all' ? (string)shell_exec('wsl -d Ubuntu -e bash -c "/usr/local/hadoop/bin/hdfs dfs -du /data/raw/' . $ds . '/' . $ds . '_' . $n . '.csv 2>/dev/null"') : '';
    $ada = preg_match('/^(\d+)\s/', trim($o), $m) === 1;
    json_out(['ada' => $ada, 'mb' => $ada ? round((int)$m[1] / 1e6, 1) : 0]);
}
if ($a === 'log' && isset($JOBS[$j])) {
    $f = RUN . "/$j.log";
    $all = is_file($f) ? file($f) : [];
    $t = implode('', array_slice($all, -25));
    $steps = []; foreach ($all as $l) if (preg_match('/^__STEP__(\S+)/', $l, $m)) $steps[] = $m[1];
    json_out(['log' => $t, 'done' => str_contains($t, '__EXIT__'), 'ok' => str_contains($t, '__EXIT__0'), 'steps' => $steps]);
}
if ($a === 'sync') {
    $src = is_dir(WSLWEB) ? WSLWEB : __DIR__ . '/data';
    json_out(['sumber' => $src, 'hasil' => import_all($src)]);
}
json_out(['jobs' => array_map(fn($x) => $x[0], $JOBS)]);
