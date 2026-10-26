# DESIGN.md: Peta Kejahatan Chicago (Tugas Akhir Big Data)

Dokumen ini ditulis sebelum kode. Pedoman: skill `frontend-design`. Pemilik keputusan visual: halaman web di folder ini. Spesifikasi fungsi ada di vault: `references/PRD-web.md`.

## 1. Subjek, pengguna, tugas utama
- **Subjek:** kejahatan terlapor di Chicago, 25 Okt 2023 sampai 15 Okt 2026 (730.504 kejadian), diperkaya data 311 dan kecelakaan.
- **Pengguna:** (a) dosen dan penguji, yang menilai Modul 1 (import + preprocessing) dan Modul 2 (BI + ML); (b) warga atau analis yang ingin tahu **di mana, kapan, dan jenis apa** kejahatan terjadi.
- **Tugas utama:** memilih jenis kejahatan, melihat sebaran lokasinya di peta, membandingkannya dengan jenis lain, lalu melihat apa yang diprakirakan untuk hari berikutnya.
- **Rasa yang dituju:** papan informasi transit kota, bukan dasbor korporat. Tegas, terbaca dari jauh, tiap warna bermakna.

## 2. Arah visual (pilihan khusus subjek)
Chicago punya tiga identitas visual yang bisa dipakai jujur: **jalur kereta L** (delapan warna jalur), **bendera kota** (garis biru muda, bintang merah), dan **huruf Big Shoulders** (dipesan Kota Chicago untuk papan dan kendaraan). Ketiganya dipakai.

- Jenis kejahatan diberi warna **jalur L**. Satu jenis = satu warna di seluruh aplikasi (grafik, legenda, peta, kartu). Ini menyatukan sistem dan memudahkan membandingkan.
- Navigasi Modul 2 digambar sebagai **satu jalur kereta dengan tiga stasiun** (Di mana, Apa dan kapan, Besok). Urutan ini nyata (alur analisis), jadi penomoran stasiun memang membawa informasi.
- Peta panas memakai skala satu warna hangat (kuning ke merah tua) di atas peta dasar abu dingin, supaya satu-satunya hal yang "panas" di layar adalah datanya.

## 3. Token

### Warna (6 nama dasar)
| Token | Hex | Peran |
|---|---|---|
| `--aspal` | `#16202B` | teks, bilah atas, garis |
| `--kabut` | `#ECEFF2` | latar halaman (abu dingin, bukan krem) |
| `--kertas` | `#FFFFFF` | permukaan panel |
| `--danau` | `#1478B5` | aksi utama, tautan, fokus |
| `--bendera` | `#C4262E` | titik panas, peringatan, risiko Tinggi |
| `--peron` | `#F5C518` | sorotan pilihan aktif (satu per layar) |

Garis dan teks sekunder: `--garis #CBD3DB`, `--redam #55626F` (kontras 5,9:1 di atas `--kabut`).

### Warna kategori (jalur L untuk 8 jenis teratas, 4 warna tambahan untuk 12 jenis)
Merah `#C60C30`, Biru `#00A1DE`, Cokelat `#62361B`, Hijau `#009B3A`, Oranye `#F9461C`, Ungu `#522398`, Merah muda `#E27EA6`, Kuning `#C9A400` (kuning L digelapkan agar terbaca di latar putih). Jenis ke-9 sampai ke-12 memakai hijau teduh `#00796B`, biru tua `#1A3A8F`, zaitun `#7C8B00`, magenta `#B0007A`; LAINNYA abu `#7A8794`. Setiap seri juga diberi label langsung, tidak mengandalkan warna saja.

### Skala panas (peta dan heatmap jam)
`#FFF3B0` → `#FDBE4B` → `#F26B38` → `#C4262E` → `#6E0F1A`, interpolasi linear dalam ruang warna terang yang meningkat monoton.

### Tipografi
- **Big Shoulders Display** (600/800): judul, angka besar, label stasiun. Bentuknya sempit dan padat seperti papan jalan, jadi angka besar muat tanpa dekorasi.
- **IBM Plex Sans** (400/500/600): isi, tabel, kontrol. Terang dan jelas pada ukuran kecil, angka tabular tersedia (`font-variant-numeric: tabular-nums`).
- Skala: 13 / 15 / 17 / 22 / 34 / 56 px. Panjang baris isi maksimum 70 karakter. Tidak ada huruf kapital semua untuk label, tidak ada satu kata disorot di judul.
- Font disimpan lokal di `assets/fonts/` agar demo jalan tanpa internet.

### Bentuk dan jarak
- Radius dua tingkat saja: 2 px (kontrol, tabel) dan 10 px (panel besar). Tidak ada bayangan lembut seragam; kedalaman dari garis 1 px `--garis` dan satu bayangan tegas pada panel yang melayang (kotak filter di atas peta).
- Grid dasar 8 px. Gutter 16 px di ponsel, 24 px di desktop. Lebar konten maksimum 1280 px.

## 4. Tata letak

