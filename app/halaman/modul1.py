import datetime as dt

import pandas as pd
import streamlit as st
from _job import impor, jalan_sekarang, log_job, mulai, panel_job, stepper
from _umum import data, inti

nf = inti.nf
BLN = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
DS_PIL = {"Kejahatan": "crime", "Kecelakaan lalu lintas": "crashes", "Layanan 311": "311", "Semua dataset (3)": "all"}
ss = st.session_state

st.title("Modul 1: Import data dan preprocessing")
st.write("Dua langkah terpisah: (1) akuisisi, NiFi mengunduh ke HDFS; (2) preprocessing, MapReduce di YARN membersihkan lalu Parquet.")

ak = ss.get("akuisisi")
j = ss.get("job")
if j and j["nama"] == "preproses":
    aktif, jalan = inti.tahap_aktif("preproses", inti.baca_log("preproses")["steps"], j["selesai"]), not j["selesai"]
    if j["selesai"] and j.get("ok"):
        aktif, jalan = 5, False
elif j and j["nama"] in ("analitik", "pipeline"):
    aktif, jalan = inti.tahap_aktif(j["nama"], inti.baca_log(j["nama"])["steps"], j["selesai"]), not j["selesai"]
    if j["selesai"] and j.get("ok"):
        aktif, jalan = 8, False
elif ak:
    aktif, jalan = (3, False) if (ak.selesai and not ak.gagal) else (2, True) if ak.log else (1, True)
else:
    aktif, jalan = 0, False
stepper(aktif, jalan)

# ---------- 1. akuisisi ----------
with st.container(border=True):
    st.subheader("1. Akuisisi data (NiFi ke HDFS)")
    st.caption("Link API disusun otomatis. Bulan yang sama diambil dua kali tidak menggandakan data (duplikat dibuang).")
    sibuk = jalan_sekarang() or bool(ak and not ak.selesai)
    dsl = st.radio("Dataset", list(DS_PIL), horizontal=True, key="dsl")
    ds = DS_PIL[dsl]
    daftar = ["crime", "crashes", "311"] if ds == "all" else [ds]
    bulan = [(y, m) for y in range(2026, 2023 - 1, -1) for m in range(12, 0, -1) if (2023, 10) <= (y, m) <= (2026, 10)]
    lbl = lambda ym: f"{BLN[ym[1] - 1]} {ym[0]}" + (" (sampai 15 Okt)" if ym == (2026, 10) else "")
    kustom = st.toggle("Lanjutan: rentang tanggal kustom", key="kustom")
    if not kustom:
        ym = st.selectbox("Bulan", bulan, index=bulan.index((2026, 9)), format_func=lbl, key="bulan")
        rg = inti.rentang_bulan(*ym)
    else:
        c = st.columns(2)
        dari = c[0].date_input("Dari tanggal", dt.date(2026, 9, 1), min_value=dt.date(2023, 10, 25), max_value=dt.date(2026, 10, 15))
        sampai = c[1].date_input("Sampai (tidak termasuk)", dt.date(2026, 10, 1), min_value=dt.date(2023, 10, 26), max_value=dt.date(2026, 10, 16))
        st.caption("Rentang kustom untuk uji coba: maksimal 366 hari per dataset, atau 92 hari bila memilih Semua dataset. Dataset 311 sangat besar, jadi rentang panjang memakan waktu dan memori.")
        rg = (dari.isoformat(), sampai.isoformat())
        if sampai <= dari:
            st.error("Tanggal akhir harus setelah tanggal awal.")
            rg = None
    if rg:
        st.caption("Link yang akan dikirim:")
        for k in daftar:
            st.markdown(f"**{inti.NAMA_DS[k]}:** `{inti.url_bulan(k, *rg)}`")
        h = inti.hari(rg)
        per = ", ".join(f"{inti.NAMA_DS[k]} ±{(lambda mb: nf(mb / 1000, 2) + ' GB' if mb >= 1000 else nf(mb) + ' MB')(h * inti.MB_HARI[k])}" for k in daftar)
        tot = inti.taksir_mb(daftar, rg)
        paket = inti.HARI_PAKET * sum(inti.MB_HARI.values())
        st.markdown(f"Perkiraan ukuran unduhan: **{nf(tot / 1000, 2) + ' GB' if tot >= 1000 else nf(tot) + ' MB'}** ({per}). Paket penuh ±{nf(paket / 1000, 2)} GB.")
    c = st.columns(2)
    if c[0].button("Ambil data pilihan", type="primary", disabled=sibuk, key="kirim"):
        maks = 92 if len(daftar) > 1 else 366
        if not rg:
            st.error("Isi tanggal dari dan sampai.")
        elif kustom and inti.hari(rg) > maks:
            st.error(f"Rentang kustom maksimal {maks} hari. Persempit rentang atau pilih satu dataset.")
        else:
            ss["dsPipe"] = "all" if len(daftar) > 1 else daftar[0]
            ss["akuisisi"] = inti.Akuisisi([(k, rg) for k in daftar], 'Akuisisi selesai. Klik "Jalankan preprocessing" di bagian 2.')
            st.rerun()
    if c[1].button("Unduh paket lebih dari 1 GB", disabled=sibuk, key="paket"):
        ss["konfirm_paket"] = True
    if ss.get("konfirm_paket") and not sibuk:
        st.warning("Unduh paket penuh ±1,7 GB (tiga dataset, 3 tahun)? Butuh beberapa menit dan memori WSL besar. Dikirim satu per satu (311 ditunggu masuk HDFS dulu).")
        y, n = st.columns(2)
        if y.button("Ya, unduh paket", key="paket_ya"):
            ss["konfirm_paket"] = False
            ss["dsPipe"] = "all"
            ss["akuisisi"] = inti.Akuisisi([(k, r) for k in ("crime", "crashes", "311") for r in inti.PAKET], 'Paket >1 GB sudah di HDFS. Klik "Jalankan preprocessing" di bagian 2.')
            st.rerun()
        if n.button("Batal", key="paket_batal"):
            ss["konfirm_paket"] = False
            st.rerun()
    st.caption("Paket = tiga dataset, seluruh periode 25 Okt 2023 sampai 15 Okt 2026, dikirim per tahun (±1,7 GB; syarat dosen lebih dari 1 GB).")


    @st.fragment(run_every=2.5)
    def status_akuisisi():
        a = ss.get("akuisisi")
        if not a:
            return
        for t_, jn, tx in a.log[-12:]:
            {"ok": st.success, "gagal": st.error}.get(jn, st.info)(f"[{t_}] {tx}")
        if a.masuk:
            st.code("\n".join(a.masuk), language="text")
        if a.selesai and not ss.get("akuisisi_toast"):
            ss["akuisisi_toast"] = True
            st.toast("Akuisisi selesai." if not a.gagal else "Akuisisi gagal, lihat log.", icon=":material/check_circle:" if not a.gagal else ":material/error:")
            st.rerun()
        elif not a.selesai:
            ss["akuisisi_toast"] = False

    status_akuisisi()
    c = st.columns(4)
    c[0].link_button("Buka NiFi", "https://localhost:8443/nifi")
    c[1].link_button("Buka HDFS UI", "http://localhost:9870")
    c[2].link_button("YARN UI", "http://localhost:18088")
    if c[3].button("Cek ukuran HDFS", key="cek_hdfs", disabled=jalan_sekarang()):
        mulai("hdfs")
        st.rerun()

    try:
        m1, hd = data()["m1"], data()["hdfs"]
    except Exception:
        m1 = hd = None
    if m1:
        cols = st.columns(3)
        for col, (k, v) in zip(cols, m1.items()):
            col.markdown(f"<div style='border-left:4px solid #1478B5;padding-left:12px'><div class='muted'>{inti.NAMA_DS.get(k, k)}</div><div class='big'>{nf(hd.get(k + '_raw_mb', 0), 1)} MB</div><div class='muted'>/data/raw/{k}</div></div>", unsafe_allow_html=True)
        st.write(f"Total mentah: **{nf(hd['total_raw_gb'], 2)} GB** (syarat dosen: lebih dari 1 GB).")

