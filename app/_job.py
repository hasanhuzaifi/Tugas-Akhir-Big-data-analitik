"""Panel job bersama (Modul 1 dan Modul 2): tombol job, unduhan hasil, log berpolling."""
import streamlit as st
from _umum import inti

TXT = {"prep": "MapReduce prep (YARN) membersihkan data", "parquet": "Spark menyimpan Parquet", "mapreduce": "MapReduce crime_dhh",
       "bi": "Analisis BI (Spark)", "analisis": "Analisis lokasi dan jenis", "ml": "Machine learning (MLlib)", "export": "Ekspor hasil", "selesai": "Semua tahap selesai"}


def mulai(job, ds="all"):
    inti.jalankan_job(job, ds)
    st.session_state["job"] = {"nama": job, "ds": ds, "dilihat": set(), "selesai": False}
    st.toast(f"Memulai job {job}...", icon=":material/play_arrow:")


def jalan_sekarang():
    j = st.session_state.get("job")
    return bool(j) and not j["selesai"]


def panel_job(tombol, kunci, ds="all", unduh=True):
    """tombol: [(job, label)]. Job lain dikunci selama ada job berjalan."""
    sibuk = jalan_sekarang()
    cols = st.columns(len(tombol) + (1 if unduh else 0))
    for c, (j, lbl) in zip(cols, tombol):
        if c.button(lbl, key=f"{kunci}_{j}", disabled=sibuk, use_container_width=True):
            mulai(j, ds)
            st.rerun()
    if unduh and inti.siap():
        cols[-1].download_button("Unduh hasil (ZIP)", inti.zip_hasil(), "hasil_chicago_crime.zip", "application/zip", key=f"{kunci}_zip", type="primary", use_container_width=True)
    log_job()


def stepper(aktif, jalan):
    nama = ["Link dari web", "NiFi unduh", "HDFS raw", "MapReduce prep", "Parquet", "Analisis", "ML", "Unduh"]
    st.markdown('<div class="stepper">' + "".join(f'<span class="{"ok" if i < aktif else ("jalan" if i == aktif and jalan else "")}">{n}</span>' for i, n in enumerate(nama)) + "</div>", unsafe_allow_html=True)


@st.fragment(run_every=2.5)
def log_job():
    j = st.session_state.get("job")
    if st.session_state.get("impor"):
        st.code("\n".join(st.session_state["impor"]), language="text")
    if not j:
        st.code("Belum ada job dijalankan.", language="text")
        return
    r = inti.baca_log(j["nama"])
    for s in r["steps"]:
        if s not in j["dilihat"]:
            j["dilihat"].add(s)
            st.toast((TXT.get(s, f"Tahap {s}")) + ("" if s == "selesai" else " berjalan..."))
    st.code(r["log"] or "(menunggu keluaran)", language="text")
    if r["done"] and not j["selesai"]:
        j["selesai"] = True
        st.toast(f"Job {j['nama']} selesai." if r["ok"] else f"Job {j['nama']} gagal, lihat log.", icon=":material/check_circle:" if r["ok"] else ":material/error:")
        j["ok"] = r["ok"]
        st.cache_data.clear()
        st.rerun()  # buka kunci tombol dan muat data baru
