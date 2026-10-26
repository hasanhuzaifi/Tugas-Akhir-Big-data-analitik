"""M1-1/M1-6: salin CSV mentah ke HDFS /data/raw/crime/ (CSV asli, tanpa ubah)."""
import subprocess, sys

RAW_DIR = "/data/raw/crime"


def ingest(local_csv: str) -> str:
    hdfs = "/usr/local/hadoop/bin/hdfs"
    subprocess.run([hdfs, "dfs", "-mkdir", "-p", RAW_DIR], check=True)
    subprocess.run([hdfs, "dfs", "-put", "-f", local_csv, RAW_DIR + "/"], check=True)
    return f"hdfs://localhost:9000{RAW_DIR}/{local_csv.rsplit('/', 1)[-1]}"


if __name__ == "__main__":
    print(ingest(sys.argv[1] if len(sys.argv) > 1 else "data/chicago_12bln.csv"))
