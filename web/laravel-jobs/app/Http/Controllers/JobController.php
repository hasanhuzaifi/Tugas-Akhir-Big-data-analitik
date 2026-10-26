<?php
namespace App\Http\Controllers;

use Illuminate\Http\Request;

class JobController extends Controller
{
    private function cmd(string $job): string
    {
        $j = config('jobs.jobs');
        abort_unless(isset($j[$job]), 404, 'job tidak dikenal'); // trust boundary: hanya whitelist
        return $j[$job];
    }

    public function run(Request $r, string $job)
    {
        $cmd = $this->cmd($job);
        $ds = $r->query('ds', 'all');
        abort_unless(in_array($ds, ['crime', 'crashes', '311', 'all'], true), 422, 'ds tidak valid');
        $dir = config('jobs.run_dir');
        @mkdir($dir, 0777, true);
        file_put_contents("$dir/$job.log", '');
        file_put_contents("$dir/$job.sh", implode("\n", [
            '#!/bin/bash',
            'export JAVA_HOME=$(dirname $(dirname $(readlink -f $(which javac))))',
            'export HADOOP_HOME=/usr/local/hadoop SPARK_HOME=/usr/local/spark',
            'export PATH=$PATH:$HADOOP_HOME/bin:$HADOOP_HOME/sbin:$SPARK_HOME/bin',
            'cd ' . config('jobs.repo'),
            str_replace('DS', $ds, $cmd),
            'echo __EXIT__$?', '']));
        pclose(popen("start /B cmd /c wsl -d Ubuntu -e bash /mnt/c/Temp/bigdata-web/$job.sh > $dir/$job.log 2>&1", 'r'));
        return ['job' => $job, 'started' => true];
    }

    public function log(string $job)
    {
        $this->cmd($job);
        $f = config('jobs.run_dir') . "/$job.log";
        $all = is_file($f) ? file($f) : [];
        $t = implode('', array_slice($all, -25));
        $steps = [];
        foreach ($all as $l) if (preg_match('/^__STEP__(\S+)/', $l, $m)) $steps[] = $m[1];
        return ['log' => $t, 'done' => str_contains($t, '__EXIT__'), 'ok' => str_contains($t, '__EXIT__0'), 'steps' => $steps];
    }

    /** Daftar semua kode analisis + isinya (lokasi relatif repo WSL). */
    public function kode()
    {
        $b = config('jobs.repo_unc');
        $out = [];
        $doc = is_file(config('jobs.vault_doc')) ? file_get_contents(config('jobs.vault_doc')) : '';
        $sec = [];  // penjelasan sintaks: bagian "### `path`" di catatan vault
        foreach (preg_split('/^### /m', $doc) as $blok)
            if (preg_match('/^([^\n]*`[^\n]*)\n(.*)$/s', $blok, $m) && preg_match_all('/`([^`]+)`/', $m[1], $ks))
                foreach ($ks[1] as $k) $sec[$k] = trim($m[2]);
        foreach (array_merge(glob("$b/src/*.py"), glob("$b/src/*.sh"), glob("$b/src/mr/*.{py,sh}", GLOB_BRACE)) as $p) {
            $rel = substr($p, strlen($b) + 1);
            $out[] = ['path' => $rel, 'isi' => file_get_contents($p), 'penjelasan' => $sec[$rel] ?? $sec[basename($p)] ?? ''];
        }
        return $out;
    }
}
