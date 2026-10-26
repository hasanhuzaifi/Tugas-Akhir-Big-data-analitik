# Aplikasi Web Tugas Akhir (Chicago Crime Big Data)
Folder proyek (terpisah dari vault Obsidian). PHP 8.3 + MySQL Laragon + Tailwind/daisyUI + Chart.js. Tanpa login.
- Laragon `www\chicago-crime` adalah junction ke folder ini: `http://localhost/chicago-crime`.
- Nyalakan MySQL Laragon (3306), lalu `php setup.php` mengisi DB `chicago_bigdata` dari `data/`.
- Tes tanpa Laragon: `php -S 127.0.0.1:8099`. `screenshots/` hasil uji.
- Job PySpark/MapReduce dijalankan `jobs.php` lewat WSL (repo `~/tugas-akhir-bigdata`).
