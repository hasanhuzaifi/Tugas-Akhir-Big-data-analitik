#!/bin/bash
# Cek data di HDFS setelah ingest. Pakai: cek_hdfs.sh [crime|crashes|311|all]
cd "$(dirname "$0")/../.."
H=/usr/local/hadoop/bin/hdfs
DS="${1:-all}"; [ "$DS" = all ] && DS="crime crashes 311"
echo "== Layanan =="; jps | grep -E "NameNode|DataNode|ResourceManager|NodeManager" || echo "HDFS/YARN MATI"
for d in $DS; do
  echo; echo "== $d =="
  n=$($H dfs -ls /data/raw/$d 2>/dev/null | grep -c '\.csv$')
  if [ "$n" -gt 0 ]; then
    echo "raw     : OK ($n berkas CSV)"; $H dfs -ls -h /data/raw/$d | tail -n 5
    echo "ukuran HDFS : $($H dfs -du -s -h /data/raw/$d | cut -d' ' -f1-2)"
    echo "ukuran landing : $(du -sh data/landing/$d 2>/dev/null | cut -f1)  (harus sama)"
    echo "baris (CSV terakhir) : $($H dfs -cat $($H dfs -ls /data/raw/$d | grep '\.csv$' | tail -1 | awk '{print $NF}') | wc -l)"
  else echo "raw     : KOSONG"; fi
  for t in clean processed; do
    if $H dfs -test -e /data/$t/$d/_SUCCESS 2>/dev/null; then echo "$t : OK ($($H dfs -du -s -h /data/$t/$d | cut -d' ' -f1-2))"; else echo "$t : belum ada"; fi
  done
done
echo; echo "== Kapasitas =="; $H dfsadmin -report 2>/dev/null | grep -E "Configured Capacity|DFS Used:|DFS Remaining|Live datanodes" | head -4
echo "== Kesehatan =="; $H fsck /data/raw 2>/dev/null | grep -E "Status|Total size|Total files|Corrupt" 
