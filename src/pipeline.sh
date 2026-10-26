#!/bin/bash
# Pipeline lengkap setelah NiFi menaruh CSV di /data/raw: MapReduce prep -> Parquet -> MapReduce crime_dhh -> BI -> analisis -> ML -> ekspor web.
# Pakai: src/pipeline.sh [crime|crashes|311|all]. Penanda __STEP__<nama> dibaca web (jobs.php) untuk stepper.
set -e
cd "$(dirname "$0")/.."
PY=.venv/bin/python
bash src/mr/run_prep.sh "${1:-all}"
echo "__STEP__parquet"; $PY -m src.load_parquet "${1:-all}"
echo "__STEP__mapreduce"; bash src/mr/run_mr.sh
echo "__STEP__bi"; $PY -m src.bi
echo "__STEP__analisis"; $PY -m src.analisis
echo "__STEP__ml"; $PY -m src.ml
echo "__STEP__export"; $PY -m src.export_web
echo "__STEP__selesai"
