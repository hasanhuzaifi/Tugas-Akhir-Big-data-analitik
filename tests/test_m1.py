"""Tes preprocessing MapReduce: data sintetis lewat mapper | sort | reducer; opsi --parquet cek hasil di HDFS."""
import json, os, subprocess, sys

MR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src", "mr")
sys.path.insert(0, MR)
import prepcfg as C

def baris(i, tgl, tipe, arrest, dist, upd):
    r = {c: "" for c in C.CRIME}
    r.update(id=i, case_number="X" + i, date=tgl, primary_type=tipe, arrest=arrest, domestic="false", district=dist, updated_on=upd, latitude="41.8", longitude="-87.6")
    return ",".join(f'"{r[c]}"' for c in C.CRIME) + ',"POINT (1 2)"'

# 5 masuk: 1 baris identik, 1 id sama beda isi (updated_on terbaru menang), hari 01-03 parsial -> 2 akhir
data = "\n".join(["id,case_number"] + [
    baris("1", "2026-01-01T10:00:00.000", "theft", "true", "1", "2026-02-01T00:00:00.000"),
    baris("1", "2026-01-01T10:00:00.000", "theft", "true", "1", "2026-02-01T00:00:00.000"),
    baris("1", "2026-01-01T10:00:00.000", "theft", "false", "1", "2026-01-05T00:00:00.000"),
    baris("2", "2026-01-02T00:00:00.000", "battery", "false", "2", "2026-02-01T00:00:00.000"),
    baris("3", "2026-01-03T09:00:00.000", "theft", "false", "1", "2026-02-01T00:00:00.000")]) + "\n"
run = lambda cmd, inp: subprocess.run(cmd, input=inp, capture_output=True, text=True, cwd=MR, check=True).stdout
m = run([sys.executable, "prep_mapper.py", "crime"], data)
out = run([sys.executable, "prep_reducer.py"], "".join(sorted(m.splitlines(True))))
rows = [l.split("\t") for l in out.splitlines()]
mx = [r[1] for r in rows if r[0] == "~MAX"][0]
recs = [dict(zip(C.kolom("crime"), r)) for r in rows if r[0] != "~MAX"]
assert len(recs) == 3 and mx == "2026-01-03", (len(recs), mx)
fin = [r for r in recs if r["date"][:10] < mx]
assert len(fin) == 2
assert [r for r in fin if r["id"] == "1"][0]["arrest"] == "true"
r2 = [r for r in fin if r["id"] == "2"][0]
assert r2["time_missing"] == "true" and r2["primary_type"] == "BATTERY" and r2["day_of_week"] == "6", r2  # Jumat = 6 (1=Min)
print("OK sintetis MapReduce")

if "--parquet" in sys.argv:
    from pyspark.sql import functions as F
    from src.preprocess import get_spark, HDFS, START
    sp = get_spark(); s = json.load(open("data/m1_summary.json"))
    for name, dcol in (("crime", "date"), ("crashes", "crash_date"), ("311", "created_date")):
        df = sp.read.parquet(f"{HDFS}/data/processed/{name}"); st = s[name]
        assert df.count() == st["rows_final"] > 0, name
        assert st["rows_after_dedup"] <= st["rows_in"], name
        assert df.agg(F.min(dcol)).first()[0].strftime("%Y-%m-%d") >= START, name
        assert df.filter("district is null").count() == 0, name
        assert df.agg(F.max(F.to_date(dcol))).first()[0].isoformat() < st["dropped_partial_day"], name
    c = sp.read.parquet(f"{HDFS}/data/processed/crime")
    assert c.select("id").distinct().count() == c.count(), "id crime duplikat"
    assert dict(c.dtypes)["arrest"] == "boolean" and dict(c.dtypes)["time_missing"] == "boolean"
    print("OK Parquet")
