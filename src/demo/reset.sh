#!/bin/bash
# Reset data demo (awal dan akhir demo). Pakai: reset.sh hdfs | semua
#   hdfs  : kosongkan /data/raw, /data/clean, /data/processed, /data/mr di HDFS + data/mr/*.tsv
#   semua : hdfs + data/landing/* (salinan NiFi) + web_export/* (tampilan kosong sampai analisis jalan lagi)
# Tidak pernah memformat NameNode. Hanya menyentuh jalur proyek.
cd "$(dirname "$0")/../.."
H=/usr/local/hadoop/bin/hdfs
MODE="${1:-hdfs}"
case "$MODE" in hdfs|semua) ;; *) echo "Pakai: reset.sh hdfs|semua"; exit 2;; esac
$H dfsadmin -safemode wait >/dev/null 2>&1
echo "== Sebelum =="; $H dfs -du -s -h /data/raw /data/clean /data/processed /data/mr 2>/dev/null || echo "(HDFS kosong)"
$H dfs -rm -r -f -skipTrash /data/raw /data/clean /data/processed /data/mr >/dev/null 2>&1
for ds in crime crashes 311; do $H dfs -mkdir -p /data/raw/$ds; done
$H dfs -expunge >/dev/null 2>&1
rm -f data/mr/*.tsv
if [ "$MODE" = semua ]; then
  rm -rf data/landing/* web_export/* 2>/dev/null
  echo "landing dan web_export dikosongkan"
fi
echo "== Sesudah =="; $H dfs -du -s -h /data/raw /data/clean /data/processed /data/mr 2>/dev/null
echo "Reset $MODE selesai."
