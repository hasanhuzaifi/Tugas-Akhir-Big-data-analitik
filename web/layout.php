<?php
require_once __DIR__ . '/lib.php';
// Warna jalur L menurut urutan 12 jenis teratas (a_meta.top). Jenis ke-9 dan seterusnya abu.
const WARNA = ['#C60C30', '#00A1DE', '#62361B', '#009B3A', '#F9461C', '#522398', '#E27EA6', '#C9A400', '#00796B', '#1A3A8F', '#7C8B00', '#B0007A'];
function jenis_list(): array {
    static $l; if ($l === null) { try { $r = one("SELECT v FROM a_meta WHERE k='top'"); $l = $r ? explode(',', $r['v']) : []; } catch (Throwable $e) { $l = []; } }
    return $l;
}
function warna(string $j): string { $i = array_search($j, jenis_list(), true); return $i !== false && $i < 12 ? WARNA[$i] : '#7A8794'; }
function nama(string $j): string { return ucfirst(strtolower($j)); }
function head(string $title, string $active) { ?>
<!doctype html><html lang="id"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title><?= h($title) ?> | Peta Kejahatan Chicago</title>
<link rel="stylesheet" href="assets/leaflet.css"><link rel="stylesheet" href="assets/app.css">
<script src="assets/chart.js"></script><script src="assets/leaflet.js"></script><script src="assets/peta.js"></script></head><body>
<header class="bar"><div class="wrap"><a href="index.php" class="logo">PETA KEJAHATAN CHICAGO</a>
<nav aria-label="Utama"><?php foreach (['index.php' => 'Beranda', 'modul1.php' => 'Modul 1: Import', 'modul2.php' => 'Modul 2: Analisis', 'kode.php' => 'Kode'] as $u => $t): ?>
<a href="<?= $u ?>" <?= $active === $u ? 'aria-current="page"' : '' ?>><?= $t ?></a><?php endforeach ?></nav></div></header>
<main class="wrap">
<?php if (!ready()): ?><p class="panel" style="margin-top:16px">Database belum terisi. Buka <a href="jobs.php?a=sync">jobs.php?a=sync</a>.</p><?php endif;
}
function foot() { echo '</main><footer><div class="wrap">Data: Chicago Data Portal (Socrata), 25 Okt 2023 sampai 15 Okt 2026. Diproses dengan NiFi, HDFS, PySpark, MapReduce. Angka agregat dari laporan polisi, bukan kepastian kejadian.</div></footer></body></html>'; }