```
+--------------------------------------------------------------+
| PETA KEJAHATAN CHICAGO     Beranda  Modul 1  Modul 2        |  bilah aspal
+--------------------------------------------------------------+
| Modul 2:  (1)--------(2)--------(3)                          |  jalur L
|        Di mana    Apa dan kapan   Besok                      |
+--------------------------------------------------------------+
| [pilih jenis: THEFT v] [bandingkan: BATTERY v] [periode]     |  kontrol
|  +------------------------------+  +-----------------------+ |
|  |                              |  | 3 angka kunci         | |
|  |   PETA PANAS (Leaflet)       |  | district teratas      | |
|  |                              |  | insight otomatis      | |
|  +------------------------------+  +-----------------------+ |
+--------------------------------------------------------------+
```

- Peta adalah elemen yang paling diingat (satu momen berani). Semua lain tenang: putih, garis tipis, sedikit warna.
- Rata kiri. Angka rata kanan di tabel. Tidak ada kartu identik berderet: panel berbeda ukuran sesuai isi (peta lebar, ringkasan sempit, tabel penuh).
- Beranda dibuka dengan **peta panas kecil hidup** (bukan angka besar dengan gradasi), karena itu hal paling khas dari subjek ini.

## 5. Tiga analisis utama (BI sesuai ketentuan dosen)
1. **Di mana (analisis spasial).** Peta panas kejadian per sel 0,005 derajat (±0,5 km), difilter per jenis kejahatan dan periode. Pilih jenis kedua untuk **membandingkan**: tampil mode "selisih" (merah = lebih padat di jenis A, biru = lebih padat di jenis B) dan tabel district teratas keduanya. Sumber: PySpark `src/analisis.py`.
2. **Apa dan kapan (perbandingan jenis).** Pilih 1 sampai 4 jenis: tren bulanan (diindeks 100 pada bulan pertama agar jenis besar dan kecil sebanding), heatmap jam × hari per jenis, profil (rasio penangkapan, persen domestik, konsentrasi district), dan korelasi antarjenis. Insight otomatis dalam kalimat.
3. **Besok (machine learning).** Prakiraan per district dari model terbaik (RandomForest, RMSE 6,50 lawan pembanding 6,76), kartu risiko Rendah/Sedang/Tinggi, aktual lawan prediksi, fitur terpenting, dan hasil jujur bahwa 311 dan kecelakaan tidak menambah akurasi. Termasuk pembandingan MapReduce (YARN) lawan Spark.

Modul 1 tetap: import (NiFi PutHDFS), duplikasi, preprocessing, simpan ke HDFS; tombol menjalankan job di WSL dengan log langsung.

## 6. Interaksi
- Filter disimpan di URL (`?jenis=THEFT&banding=BATTERY`), sehingga tautan bisa dibagikan dan peta bisa diambil screenshot dengan keadaan tertentu.
- Peta: arahkan kursor ke sel untuk jumlah kejadian; tombol "Reset" mengembalikan tampilan; ganti mode (Kepadatan | Selisih).
- Grafik: legenda dapat diklik, tooltip menampilkan angka penuh. Semua kontrol dapat dioperasikan dengan papan ketik, fokus tampak (garis `--danau` 2 px).
- Gerak hanya menjawab aksi pengguna (transisi warna sel peta 150 ms, grafik beranimasi 400 ms sekali). `prefers-reduced-motion` mematikannya. Tidak ada animasi masuk per bagian.

## 7. Prinsip
1. Satu jenis kejahatan punya satu warna di mana pun.
2. Angka selalu disertai satuan dan asal data (Spark, MapReduce, MySQL).
3. Jujur pada batas data: lonjakan 00.00 adalah waktu bawaan, bukan jam rawan; korelasi bukan sebab-akibat; prakiraan bukan kepastian.
4. Berfungsi tanpa internet (font, Leaflet, Chart.js lokal; tanpa ubin peta dasar: ubin CARTO butuh API key dan internet, jadi sel panas digambar sendiri di atas latar abu).
5. Responsif sampai 360 px; kontras teks minimal 4,5:1; target sentuh 40 px.

## 8. Tinjauan terhadap default (sebelum membangun)
| Kecenderungan umum | Rencana awal | Perubahan |
|---|---|---|
| Latar krem + serif + terakota | latar abu dingin, sans, tanpa terakota | tetap |
| Hitam + hijau neon | latar terang, aksen biru danau dan merah bendera | tetap |
| Kartu seragam bersudut sama dengan bayangan sama | panel berbeda ukuran, radius 2 dan 10 px, tanpa bayangan seragam | tetap |
| Eyebrow huruf kapital di atas tiap judul, panah pada tautan | tidak dipakai | tetap |
| Hero angka besar + gradasi | hero berupa peta panas hidup | diganti dari rencana awal "angka besar 0,67" |
| Warna kategori acak | warna jalur L, bermakna di Chicago | dipertahankan |
| Penomoran 01/02/03 sebagai hiasan | hanya pada jalur tiga stasiun (urutan nyata) | tetap |

## 9. Kriteria selesai (uji Playwright)
Tiga halaman Modul 2 dan Modul 1 dan Beranda di 1366 px dan 390 px: tanpa galat konsol, tanpa gulir horizontal, peta tampil sel, ganti jenis mengubah peta dan URL, mode selisih bekerja, perbandingan 4 jenis menampilkan 4 warna berbeda. Screenshot disimpan di `screenshots/` dan dipakai laporan.
