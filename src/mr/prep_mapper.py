#!/usr/bin/env python3
"""MapReduce mapper preprocessing: CSV mentah -> "kunci\tversi\tkolom..." (kolom bersih menurut prepcfg.kolom).
Argumen: crime|crashes|311. Header dan baris lanjutan (field location multi-baris) dibuang lewat cek bentuk kunci.
Counter M1.rows_in. Akhir: "~MAX\ttanggal-terbesar" agar load_parquet membuang hari parsial."""
import csv, os, re, sys
sys.path.insert(0, os.getcwd())  # -files memakai symlink; cwd container berisi prepcfg.py
from datetime import datetime
import prepcfg as C

ds = sys.argv[1]
raw, ordcol, datecol, _ = C.DS[ds]
ix = {c: i for i, c in enumerate(raw)}
valid = {"crime": lambda k: k.isdigit(), "crashes": lambda k: re.fullmatch(r"[0-9a-f]{20,}", k) is not None,
         "311": lambda k: k.startswith("SR") and "_" not in k}[ds]
bersih = lambda s: re.sub(r"[\t\r\n]", " ", s).strip()
bool_ = lambda b: "true" if b else "false"
rows_in, mx = 0, ""
for r in csv.reader(sys.stdin):
    if len(r) <= ix["longitude"] or not valid(r[0]):
        continue
    rows_in += 1
    v = {c: bersih(r[i]) for c, i in ix.items()}
    try:
        d = datetime.strptime(v[datecol][:19], "%Y-%m-%dT%H:%M:%S")
        if ds == "crime":
            dist = int(float(v["district"]))
        elif ds == "crashes":
            dist = int(float(v["beat_of_occurrence"]) / 100)
        else:
            dist = int(float(v["police_district"]))
            v["community_area"] = str(int(float(v["community_area"]))) if v["community_area"] else ""
        if ds == "crashes" and v["injuries_total"]:
            v["injuries_total"] = str(int(float(v["injuries_total"])))
    except ValueError:
        continue  # tanggal atau district kosong/rusak -> buang (sama dengan filter lama)
    if v[datecol][:10] < C.START or (ds != "crime" and dist <= 0):
        continue
    if ds == "crime":
        v["arrest"], v["domestic"] = bool_(v["arrest"].lower() == "true"), bool_(v["domestic"].lower() == "true")
        v["primary_type"] = v["primary_type"].upper()
        v["time_missing"] = bool_(d.strftime("%H:%M:%S") == "00:00:00")
    v["district"] = str(dist)
    v["hour"], v["month"] = str(d.hour), str(d.month)
    v["day_of_week"] = str(d.isoweekday() % 7 + 1)  # 1=Min .. 7=Sab, sama dengan Spark dayofweek
    v["is_weekend"] = bool_(d.isoweekday() >= 6)
    mx = max(mx, v[datecol][:10])
    print("\t".join([v[raw[0]], v[ordcol]] + [v[c] for c in C.kolom(ds)]))
print(f"~MAX\t{mx}")
print(f"reporter:counter:M1,rows_in,{rows_in}", file=sys.stderr)
