"""Logika bersama aplikasi Streamlit: data, validasi link, job, unduhan hasil, rumus peta/ML.
Tanpa import streamlit supaya bisa diuji."""
import hashlib, json, math, os, re, subprocess, time, urllib.parse, urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web_export"
JOBDIR = ROOT / "data" / "jobs"
PETA_KODE = Path("/mnt/d/Kuliah/Big Data & Analitik/Vault Tugas Akhir/01-Projects/Tugas-Akhir/references/peta-kode-spark.md")
NIFI_INGEST = "http://localhost:8081/ingest"
HADOOP = "/usr/local/hadoop/bin/hdfs"

DATASET = {"ijzp-q8t2": "crime", "85ca-t3if": "crashes", "v6vf-nfxy": "311"}
KOLOM = {"crime": "date", "crashes": "crash_date", "311": "created_date"}
NAMA_DS = {"crime": "Kejahatan", "crashes": "Kecelakaan", "311": "Layanan 311"}
MB_HARI = {"crime": 0.195, "crashes": 0.183, "311": 1.1}
PAKET = [("2023-10-25", "2024-10-25"), ("2024-10-25", "2025-10-25"), ("2025-10-25", "2026-10-16")]
HARI_PAKET = 1087
HARI = ["Min", "Sen", "Sel", "Rab", "Kam", "Jum", "Sab"]
HARI_PENUH = ["", "Minggu", "Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu"]
STOPS = ["#FFF3B0", "#FDBE4B", "#F26B38", "#C4262E", "#6E0F1A"]

# whitelist job; DS diganti dataset tervalidasi
JOBS = {
    "hdfs": ("Cek ukuran HDFS", f"{HADOOP} dfs -du -s -h /data/raw/crime /data/raw/crashes /data/raw/311"),
    "prep": ("Preprocessing MapReduce", "bash src/mr/run_prep.sh DS"),
    "parquet": ("TSV ke Parquet (Spark)", ".venv/bin/python -m src.load_parquet DS"),
    "pipeline": ("Pipeline lengkap", "bash src/pipeline.sh DS"),
    "preproses": ("Preprocessing (MapReduce + Parquet)", "bash src/mr/run_prep.sh DS && echo __STEP__parquet && .venv/bin/python -m src.load_parquet DS && echo __STEP__selesai"),
    "analitik": ("Analisis dan ML", "echo __STEP__mapreduce && bash src/mr/run_mr.sh && echo __STEP__bi && .venv/bin/python -m src.bi && echo __STEP__analisis && .venv/bin/python -m src.analisis && echo __STEP__ml && .venv/bin/python -m src.ml && echo __STEP__export && .venv/bin/python -m src.export_web && echo __STEP__selesai"),
    "hdfsls": ("Isi HDFS raw", f"{HADOOP} dfs -ls /data/raw/DS | tail -5"),
    "bi": ("Analisis BI PySpark", ".venv/bin/python -m src.bi"),
    "mapreduce": ("MapReduce di YARN", "bash src/mr/run_mr.sh"),
    "analisis": ("Analisis lokasi dan jenis", ".venv/bin/python -m src.analisis"),
    "ml": ("Machine learning MLlib", ".venv/bin/python -m src.ml"),
    "export": ("Ekspor ke web", ".venv/bin/python -m src.export_web"),
    "cek_hdfs": ("Cek HDFS", "bash src/demo/cek_hdfs.sh DS"),
    "reset_hdfs": ("Reset data HDFS", "bash src/demo/reset.sh hdfs"),
    "reset_semua": ("Reset penuh", "bash src/demo/reset.sh semua"),
}
STEP_MAP = {"prep": 3, "parquet": 4, "mapreduce": 5, "bi": 5, "analisis": 5, "ml": 6, "export": 7, "selesai": 8}


# ---------- format ----------
def nf(n, d=0):
    s = f"{float(n):,.{d}f}"
    return s.replace(",", "\0").replace(".", ",").replace("\0", ".")


def nama_jenis(j):
    return "Semua jenis" if j == "SEMUA" else j.capitalize()


