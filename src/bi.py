"""M2-1..M2-3: BI dari Parquet bersih di HDFS -> data/bi/*.json|parquet (fallback UI tanpa Spark)."""
import json, os
from pyspark.sql import functions as F
from src.preprocess import get_spark, HDFS
from src.ml import SR_GROUPS

OUT = f"{HDFS}/data/processed/crime"
BI_DIR = "data/bi"


def ext_corr(spark, crime_daily):
    """Korelasi harian kota: kejahatan hari t vs keluhan 311 / kecelakaan pada t-k (k=0,7,14,30)."""
    sr = spark.read.parquet(f"{HDFS}/data/processed/311")
    cr = spark.read.parquet(f"{HDFS}/data/processed/crashes")
    aggs = [F.count("*").alias("sr_all")] + [F.sum(F.col("sr_type").isin(v).cast("int")).alias(k) for k, v in SR_GROUPS.items()]
    a = sr.groupBy(F.to_date("created_date").alias("tgl")).agg(*aggs).toPandas()
    b = cr.groupBy(F.to_date("crash_date").alias("tgl")).agg(F.count("*").alias("crash_n")).toPandas()
    import pandas as pd
    base = crime_daily.assign(tgl=pd.to_datetime(crime_daily["tgl"])).set_index("tgl")["count"].rename("crime")
    x = pd.concat([base, a.assign(tgl=pd.to_datetime(a["tgl"])).set_index("tgl"),
                   b.assign(tgl=pd.to_datetime(b["tgl"])).set_index("tgl")], axis=1).dropna(subset=["crime"]).fillna(0)
    return [{"factor": c, "lag": k, "corr": float(x["crime"].corr(x[c].shift(k)))}
            for c in x.columns if c != "crime" for k in (0, 7, 14, 30)]


def compute(df):
    """Kembalikan dict nama -> pandas DataFrame / dict KPI."""
    total = df.count()
    k = df.agg(F.avg(F.col("arrest").cast("int")), F.avg(F.col("domestic").cast("int"))).first()
    kpi = {"total": total, "arrest_rate": k[0], "domestic_pct": k[1]}
    d = df.withColumn("tgl", F.date_format("date", "yyyy-MM-dd"))
    daily = d.groupBy("tgl").count().orderBy("tgl").toPandas()
    weekly = (d.groupBy(F.date_format(F.date_trunc("week", "date"), "yyyy-MM-dd").alias("minggu")).count()
              .orderBy("minggu").toPandas())
    heat = df.groupBy("day_of_week", "hour").count().orderBy("day_of_week", "hour").toPandas()
    top = df.groupBy("primary_type").count().orderBy(F.desc("count")).limit(10).toPandas()
    dist = (df.groupBy("district").agg(F.count("*").alias("count"),
            F.avg(F.col("arrest").cast("int")).alias("arrest_rate"))
            .orderBy("district").toPandas())
    # M2-3: korelasi Pearson count_t vs count_{t-k}, k=1..14, deret harian kota; hari kosong = 0
    s = daily.set_index("tgl")["count"]
    s.index = s.index.astype("datetime64[ns]")
    s = s.asfreq("D", fill_value=0)
    lag = [{"lag": i, "corr": float(s.corr(s.shift(i)))} for i in range(1, 15)]
    return {"kpi": kpi, "daily": daily, "weekly": weekly, "heatmap": heat,
            "top_types": top, "district": dist, "lag_corr": lag}


def save(res, out=BI_DIR):
    os.makedirs(out, exist_ok=True)
    json.dump(res["kpi"], open(f"{out}/kpi.json", "w"), indent=2)
    json.dump(res["lag_corr"], open(f"{out}/lag_corr.json", "w"), indent=2)
    for n in ("daily", "weekly", "heatmap", "top_types", "district"):
        res[n].to_parquet(f"{out}/{n}.parquet", index=False)


if __name__ == "__main__":
    spark = get_spark()
    res = compute(spark.read.parquet(OUT))
    res["ext_corr"] = ext_corr(spark, res["daily"])
    save(res)
    json.dump(res["ext_corr"], open(f"{BI_DIR}/ext_corr.json", "w"), indent=2)
    print("ext:", {f'{r["factor"]}@{r["lag"]}': round(r["corr"], 2) for r in res["ext_corr"]})
    print(json.dumps(res["kpi"], indent=2))
    print(res["top_types"].to_string(index=False))
    print("lag:", {r["lag"]: round(r["corr"], 3) for r in res["lag_corr"]})
    print("hari:", len(res["daily"]), "minggu:", len(res["weekly"]), "district:", len(res["district"]))
    print("heatmap sel:", len(res["heatmap"]))
