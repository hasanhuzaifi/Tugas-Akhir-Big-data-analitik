import sys
from pathlib import Path
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import inti  # noqa: E402,F401


@st.cache_data
def data():
    return inti.muat()


def wajib_data():
    """Hentikan halaman bila hasil pipeline belum ada."""
    if not inti.siap():
        st.warning("Hasil pipeline belum ada di web_export/. Jalankan Modul 1 lalu Analisis dan ML.")
        st.stop()
    return data()


def kesimpulan(butir):
    st.markdown('<div class="kes"><h4>Kesimpulan</h4><ul>' + "".join(f"<li>{b}</li>" for b in butir) + "</ul></div>", unsafe_allow_html=True)