def warna_panas(t):
    """Skala 5 stop (0..1) -> '#rrggbb'."""
    t = max(0.0, min(1.0, float(t)))
    x = t * (len(STOPS) - 1)
    i = min(int(x), len(STOPS) - 2)
    f = x - i
    a, b = STOPS[i], STOPS[i + 1]
    return "#" + "".join(f"{round(int(a[k:k+2], 16) * (1 - f) + int(b[k:k+2], 16) * f):02x}" for k in (1, 3, 5))


def warna_selisih(s):
    """-1 (biru B) .. 0 (abu) .. 1 (merah A)."""
    s = max(-1.0, min(1.0, float(s)))
    mid, end = (0xEC, 0xEF, 0xF2), ((0xC4, 0x26, 0x2E) if s >= 0 else (0x14, 0x78, 0xB5))
    f = abs(s)
    return "#" + "".join(f"{round(m * (1 - f) + e * f):02x}" for m, e in zip(mid, end))


# ---------- data ----------
def _csv(p):
    return pd.read_csv(WEB / p)


def siap():
    return (WEB / "kpi.json").is_file() and (WEB / "analisis" / "grid.csv").is_file()


def muat():
    """Semua tabel hasil pipeline sebagai dict DataFrame/dict (kunci = nama berkas CSV unduhan)."""
    j = lambda f: json.loads((WEB / f).read_text(encoding="utf-8"))
    m = j("metrics.json")
    d = {
        "kpi": j("kpi.json"), "metrics": m, "hdfs": j("hdfs_size.json"), "m1": j("m1_summary.json"),
        "meta": j("analisis/meta.json"),
        "district": _csv("district.csv"),
        "next_day": _csv("next_day.csv"),
        "test_pred": _csv("test_pred.csv").assign(day=lambda x: x["day"].astype(str)),
        "lag": pd.DataFrame(j("lag_corr.json")).rename(columns={"lag": "lg"}),
        "ext": pd.DataFrame(j("ext_corr.json")).rename(columns={"lag": "lg"}),
        "grid": _csv("analisis/grid.csv").rename(columns={"count": "n"}),
        "bulan": _csv("analisis/type_month.csv").rename(columns={"count": "n"}),
        "jam": _csv("analisis/type_hour.csv").rename(columns={"day_of_week": "dow", "hour": "hr", "count": "n"}),
        "tdist": _csv("analisis/type_district.csv").rename(columns={"count": "n"}),
        "profil": _csv("analisis/type_profile.csv").rename(columns={"top_district_share": "top_share"}),
        "korelasi": _csv("analisis/type_corr.csv"),
    }
    dhh = pd.read_csv(WEB / "crime_dhh.tsv", sep="\t", header=None, names=["k", "n"])
    dhh[["district", "dow", "hr"]] = dhh["k"].str.split("|", expand=True).astype(int)
    d["mr_dhh"] = dhh[["district", "dow", "hr", "n"]]
    d["model_metrics"] = (pd.DataFrame([{"model": k, **{x: v[x] for x in ("mae", "rmse", "r2")}}
                                        for k, v in m.items() if isinstance(v, dict) and "rmse" in v])
                          .sort_values("rmse").reset_index(drop=True))
    imp = m.get("importance_gbt_full", {})
    d["importance"] = pd.DataFrame({"fitur": list(imp), "nilai": list(imp.values())}).sort_values("nilai", ascending=False)
    return d


def daftar_jenis(d):
    """Jenis diurut menurut jumlah laporan, LAINNYA ikut bila ada di profil."""
    p = d["profil"].sort_values("n", ascending=False)
    return list(p["jenis"])


def warna_jenis(d):
    top = d["meta"]["top"]
    pal = ["#C4262E", "#1478B5", "#F2A33A", "#2E9E6B", "#7B4FA3", "#E4572E", "#17B3B3", "#8C6D3F", "#D6338A", "#4A5FC1", "#9AA52A", "#16202B"]
    return {j: (pal[top.index(j)] if j in top else "#7A8794") for j in daftar_jenis(d)}


# ---------- rumus peta ----------
def p98(v):
    v = sorted(v)
    return v[int(len(v) * 0.98)] if v else 1


def intensitas(n, p):
    return min(1.0, math.sqrt(n / p))


