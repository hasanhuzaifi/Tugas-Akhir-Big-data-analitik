#!/bin/bash
# Pantau WSL saat job dari Streamlit berjalan (terminal kedua). Ctrl+C untuk keluar. Pakai: monitor.sh [detik]
cd "$(dirname "$0")/../.."
H=/usr/local/hadoop/bin
while true; do
  clear
  echo "== $(date '+%H:%M:%S') | Layanan Hadoop/NiFi/Streamlit =="
  jps | grep -E "NameNode|DataNode|ResourceManager|NodeManager|JobHistory|NiFi" | awk '{print "  "$2" (pid "$1")"}'
  pgrep -f "streamlit run" >/dev/null && echo "  Streamlit hidup" || echo "  Streamlit MATI"
  echo; echo "== Job YARN berjalan =="
  $H/yarn application -list -appStates RUNNING 2>/dev/null | grep -E "application_" | awk '{print "  "$1"  "$2"  "$6"  "$8}' || true
  [ -z "$($H/yarn application -list -appStates RUNNING 2>/dev/null | grep application_)" ] && echo "  (tidak ada)"
  echo; echo "== Job aplikasi (data/jobs) =="
  f=$(ls -t data/jobs/*.log 2>/dev/null | head -1)
  if [ -n "$f" ]; then
    echo "  berkas: $f"; echo "  tahap : $(grep -o '__STEP__[a-z]*' "$f" | tail -1)  $(grep -o '__EXIT__[0-9]*' "$f" | tail -1)"
    tail -n 8 "$f" | cut -c1-110 | sed 's/^/  /'
  else echo "  (belum ada)"; fi
  echo; echo "== HDFS =="
  $H/hdfs dfs -du -s -h /data/raw /data/clean /data/processed /data/mr 2>/dev/null | sed 's/^/  /'
  echo; echo "== web_export =="; ls -lt --time-style=+%H:%M:%S web_export 2>/dev/null | head -5 | awk '{print "  "$6"  "$7}'
  sleep "${1:-2}"
done
