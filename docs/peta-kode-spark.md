---
updated: 2026-10-26
---
# Peta kode analisis (PySpark + MapReduce)

Lokasi semua kode: repo WSL `~/tugas-akhir-bigdata` = `\\wsl.localhost\Ubuntu\home\lenovo\tugas-akhir-bigdata`. Dijalankan dari root repo dengan `.venv/bin/python -m src.<nama>`. Alur: (lihat README). Web memicu lewat whitelist job (`app/inti.py`, Streamlit).

## Urutan eksekusi (`src/pipeline.sh`)
`run_prep.sh` -> `load_parquet` -> `run_mr.sh` -> `bi` -> `analisis` -> `ml` -> `export_web`

| File | Peran | Masuk -> Keluar |
|---|---|---|
| `src/pipeline.sh` | Rangkai semua tahap, cetak `__STEP__<nama>` untuk stepper web | argumen `crime/crashes/311/all` |
| `src/mr/run_prep.sh` | Jalankan MapReduce prep di YARN, baca counter M1 | `/data/raw/<ds>` -> `/data/clean/<ds>`, `data/m1_summary.json` |
| `src/mr/prepcfg.py` | Konfigurasi kolom, tipe, tanggal mulai | dipakai mapper + load_parquet |
| `src/mr/prep_mapper.py` | Mapper: bersihkan CSV, turunkan kolom waktu | CSV -> `kunci<TAB>versi<TAB>kolom...` |
| `src/mr/prep_reducer.py` | Reducer: dedup per kunci, ambil versi terbaru | TSV bersih |
| `src/load_parquet.py` | Spark: TSV -> Parquet, buang hari parsial | `/data/clean` -> `/data/processed/<ds>` |
| `src/mr/run_mr.sh` | MapReduce hitung kejahatan per district/hari/jam | -> `data/mr/crime_dhh.tsv` |
| `src/mr/crime_mapper.py`, `crime_reducer.py` | Mapper/reducer-combiner untuk `run_mr.sh` | `dist|hari|jam<TAB>n` |
| `src/bi.py` | Spark: KPI, harian, mingguan, heatmap, top jenis, korelasi lag | -> `data/bi/*` |
| `src/analisis.py` | Spark: peta sel, jenis x bulan/jam/district, profil, korelasi jenis | -> `data/analisis/*` |
| `src/ml.py` | MLlib: prediksi harian per district, risiko H+1 | -> `data/ml/*` |
| `src/export_web.py` | Salin hasil ke `web_export/` untuk impor MySQL | -> `web_export/` |
| `src/ingest.py`, `src/preprocess.py` | Pembantu: `get_spark()`, konstanta `HDFS` | - |

## Penjelasan sintaks per file

### `src/mr/prepcfg.py`
- `CRIME/CRASHES/SR311 = "...".split()`: daftar kolom mentah dari string spasi.
- `DS = {nama: (kolom, kolom_versi, kolom_tanggal, kolom_turunan)}`: konfigurasi per dataset.
- `TIPE`: tipe Parquet selain string.
- `kolom(ds)`: urutan keluaran = mentah + turunan khusus + fitur waktu.

### `src/mr/prep_mapper.py` (Hadoop Streaming: baca stdin, tulis stdout)
- `sys.path.insert(0, os.getcwd())`: cari `prepcfg.py` di folder container YARN.
- `csv.reader(sys.stdin)`: urai CSV (field berkutip, koma di dalam).
- `valid[ds]`: lambda cek bentuk kunci; membuang header dan baris lanjutan field multi-baris.
- `bersih`: hapus tab/newline agar TSV aman.
- `datetime.strptime(...)`: urai tanggal; `ValueError` -> baris dibuang.
- `isoweekday() % 7 + 1`: hari 1=Minggu..7=Sabtu, sama dengan `dayofweek` Spark.
- `print("\t".join(...))`: keluaran mapper, kunci di kolom 1, versi di kolom 2.
- `reporter:counter:M1,rows_in,N` ke stderr: counter Hadoop.
- `~MAX\t<tanggal>`: penanda tanggal terbesar untuk membuang hari parsial.

### `src/mr/prep_reducer.py`
- Input sudah terurut kunci (shuffle). `flush(rows)` memproses satu kunci.
- `set(rows)`: baris identik jadi satu; selisih = `dup_identical`; sisa >1 = `dup_key`.
- `max(uniq, key=lambda l: l.split("\t",2)[1])`: ambil versi terbaru (kolom ke-2).
- `[2:]`: buang kunci dan versi dari keluaran.

