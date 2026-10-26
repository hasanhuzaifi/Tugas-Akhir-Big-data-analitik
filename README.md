# Chicago Crime Safety (Tugas Akhir Big Data & Analitik)

Analisis dan peringatan kejahatan untuk warga Chicago. Data 3 tahun (2023-10-25 s/d 2026-10-15): Chicago Crimes, 311 Service Requests (tanpa `311 INFORMATION ONLY CALL` dan `Aircraft Noise Complaint`), Traffic Crashes. Raw di HDFS 1,69 GB.

Alur: Socrata API -> NiFi (`ListenHTTP`/`GenerateFlowFile` -> `SplitText` -> `ExtractText` -> `InvokeHTTP` -> `UpdateAttribute` -> `PutFile` -> `PutHDFS`) -> HDFS `/data/raw/{crime,crashes,311}` -> MapReduce prep (`src/mr/`) -> `/data/clean` -> Spark (`src/load_parquet.py`) -> Parquet `/data/processed/*` -> BI (`src/bi.py`) + ML (`src/ml.py`) -> web Laragon (`web/`) dengan lapisan job Laravel (`web/laravel-jobs`, `php artisan serve --port=8010`).

## Menjalankan dari nol (WSL2 Ubuntu, Hadoop 3.5, Spark 4.0, NiFi 2.12)
1. Hadoop: `start-dfs.sh` (jangan `namenode -format`). Daemon harus hidup di sesi WSL yang tetap terbuka.
2. NiFi: pasang `nifi-hadoop-nar` dan `nifi-hadoop-libraries-nar` 2.12.0 (Maven Central) ke `$NIFI_HOME/lib` agar `PutHDFS` ada. Java 21. `nifi.sh run`.
3. Flow: `NIFI_PASS=... python3 nifi/build_flow.py`, lalu start semua processor di UI `https://localhost:8443/nifi`.
4. `python -m src.preprocess && python -m src.bi && python -m src.ml` (Java 17; Spark `local[2]`, `spark.local.dir` di disk, bukan `/tmp` tmpfs).
5. Tes: `python -m tests.test_m1`, `python -m tests.test_bi`.
6. UI: `streamlit run app/streamlit_app.py`.

## Hasil singkat
Lihat `data/ml/metrics.json` dan `data/bi/`. Fitur 311 dan kecelakaan tidak memperbaiki prediksi harian dibanding model crime saja; RandomForest crime saja hanya sedikit lebih baik dari baseline rata-rata 7 hari.

Prakiraan statistik, bukan kepastian; bukan pengganti informasi resmi kepolisian.
