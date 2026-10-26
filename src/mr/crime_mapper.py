#!/usr/bin/env python3
"""MapReduce (Hadoop Streaming) mapper: CSV crime mentah -> "district|hari|jam\t1".
Hanya baris yang diawali id numerik (baris lanjutan field `location` multi-baris dilewati)."""
import csv, sys
from datetime import datetime

START = "2023-10-25"
for r in csv.reader(sys.stdin):
    if len(r) < 14 or not r[0].isdigit():
        continue
    try:
        d = datetime.strptime(r[2], "%Y-%m-%dT%H:%M:%S.%f")
        dist = int(float(r[11]))
    except ValueError:
        continue
    if r[2][:10] < START:
        continue
    print(f"{dist}|{d.isoweekday() % 7 + 1}|{d.hour}\t1")  # hari 1=Min..7=Sab seperti Spark dayofweek
