"""Modul 2 (ML): prediksi jumlah kejahatan harian per district.
Fitur hanya dari hari SEBELUMNYA (tanpa kebocoran). Uji = 12 bulan terakhir.
Bandingkan: baseline rata-rata 7 hari, model dasar (crime saja), model penuh (+311 +crashes)."""
import json, os
from pyspark.ml import Pipeline
from pyspark.ml.evaluation import RegressionEvaluator
from pyspark.ml.feature import VectorAssembler
from pyspark.ml.regression import GBTRegressor, RandomForestRegressor
from pyspark.sql import SparkSession, Window, functions as F

HDFS = "hdfs://localhost:9000"
OUT = "data/ml"
SR_GROUPS = {  # keluhan 311 yang relevan dengan kondisi lingkungan
    "graffiti": ["Graffiti Removal Request"],
    "streetlight": ["Street Light Out Complaint", "Street Lights - All/Out"],
    "abandoned_veh": ["Abandoned Vehicle Complaint"],
    "building_viol": ["Building Violation"],
    "dumping": ["Fly Dumping Complaint", "Sanitation Code Violation"],
    "rodent": ["Rodent Baiting/Rat Complaint"],
}


def daily(df, dcol, name, extra=None):
    g = df.groupBy("district", F.to_date(dcol).alias("day"))
    aggs = [F.count("*").alias(name)] + (extra or [])
    return g.agg(*aggs)


def build(spark):
    r = lambda n: spark.read.parquet(f"{HDFS}/data/processed/{n}")
    crime = daily(r("crime"), "date", "n")
    sr = r("311")
    ext = [F.sum(F.col("sr_type").isin(v).cast("int")).alias(k) for k, v in SR_GROUPS.items()]
    sr_d = daily(sr, "created_date", "sr_all", ext)
    cr_d = daily(r("crashes"), "crash_date", "crash_n", [F.sum("injuries_total").alias("crash_inj")])

    last = crime.agg(F.max("day")).first()[0]
    first = crime.agg(F.min("day")).first()[0]
    big = crime.groupBy("district").agg(F.sum("n").alias("t")).filter("t >= 1000").select("district")
    days = spark.sql(f"select explode(sequence(to_date('{first}'), date_add(to_date('{last}'),1), interval 1 day)) as day")
    grid = big.crossJoin(days)
    df = (grid.join(crime, ["district", "day"], "left").join(sr_d, ["district", "day"], "left")
          .join(cr_d, ["district", "day"], "left"))
    ecols = ["sr_all", *SR_GROUPS, "crash_n", "crash_inj"]
    df = df.fillna(0, subset=["n", *ecols])
    df = df.withColumn("n", F.when(F.col("day") > F.lit(last), None).otherwise(F.col("n")))  # hari depan: tak diketahui

    w = Window.partitionBy("district").orderBy("day")
    p = lambda a, b: w.rowsBetween(a, b)
    df = (df.withColumn("lag_1", F.lag("n", 1).over(w)).withColumn("lag_7", F.lag("n", 7).over(w))
          .withColumn("lag_14", F.lag("n", 14).over(w))
          .withColumn("mean_7", F.avg("n").over(p(-7, -1))).withColumn("mean_30", F.avg("n").over(p(-30, -1))))
    for c in ecols:
        df = df.withColumn(f"{c}_7d", F.sum(c).over(p(-7, -1)))  # 7 hari sebelumnya saja
    df = (df.withColumn("day_of_week", F.dayofweek("day")).withColumn("month", F.month("day"))
          .withColumn("is_weekend", F.dayofweek("day").isin(1, 7).cast("int")))
    df = df.filter(F.col("day") >= F.date_add(F.lit(first), 31)).cache()
    return df, ecols, str(first), str(last)


def evaluate(pred, col="prediction"):
    e = RegressionEvaluator(labelCol="n", predictionCol=col)
    return {m: round(e.setMetricName(m).evaluate(pred), 4) for m in ("mae", "rmse", "r2")}


def main():
    spark = SparkSession.builder.master("local[2]").appName("ml").config("spark.driver.memory","6g").config("spark.local.dir",os.path.expanduser("~/spark-tmp")).getOrCreate()
    spark.sparkContext.setLogLevel("ERROR")
    os.makedirs(OUT, exist_ok=True)
    df, ecols, first, last = build(spark)
    cut = F.date_sub(F.lit(last).cast("date"), 365)
    train, test = df.filter((F.col("day") <= cut) & F.col("n").isNotNull()), df.filter((F.col("day") > cut) & F.col("n").isNotNull())
    future = df.filter(F.col("day") > F.lit(last).cast("date"))

    base = ["district", "lag_1", "lag_7", "lag_14", "mean_7", "mean_30", "day_of_week", "month", "is_weekend"]
    full = base + [f"{c}_7d" for c in ecols]
    res = {"first_day": first, "last_day": last, "train_rows": train.count(), "test_rows": test.count(),
           "baseline_mean7": evaluate(test.withColumn("p", F.col("mean_7")), "p")}
    best = None
    for fname, feats in (("base", base), ("full", full)):
        for mname, est in (("gbt", GBTRegressor(labelCol="n", maxIter=80, maxDepth=5, seed=1)),
                           ("rf", RandomForestRegressor(labelCol="n", numTrees=100, maxDepth=8, seed=1))):
            pipe = Pipeline(stages=[VectorAssembler(inputCols=feats, outputCol="features", handleInvalid="skip"), est]).fit(train)
            pred = pipe.transform(test)
            key = f"{mname}_{fname}"
            res[key] = evaluate(pred)
            if best is None or res[key]["rmse"] < res[best[0]]["rmse"]:
                best = (key, pipe)
            if key == "gbt_full":
                imp = pipe.stages[-1].featureImportances.toArray()
                res["importance_gbt_full"] = dict(sorted(zip(feats, map(lambda x: round(float(x), 4), imp)), key=lambda t: -t[1]))
                pred.select("district", "day", "n", "prediction").toPandas().to_csv(f"{OUT}/test_pred.csv", index=False)
    res["best_model"] = best[0]
    res["ext_gain_rmse_pct"] = round(100 * (1 - res["gbt_full"]["rmse"] / res["gbt_base"]["rmse"]), 2)

    # H+1 + level risiko dari persentil historis district
    pct = (df.filter(F.col("n").isNotNull()).groupBy("district")
           .agg(F.percentile_approx("n", 0.33).alias("p33"), F.percentile_approx("n", 0.66).alias("p66")))
    nxt = (best[1].transform(future).join(pct, "district")
           .withColumn("risk", F.when(F.col("prediction") <= F.col("p33"), "Rendah")
                       .when(F.col("prediction") <= F.col("p66"), "Sedang").otherwise("Tinggi"))
           .select("district", "day", F.round("prediction", 1).alias("pred"), "p33", "p66", "risk"))
    nxt.toPandas().sort_values("district").to_csv(f"{OUT}/next_day.csv", index=False)
    json.dump(res, open(f"{OUT}/metrics.json", "w"), indent=2)
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
