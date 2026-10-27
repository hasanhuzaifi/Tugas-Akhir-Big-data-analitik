import streamlit as st
from _umum import inti

st.title("Kode di balik pipeline")
st.write("Semua kode Spark, MapReduce, dan skrip ada di repo (`src/`, `src/mr/`). Pilih berkas untuk melihat isi dan penjelasannya.")
daftar = inti.daftar_kode()
if not daftar:
    st.warning("Berkas src/ tidak ditemukan.")
    st.stop()
pil = st.selectbox("Berkas", [p for p, _ in daftar])
pen = dict(daftar)[pil]
if pen:
    st.markdown(pen)
else:
    st.caption("Belum ada penjelasan untuk berkas ini di peta-kode-spark.md.")
f = inti.ROOT / pil
st.code(f.read_text(encoding="utf-8", errors="replace"), language="bash" if f.suffix == ".sh" else "python", line_numbers=True)