### `src/load_parquet.py`
- `StructType/StructField(StringType)`: skema semua string, lalu `cast` ke tipe di `TIPE`.
- `spark.read.csv(sep="\t", quote="", mode="PERMISSIVE")`: baca TSV tanpa kutip.
- `filter(col == "~MAX")` + `agg(F.max)`: ambil tanggal terbesar.
- `df.filter(F.to_date(dcol) < mx)`: buang hari parsial terakhir.
- `write.mode("overwrite").parquet(...)`: simpan Parquet di HDFS.
- Ringkasan digabung ke `data/m1_summary.json` (`{**lama, **baru}`).

### `src/mr/crime_mapper.py` / `src/mr/crime_reducer.py`
- Mapper cetak `district|hari|jam<TAB>1`; reducer menjumlah (word count). Dipakai juga sebagai combiner agar shuffle kecil.

### `src/mr/run_prep.sh` dan `src/mr/run_mr.sh`
- `hadoop jar hadoop-streaming-*.jar`: jalankan skrip Python sebagai mapper/reducer di YARN.
- `-files`: kirim skrip ke container; `-D mapreduce.job.reduces=2`: 2 reducer.
- `-input`/`-output`: jalur HDFS; `hdfs dfs -rm -r -f`: hapus keluaran lama (Hadoop menolak timpa).
- `grep -q "completed successfully"`: gagal bila job tidak sukses. `set -e`: berhenti pada galat pertama.
- Heredoc `<<'EOF'` di `run_prep.sh`: Python kecil membaca counter dari log.

### `src/bi.py`
- `compute(df)`: `agg(F.avg(arrest.cast("int")))` = persen penangkapan; `groupBy(...).count()` = agregasi; `.toPandas()` = hasil kecil ke pandas.
- `date_trunc("week")`: awal minggu. `asfreq("D", fill_value=0)`: isi hari kosong 0.
- `s.corr(s.shift(i))`: korelasi Pearson autokorelasi lag 1..14.
- `ext_corr`: korelasi kejahatan vs 311/kecelakaan pada lag 0/7/14/30; `pd.concat(axis=1)` menyatukan deret harian.
- `save`: JSON untuk KPI/lag, Parquet untuk tabel.

### `src/analisis.py`
- `TOP=12`: 12 jenis terbesar, sisanya `LAINNYA` (`F.when(...).otherwise(...)`).
- `between(*LAT)`: saring titik di kotak Chicago.
- `floor(lat/CELL)*CELL + CELL/2`: pembulatan ke pusat sel 0,005 derajat (peta panas).
- `pivot(...).fillna(0)` lalu `.corr()`: matriks korelasi antarjenis; `melt` jadi format panjang.
- Keluaran CSV: `grid`, `type_month`, `type_hour`, `type_district`, `type_profile`, `type_corr`, `meta.json`.

### `src/ml.py`
- `daily()`: hitung kejadian per district per hari. `SR_GROUPS`: kelompok jenis 311.
- `explode(sequence(first, last+1, interval 1 day))` + `crossJoin`: kisi lengkap district x hari (termasuk H+1).
- `Window.partitionBy("district").orderBy("day")`; `F.lag("n",k)`; `rowsBetween(-7,-1)`: fitur hanya dari hari sebelumnya (tanpa kebocoran).
- `VectorAssembler` + `Pipeline` + `GBTRegressor` / `RandomForestRegressor`: model regresi.
- Uji = 365 hari terakhir (`date_sub(last, 365)`); metrik `mae/rmse/r2` lewat `RegressionEvaluator`.
- Baseline = `mean_7`. `featureImportances`: kepentingan fitur.
- `percentile_approx(n, 0.33/0.66)`: ambang risiko Rendah/Sedang/Tinggi per district.

### `src/export_web.py`
- `pd.read_parquet(...).to_csv(...)` dan `shutil.copy`: kumpulkan hasil ke `web_export/`.

### `src/ingest.py` dan `src/preprocess.py`
- `preprocess.py`: `get_spark()` membuat SparkSession lokal (`master local[2]`, memori driver 6g) dan konstanta `HDFS`; dipakai `load_parquet`, `bi`, `analisis`.
- `ingest.py`: salin CSV lokal ke HDFS `/data/raw/crime` (`hdfs dfs -put`); alur kini lewat web -> NiFi, (lihat README).

### `src/pipeline.sh`
- `set -e`: berhenti saat galat. `${1:-all}`: argumen default `all`. `echo "__STEP__x"`: penanda untuk stepper web.
