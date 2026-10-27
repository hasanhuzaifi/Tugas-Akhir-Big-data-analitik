import random

import pandas as pd
import plotly.graph_objects as go
import pydeck as pdk
import streamlit as st
from _umum import inti, kesimpulan, wajib_data

nf, nm = inti.nf, inti.nama_jenis
d = wajib_data()
J = inti.daftar_jenis(d)
COR = inti.warna_jenis(d)
PROF = d["profil"].set_index("jenis")
META = d["meta"]
QP = st.query_params
RANGE = [[255, 243, 176], [253, 190, 75], [242, 107, 56], [196, 38, 46], [110, 15, 26]]


def hexrgb(h):
    return [int(h[i:i + 2], 16) for i in (1, 3, 5)]


def kotak(df, warna, half=META["cell_deg"] / 2):
    """Sel grid -> poligon persegi untuk PolygonLayer."""
    df = df.copy()
    df["poly"] = [[[lo - half, la - half], [lo + half, la - half], [lo + half, la + half], [lo - half, la + half]] for la, lo in zip(df["la"], df["lo"])]
    df["color"] = [hexrgb(warna(r)) + [200] for r in df.itertuples()]
    return df


def peta(layers, la=41.84, lo=-87.68, zoom=9.6):
    st.pydeck_chart(pdk.Deck(layers=layers, initial_view_state=pdk.ViewState(latitude=la, longitude=lo, zoom=zoom),
                             map_style="light", tooltip={"text": "{tip}"}), height=520)


def pilih_param(kunci, default):
    v = QP.get(kunci, default)
    return v if v in J else default


t1, t2, t3 = st.tabs(["1. Di mana: peta panas lokasi", "2. Apa dan kapan: bandingkan jenis", "3. Besok: prakiraan ML"])

