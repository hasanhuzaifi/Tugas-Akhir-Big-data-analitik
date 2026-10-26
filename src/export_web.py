"""Ekspor hasil Parquet/JSON ke CSV agar web (PHP + MySQL Laragon) dapat mengimpornya. Keluaran: web_export/"""
import os, shutil, pandas as pd
O = "web_export"; os.makedirs(O, exist_ok=True)
for n in ["daily", "weekly", "heatmap", "top_types", "district"]:
    pd.read_parquet(f"data/bi/{n}.parquet").to_csv(f"{O}/{n}.csv", index=False)
for f in ["bi/kpi.json", "bi/lag_corr.json", "bi/ext_corr.json", "ml/metrics.json", "ml/next_day.csv", "ml/test_pred.csv",
          "mr/crime_dhh.tsv", "m1_summary.json", "hdfs_size.json"]:
    shutil.copy(f"data/{f}", O)
import glob
os.makedirs(f"{O}/analisis", exist_ok=True)
for f in glob.glob("data/analisis/*"): shutil.copy(f, f"{O}/analisis")
print("ok", sorted(os.listdir(O)))
