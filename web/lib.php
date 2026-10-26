<?php
// Koneksi + helper. MySQL Laragon, tanpa login.
function db(): PDO {
    static $p;
    if (!$p) {
        $p = new PDO('mysql:host=127.0.0.1;port=3306;charset=utf8mb4', 'root', '', [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION, PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC]);
        $p->exec('CREATE DATABASE IF NOT EXISTS chicago_bigdata CHARACTER SET utf8mb4');
        $p->exec('USE chicago_bigdata');
    }
    return $p;
}
function q(string $sql, array $a = []): array { $s = db()->prepare($sql); $s->execute($a); return $s->fetchAll(); }
function one(string $sql, array $a = []) { return q($sql, $a)[0] ?? null; }
function json_out($d) { header('Content-Type: application/json'); echo json_encode($d, JSON_NUMERIC_CHECK); exit; }
function h($s) { return htmlspecialchars((string)$s, ENT_QUOTES); }
function nf($n, $d = 0) { return number_format((float)$n, $d, ',', '.'); }
function ready(): bool { try { return (bool)one("SELECT 1 x FROM information_schema.tables WHERE table_schema='chicago_bigdata' AND table_name='kpi'"); } catch (Throwable $e) { return false; } }

// Impor hasil analisis (data/*.csv|json|tsv) ke MySQL. Hasil dibuat PySpark/MapReduce di WSL.
function import_all(string $dir): array {
    $db = db(); $log = [];
    $csv = fn($f) => array_map('str_getcsv', file("$dir/$f", FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES));
    $load = function (string $t, string $ddl, array $cols, array $rows) use ($db, &$log) {
        $db->exec("DROP TABLE IF EXISTS $t"); $db->exec("CREATE TABLE $t ($ddl) ENGINE=InnoDB");
        $st = $db->prepare("INSERT INTO $t (" . implode(',', $cols) . ') VALUES (' . implode(',', array_fill(0, count($cols), '?')) . ')');
        $db->beginTransaction(); foreach ($rows as $r) $st->execute($r); $db->commit();
        $log[] = "$t: " . count($rows) . ' baris';
    };
    $tbl = function (string $f) use ($csv) { $r = $csv($f); array_shift($r); return $r; };
    $load('daily', 'day DATE PRIMARY KEY, n INT', ['day', 'n'], $tbl('daily.csv'));
    $load('weekly', 'minggu DATE PRIMARY KEY, n INT', ['minggu', 'n'], $tbl('weekly.csv'));
    $load('heatmap', 'dow TINYINT, hr TINYINT, n INT, PRIMARY KEY(dow,hr)', ['dow', 'hr', 'n'], $tbl('heatmap.csv'));
    $load('top_types', 'tipe VARCHAR(60) PRIMARY KEY, n INT', ['tipe', 'n'], $tbl('top_types.csv'));
    $load('district', 'district INT PRIMARY KEY, n INT, arrest_rate DOUBLE', ['district', 'n', 'arrest_rate'], $tbl('district.csv'));
    $load('next_day', 'district INT PRIMARY KEY, day DATE, pred DOUBLE, p33 DOUBLE, p66 DOUBLE, risk VARCHAR(10)', ['district', 'day', 'pred', 'p33', 'p66', 'risk'], $tbl('next_day.csv'));
    $load('test_pred', 'district INT, day DATE, n INT, prediction DOUBLE, KEY(day)', ['district', 'day', 'n', 'prediction'], $tbl('test_pred.csv'));
    $j = fn($f) => json_decode(file_get_contents("$dir/$f"), true);
    $load('lag_corr', 'lg INT PRIMARY KEY, corr DOUBLE', ['lg', 'corr'], array_map(fn($r) => [$r['lag'], $r['corr']], $j('lag_corr.json')));
    $load('ext_corr', 'factor VARCHAR(30), lg INT, corr DOUBLE, PRIMARY KEY(factor,lg)', ['factor', 'lg', 'corr'], array_map(fn($r) => [$r['factor'], $r['lag'], $r['corr']], $j('ext_corr.json')));
    $m = $j('metrics.json'); $rows = [];
    foreach ($m as $k => $v) if (is_array($v) && isset($v['rmse'])) $rows[] = [$k, $v['mae'], $v['rmse'], $v['r2']];
    $load('model_metrics', 'model VARCHAR(30) PRIMARY KEY, mae DOUBLE, rmse DOUBLE, r2 DOUBLE', ['model', 'mae', 'rmse', 'r2'], $rows);
    $load('importance', 'fitur VARCHAR(40) PRIMARY KEY, nilai DOUBLE', ['fitur', 'nilai'], array_map(null, array_keys($m['importance_gbt_full']), array_values($m['importance_gbt_full'])));
    $rows = []; foreach (file("$dir/crime_dhh.tsv", FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES) as $l) { [$k, $n] = explode("\t", $l); [$d, $dy, $hr] = explode('|', $k); $rows[] = [(int)$d, (int)$dy, (int)$hr, (int)$n]; }
    $load('mr_dhh', 'district INT, dow INT, hr INT, n INT, KEY(district)', ['district', 'dow', 'hr', 'n'], $rows);
    $m1 = $j('m1_summary.json'); $hd = $j('hdfs_size.json'); $rows = [];
    foreach ($m1 as $k => $v) $rows[] = [$k, $v['rows_in'], $v['dup_identical'], $v['dup_key'], $v['rows_final'], $v['dropped_partial_day'], $hd[($k) . '_raw_mb']];
    $load('preprocess', 'dataset VARCHAR(20) PRIMARY KEY, rows_in INT, dup_identical INT, dup_key INT, rows_final INT, dropped_day DATE, hdfs_mb DOUBLE', ['dataset', 'rows_in', 'dup_identical', 'dup_key', 'rows_final', 'dropped_day', 'hdfs_mb'], $rows);
    $k = $j('kpi.json');
    $load('kpi', 'k VARCHAR(30) PRIMARY KEY, v VARCHAR(40)', ['k', 'v'], [['total', $k['total']], ['arrest_rate', $k['arrest_rate']], ['domestic_pct', $k['domestic_pct']], ['first_day', $m['first_day']], ['last_day', $m['last_day']], ['train_rows', $m['train_rows']], ['test_rows', $m['test_rows']], ['best_model', $m['best_model']], ['total_raw_gb', $hd['total_raw_gb']]]);
    if (is_file("$dir/analisis/grid.csv")) {   // analisis interaktif (src/analisis.py)
        $a = fn($f) => $tbl("analisis/$f");
        $load('a_grid', 'jenis VARCHAR(40), la DOUBLE, lo DOUBLE, n INT, KEY(jenis)', ['jenis', 'la', 'lo', 'n'], $a('grid.csv'));
        $load('a_type_month', 'jenis VARCHAR(40), bulan CHAR(7), n INT, KEY(jenis)', ['jenis', 'bulan', 'n'], $a('type_month.csv'));
        $load('a_type_hour', 'jenis VARCHAR(40), dow TINYINT, hr TINYINT, n INT, KEY(jenis)', ['jenis', 'dow', 'hr', 'n'], $a('type_hour.csv'));
        $load('a_type_district', 'jenis VARCHAR(40), district INT, n INT, KEY(jenis)', ['jenis', 'district', 'n'], $a('type_district.csv'));
        $load('a_type_profile', 'jenis VARCHAR(40) PRIMARY KEY, n INT, arrest_rate DOUBLE, domestic_pct DOUBLE, top_district INT, top_share DOUBLE', ['jenis', 'n', 'arrest_rate', 'domestic_pct', 'top_district', 'top_share'], $a('type_profile.csv'));
        $load('a_type_corr', 'a VARCHAR(40), b VARCHAR(40), corr DOUBLE, PRIMARY KEY(a,b)', ['a', 'b', 'corr'], $a('type_corr.csv'));
        $load('a_meta', 'k VARCHAR(30) PRIMARY KEY, v TEXT', ['k', 'v'], array_map(fn($k, $v) => [$k, is_array($v) ? implode(',', $v) : $v], array_keys($mm = $j('analisis/meta.json')), array_values($mm)));
    }
    $db->exec('CREATE TABLE IF NOT EXISTS job_runs (id INT AUTO_INCREMENT PRIMARY KEY, job VARCHAR(30), status VARCHAR(12), started DATETIME, finished DATETIME NULL, log_file VARCHAR(80))');
    return $log;
}
