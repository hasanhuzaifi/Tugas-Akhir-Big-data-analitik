"""Chicago Crime Safety Insight: Beranda, Modul 1 (NiFi + preprocessing), Modul 2 (BI + ML), Kode.
Jalan: .venv/bin/streamlit run app/streamlit_app.py --server.port 8501 (ADR 0017)."""
import streamlit as st

st.set_page_config(page_title="Chicago Crime Safety Insight", page_icon=":material/shield:", layout="wide")
st.markdown("""<style>
.block-container{padding-top:2rem;max-width:1280px}
.kes{border-left:4px solid #C4262E;background:rgba(196,38,46,.07);padding:10px 16px;border-radius:2px;margin:8px 0 16px}
.kes h4{margin:0 0 4px}.kes ul{margin:0;padding-left:18px}
.big{font-size:2rem;font-weight:700;line-height:1.1}.muted{opacity:.7;font-size:.9rem}
.stepper{display:flex;gap:4px;flex-wrap:wrap;margin:8px 0}
.stepper span{padding:4px 10px;border:1px solid #9aa5b1;border-radius:3px;font-size:.85rem}
.stepper .ok{background:#2e9e6b;color:#fff;border-color:#2e9e6b}.stepper .jalan{background:#1478B5;color:#fff;border-color:#1478B5}
.rk{border-radius:3px;padding:6px 10px;color:#fff;margin-bottom:2px}.rk-Tinggi{background:#C4262E}.rk-Sedang{background:#c98a14}.rk-Rendah{background:#2e9e6b}
.meter{display:flex;height:16px;position:relative;border-radius:3px;overflow:visible}
.meter i{display:block;height:100%}.meter u{position:absolute;top:-4px;width:4px;height:24px;background:#16202B;text-decoration:none}
</style>""", unsafe_allow_html=True)

hal = st.navigation([
    st.Page("halaman/beranda.py", title="Beranda", icon=":material/home:", default=True),
    st.Page("halaman/modul1.py", title="Modul 1: Data", icon=":material/cloud_download:"),
    st.Page("halaman/modul2.py", title="Modul 2: Analisis", icon=":material/map:"),
    st.Page("halaman/kode.py", title="Kode", icon=":material/code:"),
])
hal.run()
