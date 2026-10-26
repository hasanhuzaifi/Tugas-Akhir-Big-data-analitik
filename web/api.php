<?php
// JSON untuk halaman interaktif. Semua dari tabel a_* di MySQL.
require __DIR__ . '/lib.php';
$a = $_GET['a'] ?? '';
$ok = array_column(q('SELECT jenis FROM a_type_profile'), 'jenis');
$js = array_values(array_intersect(array_filter(explode(',', $_GET['j'] ?? '')), $ok));
if ($a === 'grid') {   // [{la,lo,n}] untuk satu jenis atau SEMUA
    $j = $_GET['j'] ?? '';
    json_out($j === 'SEMUA' ? q('SELECT la,lo,SUM(n) n FROM a_grid GROUP BY la,lo') : (in_array($j, $ok, true) ? q('SELECT la,lo,n FROM a_grid WHERE jenis=?', [$j]) : []));
}
if ($a === 'cmp' && $js) {
    $in = implode(',', array_fill(0, count($js), '?'));
    json_out([
        'bulan'    => q("SELECT jenis,bulan,n FROM a_type_month WHERE jenis IN ($in) ORDER BY bulan", $js),
        'jam'      => q("SELECT jenis,dow,hr,n FROM a_type_hour WHERE jenis IN ($in)", $js),
        'profil'   => q("SELECT * FROM a_type_profile WHERE jenis IN ($in)", $js),
        'district' => q("SELECT jenis,district,n FROM a_type_district WHERE jenis IN ($in) ORDER BY n DESC", $js),
        'korelasi' => q("SELECT a,b,corr FROM a_type_corr WHERE a IN ($in) AND b IN ($in)", array_merge($js, $js)),
    ]);
}
if ($a === 'district') {   // detail satu district untuk penjelajah ML
    $d = (int)($_GET['d'] ?? 0);
    json_out([
        'next'  => one('SELECT * FROM next_day WHERE district=?', [$d]),
        'seri'  => q('SELECT day,n,prediction p FROM test_pred WHERE district=? ORDER BY day', [$d]),
        'jam'   => q('SELECT dow,hr,n FROM mr_dhh WHERE district=?', [$d]),
        'total' => one('SELECT n,arrest_rate FROM district WHERE district=?', [$d]),
    ]);
}
json_out(['error' => 'a=grid|cmp']);
