import pydeck as pdk
import streamlit as st
from _umum import inti, wajib_data

d = wajib_data()
k, g = d["kpi"], d["grid"]
m = d["model_metrics"].set_index("model")["rmse"]
top = d["district"].sort_values("count", ascending=False).iloc[0]
LANGKAH = [("Akuisisi", "NiFi + PutHDFS", "API Socrata ditarik per bulan oleh NiFi lalu ditulis ke HDFS."),
           ("Penyimpanan", "HDFS", "Tiga dataset mentah di /data/raw, hasil bersih Parquet di /data/processed."),
           ("Preprocessing", "MapReduce + Spark", "Dedup, buang hari parsial, standardisasi kolom."),
           ("Pemrosesan", "MapReduce di YARN", "Hadoop Streaming menghitung kejadian per district, hari, jam."),
           ("Analisis BI", "PySpark SQL", "Sebaran lokasi, perbandingan jenis, korelasi, tren."),
           ("Machine learning", "Spark MLlib", "RandomForest dan GBT memprediksi kejadian per district per hari."),
           ("Tampilan", "Streamlit", "Hasil dibaca langsung dari export; bisa diunduh sebagai CSV atau ZIP.")]

a, b = st.columns([1, 1])
with a:
    st.title("Di mana kejahatan di Chicago biasanya terjadi?")
    st.write(f"Pilih jenis kejahatan, lihat sebarannya di peta, bandingkan dengan jenis lain, lalu lihat prakiraan hari berikutnya. Data {inti.nf(k['total'])} laporan, 25 Okt 2023 sampai 15 Okt 2026.")
    c1, c2, c3 = st.columns(3)
    c1.page_link("halaman/modul2.py", label="Buka peta panas", icon=":material/map:")
    c2.page_link("halaman/modul2.py", label="Bandingkan jenis", icon=":material/compare:")
    c3.page_link("halaman/modul1.py", label="Lihat proses data", icon=":material/account_tree:")
with b:
    s = g.groupby(["la", "lo"], as_index=False)["n"].sum()
    p = inti.p98(list(s["n"]))
    s["w"] = s["n"].map(lambda n: inti.intensitas(n, p))
    st.pydeck_chart(pdk.Deck(
        layers=[pdk.Layer("HeatmapLayer", s, get_position="[lo, la]", get_weight="w", radiusPixels=18,
                          color_range=[[255, 243, 176], [253, 190, 75], [242, 107, 56], [196, 38, 46], [110, 15, 26]])],
        initial_view_state=pdk.ViewState(latitude=41.84, longitude=-87.68, zoom=9.2), map_style="light"), height=300)

c1, c2, c3 = st.columns(3)
gb = d["hdfs"]["total_raw_gb"]
for c, (v, t) in zip((c1, c2, c3), [(inti.nf(k["total"]), "laporan kejahatan bersih"), (inti.nf(gb, 2) + " GB", "data mentah di HDFS (3 dataset)"), (inti.nf(k["arrest_rate"] * 100, 1) + "%", "berujung penangkapan")]):
    c.markdown(f'<div class="big">{v}</div><div class="muted">{t}</div>', unsafe_allow_html=True)

st.subheader("Temuan utama")
t1, t2, t3 = st.columns(3)
t1.info(f"**Kejahatan menumpuk di beberapa titik.** District {int(top['district'])} paling banyak laporan ({inti.nf(top['count'])}).")
t2.info(f"**Peluang tertangkap sangat beda antar jenis.** Rata-rata hanya {inti.nf(k['arrest_rate'] * 100, 1)}%.")
t3.info(f"**Besok bisa diprakirakan.** Galat model {inti.nf(m.min(), 2)} vs {inti.nf(m.get('baseline_mean7', m.min()), 2)} untuk tebakan rata-rata 7 hari.")

st.subheader("Alur big data")
for i, (n, t, ds) in enumerate(LANGKAH, 1):
    st.markdown(f"**{i}. {n}** ({t})  \n<span class='muted'>{ds}</span>", unsafe_allow_html=True)
st.caption("Langkah 1 sampai 3 adalah Modul 1 (import dan preprocessing); langkah 4 sampai 7 adalah Modul 2 (analisis BI dan ML).")