# ======================= 1. DI MANA =======================
with t1:
    st.header("Di mana kejahatan terjadi")
    opsA = ["SEMUA"] + J
    a0 = QP.get("jenis", "SEMUA")
    a0 = a0 if a0 in opsA else "THEFT"
    c = st.columns([2, 2, 2, 2, 1])
    A = c[0].selectbox("Jenis kejahatan", opsA, index=opsA.index(a0), format_func=nm, key="A")
    opsB = [""] + J
    b0 = pilih_param("banding", "")
    B = c[1].selectbox("Bandingkan dengan", opsB, index=opsB.index(b0), format_func=lambda x: "(tidak ada)" if not x else nm(x), key="B")
    mode_ops = ["Kepadatan", "Selisih A lawan B"]
    mode = c[2].radio("Mode peta", mode_ops, index=1 if QP.get("mode") == "selisih" and B else 0, horizontal=True, key="mode", disabled=not B)
    gaya = c[3].radio("Gaya peta", ["Halus", "Kotak"], horizontal=True, key="gaya")
    if c[4].button("Reset", key="reset1"):
        QP.clear()
        for k in ("A", "B", "mode", "gaya", "rad", "amb", "fokus"):
            st.session_state.pop(k, None)
        st.rerun()
    c = st.columns(2)
    rad = c[0].slider("Jari-jari sebaran", 8, 40, 18, key="rad", disabled=gaya != "Halus")
    amb = c[1].slider("Ambang tampil (% dari p98)", 0, 60, 0, key="amb")
    QP["jenis"] = "" if A == "SEMUA" else A
    QP["banding"] = B
    QP["mode"] = "selisih" if (B and mode.startswith("Selisih")) else ""
    for k in [k for k in ("jenis", "banding", "mode") if not QP.get(k)]:
        del QP[k]

    @st.cache_data
    def grid_jenis(j):
        g = d["grid"]
        return g.groupby(["la", "lo"], as_index=False)["n"].sum() if j == "SEMUA" else g[g["jenis"] == j][["la", "lo", "n"]].reset_index(drop=True)

    ga = grid_jenis(A)
    selisih = bool(B) and mode.startswith("Selisih")
    fokus = st.session_state.get("fokus")
    view = dict(la=fokus[0], lo=fokus[1], zoom=15) if fokus else {}
    with st.expander("Cara membaca peta ini"):
        st.write(f"Chicago dibagi menjadi sel sekitar 0,5 km. Makin merah dan gelap, makin banyak laporan di sel itu. Geser dan zoom dengan mouse atau jari; ikon di pojok peta memperbesar ke layar penuh. **Halus** menggabungkan sel menjadi gradasi mulus, **Kotak** menampilkan tiap sel apa adanya (arahkan kursor untuk angkanya). Pilih jenis kedua lalu **Selisih** untuk melihat di mana dua jenis berbeda pola. {nf(META['rows_mapped'])} dari {nf(META['rows'])} kejadian punya koordinat; {nf(META['rows_no_coord'])} tanpa koordinat tidak dipetakan.")

    if selisih:
        gb = grid_jenis(B)
        L = inti.selisih_sel(ga, gb)
        L["tip"] = [f"{nm(A)}: {nf(r.na)} | {nm(B)}: {nf(r.nb)}" for r in L.itertuples()]
        L = kotak(L, lambda r: inti.warna_selisih(r.s))
        top_a, top_b = L.sort_values("s").iloc[-1], L.sort_values("s").iloc[0]
        kesimpulan([f"<b>{nm(A)}</b> dan <b>{nm(B)}</b> tidak menumpuk di tempat yang sama. Merah = {nm(A)} lebih dominan, biru = {nm(B)} lebih dominan.",
                    f"Selisih terbesar: {nm(A)} unggul di sekitar {top_a['la']:.3f}, {top_a['lo']:.3f}; {nm(B)} unggul di sekitar {top_b['la']:.3f}, {top_b['lo']:.3f}."])
        pol = pdk.Layer("PolygonLayer", L, get_polygon="poly", get_fill_color="color", pickable=True, stroked=False)
        peta([pol], **view)
        st.caption(f":blue[{nm(B)} lebih padat] ◀ gradasi biru-abu-merah ▶ :red[{nm(A)} lebih padat]")
    else:
        p = inti.p98(list(ga["n"]))
        aa = ga[ga["n"] >= amb / 100 * p].copy()
        tot = ga["n"].sum()
        t = ga.sort_values("n", ascending=False)
        kesimpulan([f"<b>{nm(A)}</b>: {nf(tot)} laporan di {nf(len(ga))} sel peta.",
                    f"Terkonsentrasi: <b>10% sel teratas menampung {nf(inti.konsentrasi10(ga))}%</b> dari seluruh laporan. Sisanya tersebar tipis.",
                    f"Titik terpanas ada di sekitar {t.iloc[0]['la']:.3f}, {t.iloc[0]['lo']:.3f} ({nf(t.iloc[0]['n'])} laporan dalam satu sel). Pilih di daftar \"Titik terpanas\" di bawah untuk melihatnya."])
        if gaya == "Halus":
            aa["w"] = aa["n"].map(lambda n: inti.intensitas(n, p))
            lay = pdk.Layer("HeatmapLayer", aa, get_position="[lo, la]", get_weight="w", radius_pixels=rad, color_range=RANGE)
        else:
            aa["tip"] = aa["n"].map(lambda n: f"{nf(n)} laporan")
            aa = kotak(aa, lambda r: inti.warna_panas((r.n / p) ** 0.5))
            lay = pdk.Layer("PolygonLayer", aa, get_polygon="poly", get_fill_color="color", pickable=True, stroked=False)
        peta([lay], **view)
        st.caption(f"sedikit ▶ banyak: gradasi kuning-merah tua; {nf(p)}+ per sel")

    c1, c2 = st.columns(2)
    with c1:
        js = [x for x in (A, B) if x and x != "SEMUA"]
        st.subheader(nm(A) + (f" lawan {nm(B)}" if B else ""))
        kv = st.columns(max(1, len(js) + (A == "SEMUA")))
        i = 0
        if A == "SEMUA":
            kv[0].metric("Semua jenis, laporan", nf(d["kpi"]["total"]))
            i = 1
        for x in js:
            kv[i].metric(f"{nm(x)}, laporan", nf(PROF.loc[x, "n"]))
            i += 1
        if js:
            for x in js:
                p_ = PROF.loc[x]
                st.markdown(f"**{nm(x)}**: terbanyak di district {int(p_['top_district'])} ({nf(p_['top_share'] * 100, 1)}% dari semuanya), {nf(p_['arrest_rate'] * 100, 1)}% berujung penangkapan, {nf(p_['domestic_pct'] * 100, 1)}% kasus domestik.")
        else:
            st.caption("Pilih satu jenis untuk melihat profilnya.")
        st.subheader("Titik terpanas")
        if not selisih:
            pk = inti.titik_terpanas(ga)
            st.caption("Pilih untuk terbang ke lokasinya.")
            for n_, q in enumerate(pk, 1):
                if st.button(f"{n_}. {nf(q['n'])} laporan, {nf(q['n'] / tot * 100, 1)}% dari semua sel, {q['la']:.3f}, {q['lo']:.3f}", key=f"hot{n_}", use_container_width=True):
                    st.session_state["fokus"] = (q["la"], q["lo"])
                    st.rerun()
        else:
            st.caption("Daftar titik terpanas tampil pada mode Kepadatan.")
    with c2:
        st.subheader("District teratas")
        cols = js or ["SEMUA"]
        td = d["tdist"]
        td = td[td["jenis"].isin(js)] if js else td
        pv = td.pivot_table(index="district", columns="jenis", values="n", aggfunc="sum", fill_value=0)
        if not js:
            pv = pv.sum(axis=1).to_frame("SEMUA")
        pv = pv[cols].sort_values(cols[0], ascending=False).head(8)
        pv.columns = [nm(x) for x in pv.columns]
        pv.index.name = "District"
        st.dataframe(pv.map(lambda v: nf(v)), use_container_width=True)

