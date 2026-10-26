"""MapReduce (Hadoop Streaming) harus sama dengan PySpark untuk hitungan district x hari x jam."""
import pandas as pd
from pyspark.sql import functions as F
from src.preprocess import HDFS, get_spark

mr = pd.read_csv("data/mr/crime_dhh.tsv", sep="\t", header=None, names=["k", "mr"])
mr[["district", "day_of_week", "hour"]] = mr["k"].str.split("|", expand=True).astype(int)

df = get_spark().read.parquet(f"{HDFS}/data/processed/crime")
# MR membaca CSV mentah sampai hari terakhir; Spark membuang hari parsial terakhir -> samakan
last = df.agg(F.max(F.to_date("date"))).first()[0]
sp = (df.groupBy("district", "day_of_week", "hour").count().toPandas().rename(columns={"count": "spark"}))
m = mr.merge(sp, on=["district", "day_of_week", "hour"], how="outer").fillna(0)
tot_mr, tot_sp = int(m["mr"].sum()), int(m["spark"].sum())
print("MR total", tot_mr, "Spark total", tot_sp, "selisih", tot_mr - tot_sp, "(hari parsial dibuang Spark: >", last, ")")
# MR termasuk hari parsial terakhir + baris tanpa district tidak dibuang oleh MR -> MR >= Spark, selisih kecil
assert tot_mr >= tot_sp and (tot_mr - tot_sp) / tot_sp < 0.001, "selisih MR vs Spark terlalu besar"
big = m[m["spark"] > 0]
assert (big["mr"] >= big["spark"]).all()
print("OK MR cocok dengan Spark")
