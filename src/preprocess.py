"""Konfigurasi bersama Spark. Preprocessing (parse, dedup, fitur waktu) kini MapReduce: src/mr/prep_*.py, run_prep.sh.
Parquet dibuat oleh src/load_parquet.py."""
import os
from pyspark.sql import SparkSession

HDFS = "hdfs://localhost:9000"
START = "2023-10-25"

def get_spark():
    return (SparkSession.builder.master("local[2]").appName("spark")
            .config("spark.driver.memory", "6g").config("spark.local.dir", os.path.expanduser("~/spark-tmp")).config("spark.sql.shuffle.partitions", "16")
            .getOrCreate())