# ======================= 2. APA DAN KAPAN =======================
with t2:
    st.header("Apa dan kapan: bandingkan jenis")
    PRE = {"Pencurian dan kekerasan": ["THEFT", "BATTERY", "ROBBERY"], "Narkotika, perusakan, penipuan": ["NARCOTICS", "CRIMINAL DAMAGE", "DECEPTIVE PRACTICE"], "Properti dan kendaraan": ["BURGLARY", "MOTOR VEHICLE THEFT", "THEFT"]}
    awal = [x for x in QP.get("j", "THEFT,BATTERY,ROBBERY").split(",") if x in J][:4] or ["THEFT"]
    if "pil" not in st.session_state:
        st.session_state["pil"] = awal
    st.caption("Pilihan cepat:")
    cc = st.columns(len(PRE))
    for col, (lbl, v) in zip(cc, PRE.items()):
        if col.button(lbl, key="pre_" + lbl, use_container_width=True):
            st.session_state["pil"] = v
            st.rerun()
    sel = st.multiselect("Jenis (maks. 4)", J, key="pil", max_selections=4, format_func=nm)
    if not sel:
        st.info("Pilih minimal satu jenis.")
    else:
        QP["j"] = ",".join(sel)
        with st.expander("Cara membaca halaman ini"):
            st.write("Pilih 1 sampai 4 jenis kejahatan, atau pakai pilihan cepat. **Tren** diindeks 100 pada bulan penuh pertama supaya jenis besar dan kecil bisa dibandingkan: garis di atas 100 berarti lebih banyak dari awal. **Peta jam** menunjukkan kapan jenis itu paling sering dilaporkan (baris = hari, kolom = jam). **Korelasi** mengukur apakah dua jenis naik turun bersamaan di hari yang sama (1 = selalu bersamaan); korelasi bukan sebab-akibat.")
        P = d["profil"].set_index("jenis").loc[sel]
        kes, puncak = [], []
        Gm = {}
        for j in sel:
            g = inti.grid_jam(d["jam"], j)
            Gm[j] = g
            pd_, ph, sore = inti.puncak_jam(g)
            bl, v = inti.indeks_tren(d["bulan"], j)
            t_ = v[-1]
            puncak.append(f"**{nm(j)}** paling sering {inti.HARI_PENUH[pd_]} pukul {ph}.00 (lonjakan 00.00 diabaikan: itu waktu bawaan data).")
            kes.append(f"<b>{nm(j)}</b>: puncak {inti.HARI_PENUH[pd_]} pukul {ph}.00; {nf(sore * 100)}% laporan terjadi jam 16-21; penangkapan {nf(P.loc[j, 'arrest_rate'] * 100, 1)}%; tren {inti.arah_tren(t_)} (indeks {nf(t_)} dibanding awal).")
        if len(sel) > 1:
            ar = P.sort_values("arrest_rate", ascending=False)
            kes.append(f"Penangkapan tertinggi: <b>{nm(ar.index[0])}</b> ({nf(ar.iloc[0]['arrest_rate'] * 100, 1)}%), terendah <b>{nm(ar.index[-1])}</b> ({nf(ar.iloc[-1]['arrest_rate'] * 100, 1)}%).")
        kesimpulan(kes)
        fig = go.Figure()
        for j in sel:
            bl, v = inti.indeks_tren(d["bulan"], j)
            fig.add_scatter(x=bl, y=v, name=nm(j), mode="lines", line=dict(color=COR[j], width=2.5, shape="spline"))
        fig.update_layout(title="Tren bulanan (indeks 100)", yaxis_title="indeks (bulan pertama = 100)", legend=dict(orientation="h", y=-0.2), margin=dict(l=10, r=10, t=40, b=10), height=360)
        st.plotly_chart(fig, use_container_width=True)
        st.subheader("Profil")
        tp = pd.DataFrame({"Jenis": [nm(j) for j in sel], "Laporan": [nf(P.loc[j, "n"]) for j in sel],
                           "Penangkapan": [nf(P.loc[j, "arrest_rate"] * 100, 1) + "%" for j in sel], "Domestik": [nf(P.loc[j, "domestic_pct"] * 100, 1) + "%" for j in sel],
                           "District teratas": [f"{int(P.loc[j, 'top_district'])} ({nf(P.loc[j, 'top_share'] * 100, 1)}%)" for j in sel]})
        st.dataframe(tp, hide_index=True, use_container_width=True)
        for x in puncak:
            st.markdown(x)
        cols = st.columns(2)
        for n_, j in enumerate(sel):
            g = Gm[j]
            z = [[g[a][b] if b else None for b in range(24)] for a in range(1, 8)]
            mj = max(v for r in z for v in r if v) or 1
            hm = go.Figure(go.Heatmap(z=z, x=list(range(24)), y=inti.HARI_PENUH[1:], colorscale=[[i / 4, c_] for i, c_ in enumerate(inti.STOPS)], zmin=0, zmax=mj, showscale=False,
                                      hovertemplate="%{y} %{x}.00: %{z:,}<extra></extra>"))
            hm.update_layout(title=dict(text=f"{nm(j)}: jam dan hari", font=dict(color=COR[j])), yaxis=dict(autorange="reversed"), xaxis=dict(dtick=3), margin=dict(l=10, r=10, t=40, b=10), height=300)
            cols[n_ % 2].plotly_chart(hm, use_container_width=True)
        st.subheader("Korelasi harian antarjenis")
        st.caption("1 = naik turun bersamaan. Dihitung dari jumlah harian di seluruh kota.")
        kr = d["korelasi"].pivot(index="a", columns="b", values="corr").loc[sel, sel]
        cz = go.Figure(go.Heatmap(z=kr.values, x=[nm(x) for x in sel], y=[nm(x) for x in sel], zmin=0, zmax=1, colorscale=[[i / 4, c_] for i, c_ in enumerate(inti.STOPS)],
                                  text=[[nf(v, 2) for v in r] for r in kr.values], texttemplate="%{text}", showscale=False))
        cz.update_layout(yaxis=dict(autorange="reversed"), margin=dict(l=10, r=10, t=10, b=10), height=120 + 60 * len(sel))
        st.plotly_chart(cz, use_container_width=True)

