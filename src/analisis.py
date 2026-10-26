"""Analisis interaktif web (3 analisis utama): sebaran lokasi, perbandingan jenis, korelasi antarjenis.
Baca Parquet crime bersih di HDFS -> data/analisis/*.csv|json. Jalankan: python -m src.analisis"""
import json, os
import pandas as pd
from pyspark.sql import functions as F
from src.preprocess import get_spark, HDFS

SRC = f"{HDFS}/data/processed/crime"
OUT = "data/analisis"
TOP = 12          # jenis yang dipetakan sendiri; sisanya digabung ke LAINNYA
CELL = 0.005      # derajat per sel peta (±0,5 km)
# kotak Chicago; titik di luar ini (koordinat salah/0) dibuang dari peta
LAT, LON = (41.60, 42.05), (-87.95, -87.50)

def main():
    spark = get_spark()
    df = spark.read.parquet(SRC)
    top = [r[0] for r in df.groupBy("primary_type").count().orderBy(F.desc("count")).limit(TOP).collect()]
    df = df.withColumn("jenis", F.when(F.col("primary_type").isin(top), F.col("primary_type")).otherwise("LAINNYA"))
    os.makedirs(OUT, exist_ok=True)

    # 1. Di mana: sel peta per jenis
    ok = df.filter(F.col("latitude").between(*LAT) & F.col("longitude").between(*LON))
    n_all, n_ok = df.count(), ok.count()
    grid = (ok.withColumn("la", F.round(F.floor(F.col("latitude") / CELL) * CELL + CELL / 2, 4))
              .withColumn("lo", F.round(F.floor(F.col("longitude") / CELL) * CELL + CELL / 2, 4))
              .groupBy("jenis", "la", "lo").count().toPandas())
    grid.to_csv(f"{OUT}/grid.csv", index=False)

    # 2. Apa dan kapan: jenis x bulan, jenis x (hari, jam), profil, jenis x district
    df.groupBy("jenis", F.date_format("date", "yyyy-MM").alias("bulan")).count().toPandas().to_csv(f"{OUT}/type_month.csv", index=False)
    df.groupBy("jenis", "day_of_week", "hour").count().toPandas().to_csv(f"{OUT}/type_hour.csv", index=False)
    dist = df.groupBy("jenis", "district").count().toPandas()
    dist.to_csv(f"{OUT}/type_district.csv", index=False)
    prof = df.groupBy("jenis").agg(F.count("*").alias("n"),
                                   F.avg(F.col("arrest").cast("int")).alias("arrest_rate"),
                                   F.avg(F.col("domestic").cast("int")).alias("domestic_pct")).toPandas()
    top_d = dist.sort_values("count", ascending=False).groupby("jenis").head(1).set_index("jenis")
    prof["top_district"] = prof["jenis"].map(top_d["district"])
    prof["top_district_share"] = prof.apply(lambda r: top_d.loc[r["jenis"], "count"] / r["n"], axis=1)
    prof.to_csv(f"{OUT}/type_profile.csv", index=False)

    # 3. Korelasi harian antarjenis (Pearson, deret harian kota)
    daily = df.groupBy(F.to_date("date").alias("tgl"), "jenis").count().toPandas()
    wide = daily.pivot(index="tgl", columns="jenis", values="count").fillna(0)
    wide.corr().round(4).reset_index().rename(columns={"jenis": "a"}).melt(id_vars="a", var_name="b", value_name="corr") \
        .to_csv(f"{OUT}/type_corr.csv", index=False)

    meta = {"cell_deg": CELL, "top": top, "rows": n_all, "rows_mapped": n_ok, "rows_no_coord": n_all - n_ok,
            "cells": int(len(grid[["la", "lo"]].drop_duplicates()))}
    json.dump(meta, open(f"{OUT}/meta.json", "w"), indent=2)
    print(json.dumps(meta))

if __name__ == "__main__":
    main()
