"""TSV bersih hasil MapReduce (/data/clean/<ds>) -> Parquet (/data/processed/<ds>), buang hari parsial terakhir.
Pakai: python -m src.load_parquet [crime|crashes|311|all]. Melengkapi data/m1_summary.json."""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "mr"))
from pyspark.sql import functions as F
from pyspark.sql.types import StructType, StructField, StringType
from src.preprocess import get_spark, HDFS
import prepcfg as C

def load(spark, ds):
    cols = C.kolom(ds)
    sch = StructType([StructField(c, StringType()) for c in cols])
    tsv = spark.read.csv(f"{HDFS}/data/clean/{ds}", sep="\t", schema=sch, quote="", mode="PERMISSIVE")
    mx = tsv.filter(F.col(cols[0]) == "~MAX").agg(F.max(cols[1])).first()[0]  # kolom ke-2 berisi tanggal terbesar
    df = tsv.filter(F.col(cols[0]) != "~MAX")
    for c, t in C.TIPE.items():
        if c in cols:
            df = df.withColumn(c, F.col(c).cast(t))
    after = df.count()
    dcol = C.DS[ds][2]
    df = df.filter(F.to_date(dcol) < F.lit(mx).cast("date"))
    df.write.mode("overwrite").parquet(f"{HDFS}/data/processed/{ds}")
    return {"rows_after_dedup": after, "dropped_partial_day": mx, "rows_final": df.count()}

if __name__ == "__main__":
    a = sys.argv[1] if len(sys.argv) > 1 else "all"
    sp = get_spark()
    p = "data/m1_summary.json"
    s = json.load(open(p)) if os.path.exists(p) else {}
    for ds in (C.DS if a == "all" else [a]):
        s[ds] = {**s.get(ds, {}), **load(sp, ds)}
        print(ds, json.dumps(s[ds]))
        json.dump(s, open(p, "w"), indent=2)