def selisih_sel(a: pd.DataFrame, b: pd.DataFrame):
    """a,b: kolom la,lo,n. Kembalikan DataFrame la,lo,na,nb,s (s -1..1, positif = A dominan)."""
    sa, sb = a["n"].sum() or 1, b["n"].sum() or 1
    m = a[["la", "lo", "n"]].merge(b[["la", "lo", "n"]], on=["la", "lo"], how="outer", suffixes=("_a", "_b")).fillna(0)
    m = m.rename(columns={"n_a": "na", "n_b": "nb"})
    d = m["na"] / sa - m["nb"] / sb
    mx = d.abs().max() or 1
    m["s"] = d.apply(lambda x: math.copysign(math.sqrt(abs(x) / mx), x) if x else 0.0)
    return m[["la", "lo", "na", "nb", "s"]]


def titik_terpanas(g: pd.DataFrame, k=5):
    """Sel terpadat dengan jarak pisah hypot(dla, dlo*0.75) > 0.02."""
    pk = []
    for _, c in g.sort_values("n", ascending=False).iterrows():
        if all(math.hypot(q["la"] - c["la"], (q["lo"] - c["lo"]) * 0.75) > 0.02 for q in pk):
            pk.append({"la": c["la"], "lo": c["lo"], "n": int(c["n"])})
        if len(pk) >= k:
            break
    return pk


def konsentrasi10(g):
    """Persen laporan di 10% sel teratas."""
    t = g["n"].sort_values(ascending=False)
    k = max(1, math.ceil(len(t) * 0.1))
    return t.iloc[:k].sum() / t.sum() * 100


# ---------- rumus ML / tren ----------
def indeks_tren(bulan_df, jenis):
    """Bulan parsial pertama dan terakhir dibuang; indeks 100 = bulan penuh pertama."""
    bl = sorted(bulan_df["bulan"].unique())[1:-1]
    s = bulan_df[bulan_df["jenis"] == jenis].set_index("bulan")["n"]
    b0 = s.get(bl[0], 1) or 1
    return bl, [s.get(x, 0) / b0 * 100 for x in bl]


def arah_tren(v):
    return "naik" if v >= 105 else "turun" if v <= 95 else "datar"


def grid_jam(jam_df, jenis):
    """Matriks 8x24 (dow 1..7, jam 0..23)."""
    g = [[0] * 24 for _ in range(8)]
    for r in jam_df[jam_df["jenis"] == jenis].itertuples():
        g[int(r.dow)][int(r.hr)] = int(r.n)
    return g


def puncak_jam(g):
    """(hari, jam, frac_sore): jam 0 diabaikan (waktu bawaan data); sore = 16-21."""
    mx, pd_, ph = -1, 1, 1
    for a in range(1, 8):
        for b in range(1, 24):
            if g[a][b] > mx:
                mx, pd_, ph = g[a][b], a, b
    jm = [sum(g[a][b] for a in range(1, 8)) for b in range(24)]
    tot = sum(jm[1:]) or 1
    return pd_, ph, sum(jm[16:22]) / tot


def meter(pred, p33, p66):
    """Persen posisi (p33, p66, pred) pada skala meter risiko."""
    hi = max(p66 * 1.4, pred * 1.15)
    pc = lambda v: min(100.0, v / hi * 100)
    return pc(p33), pc(p66), pc(pred)


def kartu_risiko(next_day):
    return next_day[(next_day["district"] != 61) & (next_day["pred"] > 5)].sort_values("pred", ascending=False)


def soal_tebak(seri, rnd):
    """seri: DataFrame day,n,prediction (urut). rnd: float 0..1. Soal = hari i, riwayat 7 hari sebelumnya."""
    i = 7 + int(rnd * (len(seri) - 7))
    h = seri.iloc[i - 7:i]
    return {"a": int(seri.iloc[i]["n"]), "m": float(seri.iloc[i]["prediction"]), "b": float(h["n"].mean()),
            "t": str(seri.iloc[i]["day"]), "riwayat": [(str(r.day), int(r.n)) for r in h.itertuples()]}


def nilai_tebakan(g, s):
    e = {"Anda": abs(g - s["a"]), "Model": abs(s["m"] - s["a"]), "Rata-rata 7 hari": abs(s["b"] - s["a"])}
    return e, min(e, key=e.get)


