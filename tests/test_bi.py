import json
from src.bi import BI_DIR, OUT, compute, ext_corr, save
from src.preprocess import get_spark
import pandas as pd

sp = get_spark()
res = compute(sp.read.parquet(OUT))
save(res)
ec = ext_corr(sp, res["daily"])
assert {r["lag"] for r in ec} == {0, 7, 14, 30} and all(-1 <= r["corr"] <= 1 for r in ec)
assert {"sr_all", "graffiti", "crash_n"} <= {r["factor"] for r in ec}
n = json.load(open("data/m1_summary.json"))["crime"]["rows_final"]
assert res["kpi"]["total"] == n
assert 0 <= res["kpi"]["arrest_rate"] <= 1 and 0 <= res["kpi"]["domestic_pct"] <= 1
assert res["daily"]["count"].sum() == n == res["heatmap"]["count"].sum() == res["district"]["count"].sum()
assert res["weekly"]["count"].sum() == n
assert len(res["top_types"]) == 10 and res["top_types"]["count"].is_monotonic_decreasing
assert [r["lag"] for r in res["lag_corr"]] == list(range(1, 15))
assert all(-1 <= r["corr"] <= 1 for r in res["lag_corr"])
assert not pd.read_parquet(f"{BI_DIR}/daily.parquet").empty
print("OK semua tes BI")