# ======================= 3. BESOK =======================
with t3:
    mm, nd, kpi = d["model_metrics"], d["next_day"], d["kpi"]
    best = mm.iloc[0]
    base = mm[mm["model"] == "baseline_mean7"].iloc[0]
    gain = (base["rmse"] - best["rmse"]) / base["rmse"] * 100
    risk = inti.kartu_risiko(nd)
    tinggi = int((risk["risk"] == "Tinggi").sum())
    lag = d["lag"].sort_values("lg")
    met = d["metrics"]
    st.header("Besok: prakiraan per district")
    kesimpulan([f"Model <b>RandomForest</b> memprakirakan jumlah kejadian per district per hari dengan kesalahan rata-rata sekitar <b>{nf(best['mae'], 1)} kejadian</b>, lebih baik <b>{nf(gain, 1)}%</b> dari tebakan \"sama dengan rata-rata 7 hari\".",
                "Yang paling menentukan adalah <b>kebiasaan district itu sendiri</b>: rata-rata 30 hari terakhir. Data 311 dan kecelakaan <b>tidak</b> membantu, jadi model sederhana justru terbaik.",
                "Prakiraan besok dikelompokkan Rendah, Sedang, Tinggi dengan membandingkannya ke sejarah district itu sendiri, bukan ke district lain."])
    with st.expander("Cara membaca halaman ini"):
        st.write(f"Model dilatih dengan {nf(kpi['train_rows'] if 'train_rows' in kpi else met['train_rows'])} baris dan diuji pada {nf(met['test_rows'])} baris (12 bulan terakhir, dipisah menurut waktu supaya tidak \"mengintip\" masa depan). **Pilih kartu district** untuk detailnya: posisi prakiraan terhadap kisaran normal, riwayat prakiraan lawan kenyataan, dan jam rawan. **Tebak dulu** mengajak Anda menebak lalu membandingkan dengan model. Prakiraan bukan kepastian.")
    c = st.columns(3)
    c[0].metric("Kemarin menentukan hari ini", nf(lag.iloc[0]["corr"], 2), help=f"Korelasi dengan 1 hari sebelumnya; 7 hari {nf(lag.iloc[6]['corr'], 2)}. Rata-rata 30 hari terakhir adalah fitur terpenting.")
    c[1].metric("Lebih akurat dari tebakan rata-rata", nf(gain, 1) + "%", help=f"RMSE {nf(best['rmse'], 2)} lawan {nf(base['rmse'], 2)}. Menambah data 311 dan kecelakaan tidak membantu.")
    r0 = risk.iloc[0]
    c[2].metric(f"District {int(r0['district'])}: tertinggi {r0['day']}", f"{nf(r0['pred'], 1)} ({r0['risk']})", help=f"{tinggi} district Tinggi. Kategori dibandingkan persentil 33 dan 66 sejarah district itu sendiri.")

    st.subheader("Kartu risiko")
    c = st.columns([3, 2])
    f = c[0].radio("Saring risiko", ["Semua", "Tinggi", "Sedang", "Rendah"], horizontal=True, key="fr")
    u = c[1].selectbox("Urutkan", ["Prakiraan tertinggi", "Nomor district"], key="urut")
    kt = risk if f == "Semua" else risk[risk["risk"] == f]
    kt = kt.sort_values("pred", ascending=False) if u.startswith("Prakiraan") else kt.sort_values("district")
    if "dsel" not in st.session_state or st.session_state["dsel"] not in set(risk["district"]):
        st.session_state["dsel"] = int(r0["district"])
    for baris in range(0, len(kt), 6):
        cols = st.columns(6)
        for col, r in zip(cols, kt.iloc[baris:baris + 6].itertuples()):
            col.markdown(f'<div class="rk rk-{r.risk}"><small>District {r.district}</small><div class="big" style="font-size:1.5rem">{nf(r.pred, 1)}</div><b>{r.risk}</b></div>', unsafe_allow_html=True)
            if col.button("Detail", key=f"k{r.district}", use_container_width=True):
                st.session_state["dsel"] = int(r.district)
    st.caption("Prakiraan berbasis pola agregat historis, bukan kepastian.")

    dd = st.session_state["dsel"]
    n = nd[nd["district"] == dd].iloc[0]
    seri = d["test_pred"][d["test_pred"]["district"] == dd].sort_values("day").reset_index(drop=True)
    with st.container(border=True):
        st.subheader(f"District {dd}: prakiraan {nf(n['pred'], 1)} kejadian pada {n['day']}")
        c1, c2 = st.columns(2)
        with c1:
            a_, b_, p_ = inti.meter(n["pred"], n["p33"], n["p66"])
            st.markdown(f'<div style="display:flex;justify-content:space-between" class="muted"><span>Rendah</span><span>Sedang</span><span>Tinggi</span></div>'
                        f'<div class="meter"><i style="width:{a_}%;background:#2e9e6b"></i><i style="width:{b_ - a_}%;background:#c98a14"></i><i style="flex:1;background:#C4262E"></i><u style="left:calc({p_}% - 2px)"></u></div>', unsafe_allow_html=True)
            tot_ = d["district"].set_index("district").loc[dd]
            st.markdown(f"Kisaran normal district ini: **{n['p33']:g}** sampai **{n['p66']:g}** kejadian per hari. Prakiraan **{nf(n['pred'], 1)}** berarti **{n['risk']}**. Sepanjang periode: {nf(tot_['count'])} laporan, penangkapan {nf(tot_['arrest_rate'] * 100, 1)}%.")
            jm = d["mr_dhh"][(d["mr_dhh"]["district"] == dd) & (d["mr_dhh"]["hr"] > 0)].groupby("hr")["n"].sum().reindex(range(1, 24), fill_value=0)
            fj = go.Figure(go.Bar(x=list(jm.index), y=list(jm.values), marker_color=["#C4262E" if v == jm.max() else "#9fb3c4" for v in jm.values]))
            fj.update_layout(title="Jam rawan (semua hari)", xaxis_title="jam", margin=dict(l=10, r=10, t=40, b=10), height=240)
            st.plotly_chart(fj, use_container_width=True)
        with c2:
            sr = seri.tail(30)
            fs = go.Figure()
            fs.add_scatter(x=sr["day"].str[5:], y=sr["n"], name="Kenyataan", line=dict(color="#16202B", width=2), mode="lines+markers")
            fs.add_scatter(x=sr["day"].str[5:], y=sr["prediction"], name="Prakiraan model", line=dict(color="#C4262E", width=2, dash="dash"), mode="lines")
            fs.update_layout(title="Prakiraan lawan kenyataan (30 hari terakhir uji)", legend=dict(orientation="h", y=-0.2), margin=dict(l=10, r=10, t=40, b=10), height=330)
            st.plotly_chart(fs, use_container_width=True)

    st.subheader("Tebak dulu: Anda lawan model")
    st.caption("Pilih district. Anda lihat 7 hari sebelumnya pada hari acak dari periode uji, tebak jumlah kejadian hari itu, lalu bandingkan dengan model dan rata-rata 7 hari.")
    c = st.columns([2, 1])
    gd = c[0].selectbox("District", sorted(risk["district"].astype(int)), key="gd", format_func=lambda x: f"District {x}")
    if c[1].button("Soal baru", type="primary", key="gmulai"):
        s_ = d["test_pred"][d["test_pred"]["district"] == gd].sort_values("day").reset_index(drop=True)
        st.session_state["soal"] = inti.soal_tebak(s_, random.random())
    sl = st.session_state.get("soal")
    if sl:
        st.write("7 hari sebelumnya: " + " | ".join(f"{t[5:]}: **{v}**" for t, v in sl["riwayat"]))
        with st.form("tebak"):
            g_ = st.number_input(f"Tebakan Anda (kejadian pada {sl['t']})", 0, 200, 0)
            if st.form_submit_button("Cek"):
                e, win = inti.nilai_tebakan(g_, sl)
                st.markdown(f"Kenyataan: **{sl['a']}** kejadian. Tebakan Anda {g_} (selisih {nf(e['Anda'], 1)}), model {nf(sl['m'], 1)} (selisih {nf(e['Model'], 1)}), rata-rata 7 hari {nf(sl['b'], 1)} (selisih {nf(e['Rata-rata 7 hari'], 1)}). "
                            + (":green[**Anda terdekat!**]" if win == "Anda" else f":red[**Terdekat: {win}.**]"))

    LAB = {"baseline_mean7": "Rata-rata 7 hari (pembanding)", "rf_base": "RandomForest, kejahatan saja", "rf_full": "RandomForest + 311 + kecelakaan", "gbt_base": "GBT, kejahatan saja", "gbt_full": "GBT + 311 + kecelakaan"}
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Perbandingan model")
        t_ = mm.assign(Model=mm["model"].map(lambda x: LAB.get(x, x)), MAE=mm["mae"].map(lambda v: nf(v, 2)), RMSE=mm["rmse"].map(lambda v: nf(v, 2)), R2=mm["r2"].map(lambda v: nf(v, 3)))[["Model", "MAE", "RMSE", "R2"]]
        st.dataframe(t_, hide_index=True, use_container_width=True)
    with c2:
        im = d["importance"].head(8).iloc[::-1]
        fi = go.Figure(go.Bar(x=im["nilai"], y=im["fitur"], orientation="h", marker_color="#C4262E"))
        fi.update_layout(title="Fitur terpenting (GBT)", margin=dict(l=10, r=10, t=40, b=10), height=300)
        st.plotly_chart(fi, use_container_width=True)
    pr = d["test_pred"].groupby("day", as_index=False)[["n", "prediction"]].sum()
    fp = go.Figure()
    fp.add_scatter(x=pr["day"], y=pr["n"], name="Aktual", line=dict(color="#7A8794", width=1.5))
    fp.add_scatter(x=pr["day"], y=pr["prediction"], name="Prediksi", line=dict(color="#C4262E", width=2))
    fp.update_layout(title="Aktual lawan prediksi, 12 bulan uji", legend=dict(orientation="h", y=-0.2), margin=dict(l=10, r=10, t=40, b=10), height=320)
    st.plotly_chart(fp, use_container_width=True)
    c1, c2 = st.columns(2)
    fl = go.Figure(go.Bar(x=lag["lg"], y=lag["corr"], marker_color="#C4262E"))
    fl.update_layout(title="Pengaruh hari lampau", xaxis_title="hari sebelumnya", yaxis=dict(range=[0, 0.8]), margin=dict(l=10, r=10, t=40, b=10), height=300)
    c1.plotly_chart(fl, use_container_width=True)
    ex = d["ext"][d["ext"]["lg"].isin([7, 30])]
    fe = go.Figure()
    for lg_, col_ in ((7, "#00A1DE"), (30, "#16202B")):
        e_ = ex[ex["lg"] == lg_]
        fe.add_bar(x=e_["factor"], y=e_["corr"], name=f"lag {lg_}", marker_color=col_)
    fe.update_layout(title="Data pendukung: 311 dan kecelakaan", barmode="group", margin=dict(l=10, r=10, t=40, b=10), height=300, legend=dict(orientation="h", y=-0.2))
    c2.plotly_chart(fe, use_container_width=True)
    c2.caption("Dua dataset ini diuji sebagai petunjuk tambahan (keluhan warga dan kecelakaan per district per hari). Hasilnya lemah (di bawah 0,35) dan tidak memperbaiki prakiraan, jadi dicatat sebagai temuan, bukan dipakai.")
    mrT, spT = int(d["mr_dhh"]["n"].sum()), int(kpi["total"])
    st.subheader("MapReduce (YARN) dan PySpark")
    c = st.columns(3)
    c[0].metric("Total MapReduce (37 map, 2 reduce)", nf(mrT))
    c[1].metric("Total PySpark", nf(spT))
    c[2].metric("Selisih = hari parsial yang dibuang Spark", nf(mrT - spT))

    st.subheader("Jalankan ulang")
    from _job import panel_job
    panel_job([("bi", "BI"), ("mapreduce", "MapReduce"), ("analisis", "Analisis lokasi"), ("ml", "Latih ML"), ("export", "Ekspor")], kunci="m2")