# ---------- validasi link ----------
def normalisasi(masuk, dari="", sampai=""):
    """Kembalikan (dataset, nama, url, where) atau string pesan galat."""
    try:
        u = urllib.parse.urlsplit(masuk.strip())
        host, user, port = (u.hostname or ""), u.username, u.port
    except ValueError:
        return "Hanya link https://data.cityofchicago.org yang diterima."
    if u.scheme != "https" or host.lower() != "data.cityofchicago.org" or user or port:
        return "Hanya link https://data.cityofchicago.org yang diterima."
    m = re.fullmatch(r"/(?:resource|api/views)/([a-z0-9]{4}-[a-z0-9]{4})(?:\.(?:csv|json)|/rows\.csv)", u.path)
    if not m or m.group(1) not in DATASET:
        return "Resource tidak dikenal. Boleh: ijzp-q8t2 (kejahatan), 85ca-t3if (kecelakaan), v6vf-nfxy (311)."
    ds = DATASET[m.group(1)]
    q = urllib.parse.parse_qs(u.query, keep_blank_values=True)
    where = (q.get("$where", [""])[0]).strip()
    if where == "" and dari and sampai:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", dari) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", sampai):
            return "Tanggal harus berformat YYYY-MM-DD."
        k = KOLOM[ds]
        where = f"{k} >= '{dari}T00:00:00' AND {k} < '{sampai}T00:00:00'"
    if where == "":
        return "Link belum punya filter $where. Isi rentang tanggal supaya unduhan tidak sebesar seluruh dataset."
    if re.search(r"[|\r\n]", where):
        return "Filter $where memuat karakter tidak valid."
    t = re.search(r"(\d{4}-\d{2}-\d{2})", where)
    nama = (t.group(1) if t else time.strftime("%Y%m%d")) + "_w" + hashlib.md5(where.encode()).hexdigest()[:6]
    try:
        lim = int(q.get("$limit", ["2000000"])[0])
    except ValueError:
        lim = 2000000
    url = f"https://data.cityofchicago.org/resource/{m.group(1)}.csv?%24where={urllib.parse.quote(where, safe='')}&%24limit={lim}"
    return ds, nama, url, where


def url_bulan(ds, dari, sampai):
    k = KOLOM[ds]
    rid = next(r for r, n in DATASET.items() if n == ds)
    return f"https://data.cityofchicago.org/resource/{rid}.csv?$where={k} >= '{dari}T00:00:00' AND {k} < '{sampai}T00:00:00'"


def rentang_bulan(y, m):
    return f"{y}-{m:02d}-01", (f"{y + 1}-01-01" if m == 12 else f"{y}-{m + 1:02d}-01")


def hari(rg):
    from datetime import date
    return (date.fromisoformat(rg[1]) - date.fromisoformat(rg[0])).days


def taksir_mb(daftar, rg):
    return sum(hari(rg) * MB_HARI[k] for k in daftar)