# ---------- 2. preprocessing ----------
with st.container(border=True):
    st.subheader("2. Preprocessing (MapReduce di YARN)")
    st.caption("Jalankan setelah akuisisi selesai (data pilihan di atas). Mapper membaca CSV, mengubah tipe, membuat fitur waktu, dan membuang baris di luar rentang. Reducer menyisakan satu baris per ID (versi terbaru) dan menghitung duplikat lewat counter Hadoop. Hasil TSV di /data/clean, lalu Spark menyimpannya sebagai Parquet di /data/processed tanpa hari terakhir yang belum lengkap.")
    if st.button("Jalankan preprocessing", type="primary", disabled=jalan_sekarang() or bool(ak and not ak.selesai), key="prep"):
        mulai("preproses", ss.get("dsPipe", "crime"))
        st.rerun()
    if m1:
        nama = inti.NAMA_DS
        tb = pd.DataFrame([{"Dataset": nama.get(k, k), "Baris masuk": v["rows_in"], "Duplikat": v["dup_identical"] + v["dup_key"], "Hari parsial dibuang": v["dropped_partial_day"], "Baris akhir": v["rows_final"]} for k, v in m1.items()])
        ti, to = int(tb["Baris masuk"].sum()), int(tb["Baris akhir"].sum())
        tb.loc[len(tb)] = ["Total", ti, None, "", to]
        st.dataframe(tb.assign(**{c_: tb[c_].map(lambda v: "" if pd.isna(v) else nf(v)) for c_ in ("Baris masuk", "Duplikat", "Baris akhir")}), hide_index=True, use_container_width=True)
        st.caption(f"Selisih {nf(ti - to)} baris adalah duplikat dan hari parsial yang dibuang agar hitungan harian tidak menipu.")

# ---------- 3. analisis, ML, database ----------
with st.container(border=True):
    st.subheader("3. Analisis, ML, dan database")
    st.caption("Satu tombol menjalankan MapReduce, analisis BI, machine learning, dan ekspor. Lalu impor hasilnya ke MySQL (`chicago_bigdata`).")
    c = st.columns(2)
    if c[0].button("Jalankan analisis dan ML", disabled=jalan_sekarang(), key="analitik"):
        mulai("analitik", "all")
        st.rerun()
    if c[1].button("Impor ke MySQL", key="impor1"):
        impor()

st.subheader("Log job")
log_job()
st.caption("Job butuh HDFS (dan YARN untuk MapReduce) hidup. Bila mati, aplikasi tetap menampilkan hasil tersimpan.")
