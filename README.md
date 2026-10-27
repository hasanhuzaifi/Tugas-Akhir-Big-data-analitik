# Chicago Crime Safety Insight

Tugas Akhir Big Data & Analitik. Aplikasi web yang menganalisis dan memprediksi kejahatan kota Chicago dari data terbuka, dibangun di atas pipeline Big Data lengkap: **NiFi, HDFS, MapReduce (YARN), Spark/MLlib, MySQL, PHP (Laragon), dan Laravel**.

Repositori: https://github.com/hasanhuzaifi/Tugas-Akhir-Big-data-analitik

Penulis: Hasan Huzaifi

## Daftar isi
1. [Tentang proyek](#tentang-proyek)
2. [Data](#data)
3. [Arsitektur](#arsitektur)
4. [Struktur repositori](#struktur-repositori)
5. [Cara mencoba](#cara-mencoba)
   - [Jalur A: hanya melihat web (10 menit)](#jalur-a-hanya-melihat-web-10-menit)
   - [Jalur B: pipeline penuh](#jalur-b-pipeline-penuh)
6. [Memakai aplikasi](#memakai-aplikasi)
7. [Hasil utama](#hasil-utama)
8. [Detail teknis](#detail-teknis)
9. [Pengujian](#pengujian)
10. [Pemecahan masalah](#pemecahan-masalah)
11. [Keterbatasan](#keterbatasan)

## Tentang proyek
Warga dan petugas perlu tahu **di mana**, **kapan**, dan **jenis** kejahatan yang berisiko. Proyek ini:
- mengambil data dari API Socrata (portal data Chicago) lewat link yang disusun web dari pilihan dataset dan periode,
- membersihkan dan menyimpannya di HDFS,
- menganalisis dengan Spark dan MapReduce,
- memprediksi jumlah kejahatan harian dengan MLlib,
- menampilkan hasilnya di web interaktif (peta panas interaktif, perbandingan jenis, prakiraan besok dengan penjelajah per district).

Hasilnya prakiraan statistik, bukan kepastian, dan bukan pengganti informasi resmi kepolisian.

## Data
Tiga dataset dari `data.cityofchicago.org`, rentang 3 tahun (2023-10-25 sampai 2026-10-15), total mentah 1,69 GB.

| Dataset | Isi | Baris setelah bersih |
|---|---|---|
| `crime` | Chicago Crimes | 730.504 |
| `crashes` | Traffic Crashes | 332.462 |
| `311` | 311 Service Requests (tanpa `311 INFORMATION ONLY CALL` dan `Aircraft Noise Complaint`) | 2.766.517 |

## Arsitektur
```
Web Modul 1 (pilih dataset + periode -> link Socrata disusun otomatis)
  -> PHP validasi (host data.cityofchicago.org + 3 resource)
  -> NiFi ListenHTTP :8081 /ingest   (baris "dataset|nama|url")
  -> SplitText -> ExtractText -> InvokeHTTP -> UpdateAttribute
  -> PutFile   data/landing/<dataset>   (salinan lokal)
  -> PutHDFS   /data/raw/<dataset>
  -> MapReduce prep (Hadoop Streaming, YARN)  -> /data/clean (TSV)
  -> Spark load_parquet                       -> /data/processed (Parquet)
  -> MapReduce crime_dhh + Spark bi / analisis / ml
  -> export_web -> MySQL -> Web Modul 2 (Di mana, Apa dan kapan, Besok)
```
Tombol job di web (Streamlit) menjalankan skrip `.py` / `.sh` di WSL lewat `subprocess` dengan daftar job yang diizinkan (whitelist).

## Struktur repositori
```
nifi/               build_flow.py (membangun flow lewat REST API), flow.json (hasil ekspor)
src/
  pipeline.sh       merangkai semua tahap, mencetak penanda __STEP__
  mr/               MapReduce: prep_mapper/reducer, crime_mapper/reducer, run_prep.sh, run_mr.sh
  load_parquet.py   TSV bersih -> Parquet
  bi.py             KPI, tren, heatmap, korelasi lag
  analisis.py       peta sel, jenis x bulan/jam/district, korelasi jenis
  ml.py             fitur lag, GBT dan RandomForest, risiko H+1
  export_web.py     hasil -> berkas untuk impor MySQL
tests/              test_m1.py, test_bi.py, test_mr.py
web/                aplikasi web Laragon (PHP): index, modul1, modul2, kode, jobs.php, setup.php
web/data/           hasil analisis siap impor (CSV/JSON/TSV) untuk Jalur A
docs/               peta-kode-spark.md (lokasi dan penjelasan sintaks semua skrip)
data/bi, data/ml    keluaran analisis dan metrik model
```

## Cara mencoba

### Jalur A: hanya melihat web (10 menit)
Tidak butuh Hadoop, Spark, atau NiFi. Hasil analisis sudah ada di `web/data/`.

Kebutuhan: Windows/Linux/macOS dengan **Laragon** (Apache + MySQL + PHP 8.2+) atau PHP dan MySQL biasa.

1. Klon repo:
   ```bash
   git clone https://github.com/hasanhuzaifi/Tugas-Akhir-Big-data-analitik.git
   ```
2. Salin folder `web/` ke `C:\laragon\www\chicago-crime\` (Laragon), atau pakai server bawaan PHP.
3. Nyalakan **MySQL** (user `root`, tanpa sandi, bawaan Laragon). Sesuaikan di `web/lib.php` bila sandi Anda berbeda.
4. Impor data ke MySQL (membuat database `chicago_bigdata`):
   ```bash
   php web/setup.php          # di folder repo, atau buka http://localhost/chicago-crime/setup.php
   ```
5. Buka `http://localhost/chicago-crime/` (atau `php -S 127.0.0.1:8099 -t web`, lalu `http://127.0.0.1:8099`).
6. Yang bisa dicoba tanpa pipeline: Beranda, **Modul 2** (Di mana, Apa dan kapan, Besok). Tombol job di Modul 1 dan halaman **Kode** butuh pipeline (lihat Jalur B).

### Jalur B: pipeline penuh
Kebutuhan:
- Windows 11 + **WSL2 Ubuntu**, RAM minimal 16 GB (disarankan), disk kosong >= 15 GB
- Java 17 (Hadoop/Spark) dan Java 21 (NiFi 2.12)
- Hadoop 3.5 (HDFS + YARN, mode pseudo-distributed), Spark 4.0, NiFi 2.12
- Python 3.10+ dengan `pyspark==4.0.0`, `pandas`, `pyarrow` (`pip install -r requirements.txt`)
- MySQL (opsional, untuk tombol Impor ke MySQL)

Langkah:
1. **Klon repo ke WSL**: `git clone https://github.com/hasanhuzaifi/Tugas-Akhir-Big-data-analitik.git ~/tugas-akhir-bigdata`
2. **Lingkungan Python**: `cd ~/tugas-akhir-bigdata && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`
3. **Hadoop**: `start-dfs.sh; start-yarn.sh; jps` (harus ada NameNode, DataNode, ResourceManager, NodeManager). Jangan jalankan `namenode -format` pada HDFS yang sudah berisi data. Buat direktori: `hdfs dfs -mkdir -p /data/raw/{crime,crashes,311}`.
4. **NiFi**: pasang `nifi-hadoop-nar` dan `nifi-hadoop-libraries-nar` 2.12.0 (Maven Central) ke `$NIFI_HOME/lib` agar `PutHDFS` tersedia, lalu `nifi.sh start`. Buka `https://localhost:8443/nifi`.
5. **Bangun flow**: `NIFI_USER=<user> NIFI_PASS=<sandi> python3 nifi/build_flow.py`, lalu jalankan semua processor di UI **kecuali** `GenerateFlowFile` (biarkan STOPPED; kalau hidup, ia mengunduh semua bulan sekaligus). `nifi/flow.json` adalah hasil ekspor flow.
6. **Daemon harus hidup**: HDFS, YARN, dan NiFi mati bila sesi WSL berakhir. Jalankan di terminal WSL yang tetap terbuka, atau pakai `exec sleep infinity` di akhir perintah.
7. **Web**: salin `web/` ke Laragon (seperti Jalur A), jalankan `setup.php` bila MySQL masih kosong.
8. **Jalankan**: buka web, Modul 1, pilih dataset (atau Semua dataset) dan bulan (rentang kustom ada di Lanjutan), klik **Ambil data pilihan** (akuisisi: NiFi ke HDFS; perkiraan ukuran tampil), lalu **Jalankan preprocessing** (MapReduce prep di YARN, lalu Parquet). Tombol **Unduh paket lebih dari 1 GB** menarik tiga dataset seluruh periode (±1,7 GB, syarat dosen). Analisis dan ML dijalankan tombol terpisah di bagian 3. Atau jalankan tahap manual di WSL:
   ```bash
   bash src/pipeline.sh crime        # crime | crashes | 311 | all
   ```

Contoh link yang diterima (host dan resource dibatasi):
```
https://data.cityofchicago.org/resource/ijzp-q8t2.csv?$where=date between '2026-10-10T00:00:00' and '2026-10-10T23:59:59'
```

## Memakai aplikasi
| Halaman | Fungsi |
|---|---|
| Beranda | Temuan utama, KPI, peta mini, alur pipeline |
| **Modul 1: Import** | Pilih dataset atau Semua dataset, lalu satu bulan atau rentang kustom (tanpa mengetik link), kirim ke NiFi dengan notifikasi tiap tahap, lihat ukuran di HDFS, jalankan pipeline dengan stepper 8 tahap |
| **Modul 2: Analisis** | Tiap tahap diawali kotak **Kesimpulan** dan cara membaca. **Di mana**: peta panas halus yang bisa di-zoom dan layar penuh, slider radius dan ambang, daftar titik terpanas, mode Selisih antar jenis. **Apa dan kapan**: jenis x bulan/jam/district, pilihan cepat, korelasi. **Besok**: kartu risiko yang bisa disaring dan diklik (meter risiko, prakiraan vs kenyataan, jam rawan) serta permainan **Tebak dulu** |
| **Kode** | Seluruh skrip PySpark, MapReduce, dan shell beserta lokasinya dan penjelasan sintaks |

## Hasil utama
- MapReduce dan Spark menghasilkan jumlah baris yang sama pada ketiga dataset.
- Prediksi jumlah kejahatan harian: **RandomForest (fitur crime saja) RMSE 6,50** vs baseline rata-rata 7 hari **6,76**; RMSE terbaik semua model 6,52.
- Temuan jujur: fitur tambahan 311 dan kecelakaan **tidak** memperbaiki prediksi.
- Tingkat penangkapan berbeda jauh antar jenis, contoh Narcotics 96,2% vs Theft 8,0%.
- Metrik lengkap: `data/ml/metrics.json`; KPI dan korelasi: `data/bi/`.

## Detail teknis
- **Pengawasan job**: log tiap job memuat penanda `__STEP__<nama>` dan `__EXIT__<kode>`; aplikasi membaca log job secara berkala.
- **Kebersihan data (MapReduce prep)**: mapper membersihkan kolom dan membuat fitur waktu; reducer membuang duplikat per kunci dan mengambil versi terbaru; counter `dup_identical` dan `dup_key` terlihat di UI YARN.
- **Penyimpanan ganda**: setiap berkas unduhan disimpan di `data/landing/<dataset>` (PutFile) sebelum masuk HDFS (PutHDFS), ukuran keduanya sama. Hapus `data/landing` bila disk sempit.
- Peta kode lengkap: [`docs/peta-kode-spark.md`](docs/peta-kode-spark.md).

## Pengujian
Dari folder repo di WSL:
```bash
PYTHONPATH=. .venv/bin/python -m tests.test_m1 --parquet   # bersih data dan kunci
PYTHONPATH=. .venv/bin/python -m tests.test_bi
PYTHONPATH=. .venv/bin/python -m tests.test_mr             # total MapReduce = Spark
```

## Pemecahan masalah
| Gejala | Penyebab | Tindakan |
|---|---|---|
| `Connection refused localhost:9000` | HDFS mati (sesi WSL berakhir) | `start-dfs.sh; start-yarn.sh` di terminal WSL yang tetap terbuka |
| Tombol job tidak bereaksi | Streamlit belum jalan | `.venv/bin/streamlit run app/streamlit_app.py --server.port 8501` |
| Kirim link: NiFi tidak terjangkau | NiFi mati atau ListenHTTP berhenti | `nifi.sh start`, jalankan processor |
| NiFi mengunduh semua bulan | `GenerateFlowFile` hidup | Hentikan processor itu |
| Halaman Modul 2 kosong | MySQL belum terisi | `php web/setup.php` |
| Job gagal dengan jalur aneh | Spasi atau `&` di `run_dir` | Pakai jalur tanpa spasi, mis. `C:/Temp/bigdata-web` |
| OOM / `/tmp` penuh pada 311 | Spark memakai tmpfs | `spark.local.dir` ke disk, `local[2]`, 16 shuffle partition (sudah di kode) |
| Memori sistem habis | Hadoop + Spark + NiFi bersamaan | Tutup aplikasi lain, naikkan memori WSL (`.wslconfig`) |

## Keterbatasan
- Prakiraan harian berbasis pola historis; cuaca dan acara kota belum dimasukkan.
- Data hanya mencakup kejadian yang dilaporkan, sehingga ada bias pelaporan.
- Resolusi spasial sel peta sekitar 0,5 km; pembaruan data masih lewat link manual, belum terjadwal harian.
- Setup penuh (Jalur B) cukup berat dan dibuat untuk satu mesin; konfigurasi jalur (`config/jobs.php`) perlu disesuaikan di mesin lain.
- Salinan lokal PutFile menggandakan kebutuhan disk data mentah.

## Aplikasi (Streamlit)
Web kini Streamlit (folder `app/`): `.venv/bin/streamlit run app/streamlit_app.py --server.port 8501` lalu buka http://localhost:8501. Tes: `PYTHONPATH=. .venv/bin/python tests/test_app.py`. Versi PHP lama tetap di `web/` sebagai arsip (lapisan Laravel sudah dihapus, jadi tombol job di sana tidak berfungsi).
