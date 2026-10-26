#!/bin/bash
# Jalankan MapReduce di YARN: hitung kejahatan per district|hari|jam dari /data/raw/crime/*.csv
# Prasyarat: HDFS + YARN (start-yarn.sh) hidup. Keluaran: /data/mr/crime_dhh dan data/mr/crime_dhh.tsv
set -e
H=/usr/local/hadoop
D=$(cd "$(dirname "$0")" && pwd)
$H/bin/hdfs dfs -rm -r -f /data/mr/crime_dhh >/dev/null 2>&1 || true
$H/bin/hadoop jar $H/share/hadoop/tools/lib/hadoop-streaming-3.5.0.jar \
  -D mapreduce.job.reduces=2 \
  -files "$D/crime_mapper.py,$D/crime_reducer.py" \
  -mapper "python3 crime_mapper.py" -combiner "python3 crime_reducer.py" -reducer "python3 crime_reducer.py" \
  -input "/data/raw/crime/crime_*.csv" -output /data/mr/crime_dhh
mkdir -p data/mr
$H/bin/hdfs dfs -cat /data/mr/crime_dhh/part-* > data/mr/crime_dhh.tsv
wc -l data/mr/crime_dhh.tsv
