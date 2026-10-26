"""UI: Peringatan (publik), Modul 1 (NiFi + preprocessing), Modul 2 (BI + ML). Baca hasil tersimpan di data/."""
import json, os
import pandas as pd
import plotly.express as px
import streamlit as st

D = os.path.join(os.path.dirname(__file__), "..", "data")
st.set_page_config(page_title="Chicago Crime Safety", layout="wide")


@st.cache_data
def jload(p):
    return json.load(open(os.path.join(D, p)))


@st.cache_data
def pload(p):
    return pd.read_parquet(os.path.join(D, p)) if p.endswith(".parquet") else pd.read_csv(os.path.join(D, p))


DAY = {1: "Min", 2: "Sen", 3: "Sel", 4: "Rab", 5: "Kam", 6: "Jum", 7: "Sab"}
page = st.sidebar.radio("Halaman", ["Peringatan", "Modul 1: Data", "Modul 2: Analisis"])

if page == "Peringatan":
    st.title("Peringatan Kejahatan Chicago")
    nd = pload("ml/next_day.csv")
    st.caption(f"Perkiraan untuk {nd['day'].iloc[0]} per district polisi (agregat, bukan individu).")
    color = {"Rendah": "#2e7d32", "Sedang": "#f9a825", "Tinggi": "#c62828"}
    nd["district"] = nd["district"].astype(str)
    fig = px.bar(nd, x="district", y="pred", color="risk", color_discrete_map=color,
                 labels={"pred": "Prakiraan kejadian", "district": "District", "risk": "Risiko"})
    st.plotly_chart(fig, use_container_width=True)
    hi = nd[nd["risk"] == "Tinggi"]["district"].tolist()
    st.warning(f"District risiko Tinggi pada {nd['day'].iloc[0]}: " + (", ".join(hi) if hi else "tidak ada") + ". Tetap waspada, utamakan jalan ramai dan terang.")
    st.caption("Data sumber Chicago tertinggal beberapa hari dari hari ini, jadi tanggal prakiraan mengikuti data terakhir yang tersedia.")
    heat = pload("bi/heatmap.parquet")
    h = heat.sort_values("count", ascending=False).head(5)
    st.subheader("Jam dan hari paling rawan")
    st.write(", ".join(f"{DAY[r.day_of_week]} {int(r.hour):02d}:00" for r in h.itertuples()))
    top = pload("bi/top_types.parquet")
    st.subheader("Jenis kejahatan dominan")
    st.write(", ".join(top["primary_type"].head(5)))
    st.info("Tips: simpan barang berharga, jangan tinggalkan kendaraan terbuka, hindari jalan sepi saat malam.")
    st.caption("Disclaimer: prakiraan statistik dari data historis, bukan kepastian. Bukan pengganti informasi resmi kepolisian.")

elif page == "Modul 1: Data":
    st.title("Modul 1: Impor (NiFi) dan Preprocessing")
    st.markdown("**Alur:** Socrata API -> NiFi (`GenerateFlowFile` -> `SplitText` -> `ExtractText` -> `InvokeHTTP` -> `UpdateAttribute` -> `PutHDFS`) -> HDFS `/data/raw/*` -> Spark -> Parquet `/data/processed/*`")
    s = jload("m1_summary.json")
    st.dataframe(pd.DataFrame(s).T)
    if os.path.exists(os.path.join(D, "hdfs_size.json")):
        st.json(jload("hdfs_size.json"))

else:
    st.title("Modul 2: Analisis (BI) dan Prediksi (ML)")
    k = jload("bi/kpi.json")
    c = st.columns(3)
    c[0].metric("Total kejadian", f"{k['total']:,}")
    c[1].metric("Rasio penangkapan", f"{k['arrest_rate']:.1%}")
    c[2].metric("Domestik", f"{k['domestic_pct']:.1%}")
    st.plotly_chart(px.line(pload("bi/weekly.parquet"), x="minggu", y="count", title="Tren mingguan"), use_container_width=True)
    heat = pload("bi/heatmap.parquet")
    heat["hari"] = heat["day_of_week"].map(DAY)
    st.plotly_chart(px.density_heatmap(heat, x="hour", y="hari", z="count", histfunc="sum", title="Jam x hari"), use_container_width=True)
    st.plotly_chart(px.bar(pload("bi/top_types.parquet"), x="count", y="primary_type", orientation="h", title="10 jenis teratas"), use_container_width=True)
    st.subheader("MapReduce (Hadoop Streaming, YARN)")
    mr = pd.read_csv(os.path.join(D, "mr/crime_dhh.tsv"), sep="	", header=None, names=["k", "n"])
    mr[["district", "day_of_week", "hour"]] = mr["k"].str.split("|", expand=True).astype(int)
    st.caption(f"Hitungan district x hari x jam dari CSV mentah: {int(mr['n'].sum()):,} kejadian, {len(mr)} sel. Cocok dengan PySpark.")
    st.plotly_chart(px.bar(mr.groupby("district", as_index=False)["n"].sum(), x="district", y="n", title="Kejadian per district (MapReduce)"), use_container_width=True)
    st.subheader("Faktor masa lalu: keluhan 311 dan kecelakaan")
    ec = pd.DataFrame(jload("bi/ext_corr.json"))
    st.plotly_chart(px.bar(ec, x="factor", y="corr", color=ec["lag"].astype(str), barmode="group",
                           labels={"corr": "Korelasi dengan kejahatan", "color": "Lag (hari)"}), use_container_width=True)
    st.subheader("Model prediksi (uji = 12 bulan terakhir)")
    m = jload("ml/metrics.json")
    rows = {k2: v for k2, v in m.items() if isinstance(v, dict) and "mae" in v}
    st.dataframe(pd.DataFrame(rows).T)
    st.caption(f"Model terbaik: {m['best_model']}. Penambahan fitur 311+kecelakaan mengubah RMSE sebesar {m['ext_gain_rmse_pct']}% (GBT).")
    imp = pd.Series(m["importance_gbt_full"]).sort_values().tail(12)
    st.plotly_chart(px.bar(imp, orientation="h", labels={"value": "Importance", "index": "Fitur"}), use_container_width=True)
