#!/bin/bash
# Preprocessing MapReduce di YARN: /data/raw/<ds>/*.csv -> /data/clean/<ds> (TSV bersih, dedup per kunci).
# Pakai: run_prep.sh [crime|crashes|311|all]. Counter M1 (rows_in, dup_identical, dup_key) ditulis ke data/m1_summary.json.
set -e
H=/usr/local/hadoop
D=$(cd "$(dirname "$0")" && pwd)
mkdir -p data
$H/bin/hdfs dfsadmin -safemode wait >/dev/null 2>&1  # HDFS baru restart: tunggu safe mode keluar
for ds in $( [ "${1:-all}" = all ] && echo crime crashes 311 || echo "$1" ); do
  echo "__STEP__prep:$ds"
  $H/bin/hdfs dfs -rm -r -f /data/clean/$ds >/dev/null 2>&1 || true
  $H/bin/hadoop jar $H/share/hadoop/tools/lib/hadoop-streaming-3.5.0.jar \
    -D mapreduce.job.reduces=2 -D mapreduce.job.name="prep-$ds" \
    -files "$D/prep_mapper.py,$D/prep_reducer.py,$D/prepcfg.py" \
    -mapper "python3 prep_mapper.py $ds" -reducer "python3 prep_reducer.py" \
    -input "/data/raw/$ds/*.csv" -output /data/clean/$ds 2>&1 | tee /tmp/prep_$ds.log | grep -E "map [0-9]+%|Counters|ERROR|Job .* (completed|failed)" || true
  grep -q "completed successfully" /tmp/prep_$ds.log || { echo "prep $ds gagal"; exit 1; }
  python3 - "$ds" <<'EOF'
import json, os, re, sys
ds = sys.argv[1]
log = open(f"/tmp/prep_{ds}.log").read()
c = {k: int(re.search(rf"\b{k}=(\d+)", log).group(1)) if re.search(rf"\b{k}=(\d+)", log) else 0 for k in ("rows_in", "dup_identical", "dup_key")}
p = "data/m1_summary.json"
s = json.load(open(p)) if os.path.exists(p) else {}
s[ds] = {**s.get(ds, {}), **c}
json.dump(s, open(p, "w"), indent=2)
print(ds, c)
EOF
done
