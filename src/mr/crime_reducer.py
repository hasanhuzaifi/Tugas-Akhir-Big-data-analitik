#!/usr/bin/env python3
"""MapReduce reducer: jumlahkan hitungan per kunci (input sudah terurut oleh shuffle)."""
import sys

key, n = None, 0
for line in sys.stdin:
    k, v = line.rstrip("\n").split("\t")
    if k != key:
        if key is not None:
            print(f"{key}\t{n}")
        key, n = k, 0
    n += int(v)
if key is not None:
    print(f"{key}\t{n}")