def ingest(ds, nama, url):
    """Kirim 'ds|nama|url' ke NiFi ListenHTTP. Kembalikan (ok, http, pesan)."""
    req = urllib.request.Request(NIFI_INGEST, data=f"{ds}|{nama}|{url}".encode(), headers={"Content-Type": "text/plain"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return 200 <= r.status < 300, r.status, f"NiFi membalas HTTP {r.status}"
    except urllib.error.HTTPError as e:
        return False, e.code, f"NiFi membalas HTTP {e.code}"
    except Exception as e:
        return False, 0, f"NiFi tidak terjangkau: {e}"


def hdfs_file(ds, nama):
    """(ada, MB) berkas /data/raw/<ds>/<ds>_<nama>.csv."""
    n = re.sub(r"[^A-Za-z0-9_.-]", "", nama or "")
    if not n or ds not in KOLOM:
        return False, 0.0
    try:
        o = subprocess.run([HADOOP, "dfs", "-du", f"/data/raw/{ds}/{ds}_{n}.csv"], capture_output=True, text=True, timeout=30).stdout.strip()
    except Exception:
        return False, 0.0
    m = re.match(r"(\d+)\s", o)
    return (True, round(int(m.group(1)) / 1e6, 1)) if m else (False, 0.0)


class Akuisisi:
    """Kirim tugas [(ds, (dari, sampai))] ke NiFi lalu tunggu masuk HDFS, di thread latar.
    Dataset 311 dikirim satu per satu (tunggu masuk HDFS dulu; ADR 0016), lainnya langsung."""

    def __init__(self, tugas, selesai_pesan):
        self.tugas, self.pesan_selesai = tugas, selesai_pesan
        self.log, self.masuk, self.sisa = [], [], {}
        self.selesai = self.gagal = False
        import threading
        self.t = threading.Thread(target=self._jalan, daemon=True)
        self.t.start()

    def _l(self, teks, jenis="info"):
        self.log.append((time.strftime("%H:%M:%S"), jenis, teks))

    def _tunggu(self, ids, batas=500):
        n = 0
        while ids and n < batas:
            for id_ in list(ids):
                ds, nama = id_
                ada, mb = hdfs_file(ds, nama)
                if ada:
                    ids.remove(id_)
                    self.masuk.append(f"/data/raw/{ds}/{ds}_{nama}.csv ({mb} MB)")
                    self._l(f"{NAMA_DS[ds]} masuk HDFS ({mb} MB). Sisa {len(ids)}.", "ok")
            if ids:
                time.sleep(3)
                n += 1
        return not ids

    def _jalan(self):
        try:
            ids = set()
            for ds, rg in self.tugas:
                r = normalisasi(url_bulan(ds, *rg))
                if isinstance(r, str):
                    self._l(f"{NAMA_DS[ds]}: {r}", "gagal")
                    continue
                self._l(f"{NAMA_DS[ds]} {rg[0][:7]}: link valid, mengirim ke NiFi...")
                ok, kode, pesan = ingest(r[0], r[1], r[2])
                self._l(f"{NAMA_DS[ds]}: {pesan}", "ok" if ok else "gagal")
                if not ok:
                    continue
                ids.add((r[0], r[1]))
                if ds == "311" and len(self.tugas) > 1:
                    self._l("NiFi mengunduh 311 (besar), tunggu masuk HDFS sebelum kiriman berikutnya...")
                    self._tunggu(ids)
            if not ids and not self.masuk:
                self.gagal = True
            else:
                self.sisa = ids
                self._l(f"NiFi mengunduh {len(ids)} berkas dari portal...")
                if not self._tunggu(ids):
                    self.gagal = True
                    self._l(f"Belum muncul di HDFS: {len(ids)} berkas. Cek NiFi.", "gagal")
                else:
                    self._l(self.pesan_selesai, "ok")
        except Exception as e:  # thread latar: jangan mati diam-diam
            self.gagal = True
            self._l(f"Galat: {e}", "gagal")
        finally:
            self.selesai = True


# ---------- job ----------
ENV_JOB = ("export JAVA_HOME=$(dirname $(dirname $(readlink -f $(which javac))))\n"
           "export HADOOP_HOME=/usr/local/hadoop SPARK_HOME=/usr/local/spark\n"
           "export PATH=$PATH:$HADOOP_HOME/bin:$HADOOP_HOME/sbin:$SPARK_HOME/bin\n")


def jalankan_job(job, ds="all"):
    if job not in JOBS:
        raise ValueError("job tidak dikenal")
    if ds not in ("crime", "crashes", "311", "all"):
        ds = "all"
    JOBDIR.mkdir(parents=True, exist_ok=True)
    log = JOBDIR / f"{job}.log"
    sh = JOBDIR / f"{job}.sh"
    sh.write_text("#!/bin/bash\n" + ENV_JOB + f"cd {ROOT}\n" + JOBS[job][1].replace("DS", ds) + "\necho __EXIT__$?\n")
    log.write_text("")
    subprocess.Popen(["bash", str(sh)], stdout=open(log, "a"), stderr=subprocess.STDOUT, start_new_session=True)


def baca_log(job):
    f = JOBDIR / f"{job}.log"
    semua = f.read_text(errors="replace").splitlines() if f.is_file() else []
    t = "\n".join(semua[-25:])
    steps = [m.group(1) for l in semua if (m := re.match(r"__STEP__(\S+)", l))]
    return {"log": t, "done": "__EXIT__" in t, "ok": "__EXIT__0" in t, "steps": steps}


def tahap_aktif(job, steps, done):
    """Indeks stepper 0..8 (port JS warnai/MAP)."""
    if not steps:
        return 3 if job == "preproses" else 0
    last = steps[-1]
    return 5 if job == "preproses" and last == "selesai" else STEP_MAP.get(last, 3)


# ---------- unduhan hasil (CSV / ZIP) ----------
def tabel_csv(d):
    """{nama: DataFrame} semua hasil pipeline yang bisa diunduh sebagai CSV."""
    kv = lambda x: pd.DataFrame({"kunci": list(x), "nilai": list(x.values())})
    t = {k: v for k, v in d.items() if isinstance(v, pd.DataFrame)}
    t["kpi"] = kv(d["kpi"])
    t["hdfs"] = kv(d["hdfs"])
    t["preprocess"] = pd.DataFrame(d["m1"]).T.rename_axis("dataset").reset_index()
    t["meta"] = pd.DataFrame({"kunci": list(d["meta"]), "nilai": [",".join(map(str, v)) if isinstance(v, list) else v for v in d["meta"].values()]})
    return t


def insight_md(d):
    """Ringkasan hasil dalam Markdown, dari data yang sudah dimuat."""
    m, k = d["metrics"], d["kpi"]
    mm = d["model_metrics"]
    base = mm[mm["model"] == "baseline_mean7"]["rmse"]
    top = mm.iloc[0]
    L = ["# Ringkasan hasil Chicago Crime", "",
         f"- Periode: {m['first_day']} s.d. {m['last_day']}; total kejadian {int(k['total']):,}".replace(",", "."),
         f"- Tingkat penangkapan {k['arrest_rate'] * 100:.1f}%, kasus domestik {k['domestic_pct'] * 100:.1f}%",
         f"- Model terbaik: {top['model']} (RMSE {top['rmse']:.2f}, R2 {top['r2']:.2f})"
         + (f"; baseline rata-rata 7 hari RMSE {base.iloc[0]:.2f}" if len(base) else ""),
         f"- Tambahan fitur 311 dan kecelakaan mengubah RMSE {m.get('ext_gain_rmse_pct', 0):+.2f}% (negatif = tidak membantu)",
         "", "## Jenis kejahatan terbanyak"]
    p = d["profil"].sort_values("n", ascending=False).head(5)
    L += [f"{i}. {r.jenis}: {int(r.n):,} kejadian".replace(",", ".") for i, r in enumerate(p.itertuples(), 1)]
    L += ["", "## 5 titik terpanas (lintang, bujur, kejadian)"]
    L += [f"- {q['la']:.3f}, {q['lo']:.3f}: {q['n']}" for q in titik_terpanas(d["grid"].groupby(["la", "lo"], as_index=False)["n"].sum())]
    L += ["", "## Prakiraan besok (district dengan prediksi tertinggi)"]
    L += [f"- District {int(r.district)}: {r.pred:.1f} kejadian, risiko {r.risk}" for r in kartu_risiko(d["next_day"]).head(5).itertuples()]
    L += ["", "Prakiraan statistik, bukan kepastian."]
    return "\n".join(L) + "\n"


def zip_hasil(d=None):
    """ZIP berisi insight.md dan satu CSV per tabel (utf-8-sig agar terbuka benar di Excel)."""
    import io, zipfile
    d = d or muat()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("insight.md", insight_md(d))
        for n, df in tabel_csv(d).items():
            z.writestr(f"{n}.csv", df.to_csv(index=False, encoding="utf-8-sig"))
    return buf.getvalue()


# ---------- halaman Kode ----------
def daftar_kode():
    """{path: penjelasan} dari bagian '### `path`' di peta-kode-spark.md (kosong bila tidak ada)."""
    pen = {}
    if PETA_KODE.is_file():
        for blok in re.split(r"^### ", PETA_KODE.read_text(encoding="utf-8"), flags=re.M)[1:]:
            h, _, isi = blok.partition("\n")
            for p in re.findall(r"`([^`]+)`", h):  # judul bisa memuat beberapa path
                pen[p] = isi.strip()
            if "run_prep.sh" in h:
                pen["src/mr/run_prep.sh"] = pen["src/mr/run_mr.sh"] = isi.strip()
    berkas = sorted([*ROOT.glob("src/*.py"), *ROOT.glob("src/*.sh"), *ROOT.glob("src/mr/*")])
    return [(str(p.relative_to(ROOT)), pen.get(str(p.relative_to(ROOT)), "")) for p in berkas if p.is_file()]
