"""Uji logika app/inti.py. Jalankan: PYTHONPATH=. .venv/bin/python tests/test_app.py"""
import pandas as pd
from app import inti as i

OK = "https://data.cityofchicago.org/resource/ijzp-q8t2.csv?$where=date >= '2026-09-01T00:00:00' AND date < '2026-10-01T00:00:00'"
r = i.normalisasi(OK)
assert r[0] == "crime" and r[1].startswith("2026-09-01_w") and len(r[1]) == 18 and "%24where=" in r[2], r
assert i.normalisasi(OK.replace("https", "http")) .startswith("Hanya")
assert i.normalisasi(OK.replace("data.cityofchicago.org", "evil.com")).startswith("Hanya")
assert i.normalisasi(OK.replace("data.cityofchicago.org", "user@data.cityofchicago.org")).startswith("Hanya")
assert i.normalisasi(OK.replace("data.cityofchicago.org", "data.cityofchicago.org:8080")).startswith("Hanya")
assert i.normalisasi(OK.replace("ijzp-q8t2", "abcd-efgh")).startswith("Resource")
assert i.normalisasi(OK.replace("date >=", "date | >=")).startswith("Filter")
assert i.normalisasi("https://data.cityofchicago.org/resource/ijzp-q8t2.csv").startswith("Link belum")
assert i.normalisasi("https://data.cityofchicago.org/resource/85ca-t3if.csv", "2026-01-01", "2026-02-01")[0] == "crashes"
assert i.normalisasi("https://data.cityofchicago.org/resource/85ca-t3if.csv", "2026-1-1", "2026-02-01").startswith("Tanggal")
for ds in i.KOLOM:  # url_bulan harus lolos validasi
    assert not isinstance(i.normalisasi(i.url_bulan(ds, "2026-09-01", "2026-10-01")), str)
assert i.rentang_bulan(2026, 12) == ("2026-12-01", "2027-01-01")

assert i.nf(1234567.891, 2) == "1.234.567,89" and i.nf(0.5, 1) == "0,5"
assert i.warna_panas(0) == "#fff3b0" and i.warna_panas(1) == "#6e0f1a"
assert i.warna_selisih(0) == "#eceff2" and i.warna_selisih(1) == "#c4262e" and i.warna_selisih(-1) == "#1478b5"

a = pd.DataFrame({"la": [1.0, 2.0], "lo": [1.0, 1.0], "n": [10, 0]})
b = pd.DataFrame({"la": [2.0, 3.0], "lo": [1.0, 1.0], "n": [5, 5]})
s = i.selisih_sel(a, b).set_index("la")["s"]
assert s[1.0] == 1.0 and s[3.0] < 0 and 0 <= abs(s[2.0]) <= 1

g = pd.DataFrame({"la": [41.0, 41.001, 41.5, 42.0], "lo": [-87.0] * 4, "n": [100, 90, 80, 70]})
pk = i.titik_terpanas(g)
assert [p["n"] for p in pk] == [100, 80, 70], pk  # 41.001 terlalu dekat
assert round(i.konsentrasi10(g)) == 29  # 1 sel dari 4: 100/340

assert i.arah_tren(105) == "naik" and i.arah_tren(95) == "turun" and i.arah_tren(100) == "datar"
bd = pd.DataFrame({"jenis": ["X"] * 4, "bulan": ["2023-10", "2023-11", "2023-12", "2024-01"], "n": [1, 50, 100, 7]})
assert i.indeks_tren(bd, "X") == (["2023-11", "2023-12"], [100.0, 200.0])
jm = pd.DataFrame({"jenis": ["X", "X", "X"], "dow": [1, 2, 3], "hr": [0, 17, 3], "n": [999, 40, 10]})
d_, h_, sore = i.puncak_jam(i.grid_jam(jm, "X"))
assert (d_, h_) == (2, 17) and abs(sore - 0.8) < 1e-9  # jam 0 diabaikan

p33, p66, pr = i.meter(40, 30, 50)
assert abs(p66 - 50 / 70 * 100) < 1e-9 and pr < 100 and p33 < p66  # hi = max(70, 46)
assert abs(i.meter(100, 30, 50)[2] - 100 / 115 * 100) < 1e-9
nd = pd.DataFrame({"district": [1, 61, 2], "pred": [20, 50, 3], "p33": 0, "p66": 0, "risk": "x"})
assert list(i.kartu_risiko(nd)["district"]) == [1]

sr = pd.DataFrame({"day": [f"2026-01-{k:02d}" for k in range(1, 21)], "n": range(20), "prediction": 1.5})
sl = i.soal_tebak(sr, 0.0)
assert sl["t"] == "2026-01-08" and sl["b"] == 3.0 and len(sl["riwayat"]) == 7
assert i.soal_tebak(sr, 0.999999)["t"] == "2026-01-20"
e, menang = i.nilai_tebakan(7, sl)
assert menang == "Anda" and e["Model"] == 5.5

assert set(i.JOBS) >= {"hdfs", "preproses", "analitik", "export"}
try:
    i.jalankan_job("rm -rf")
    raise SystemExit("job asing harus ditolak")
except ValueError:
    pass
assert i.tahap_aktif("preproses", ["parquet", "selesai"], True) == 5 and i.tahap_aktif("analitik", ["ml"], False) == 6

if i.siap():
    d = i.muat()
    jn = i.daftar_jenis(d)
    assert len(jn) >= 12 and set(i.warna_jenis(d)) == set(jn)
    tb = i.skema_tabel(d)
    assert {t[0] for t in tb} >= {"kpi", "a_grid", "mr_dhh", "next_day", "preprocess", "a_meta"}
    assert all(len(r) == len(cols) for _, _, cols, rows in tb for r in rows[:50])
    assert len(i.kartu_risiko(d["next_day"])) > 0 and d["model_metrics"].iloc[0]["rmse"] < 7
print("test_app OK")
