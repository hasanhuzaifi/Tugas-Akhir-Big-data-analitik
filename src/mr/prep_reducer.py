#!/usr/bin/env python3
"""Reducer preprocessing: per kunci ambil versi terbaru (kolom ke-2), buang duplikat.
Counter M1.dup_identical (baris sama persis) dan M1.dup_key (kunci sama, isi beda). Keluaran: kolom bersih tanpa kunci/versi."""
import sys

def flush(rows):
    if not rows:
        return
    uniq = set(rows)
    ident, key = len(rows) - len(uniq), len(uniq) - 1
    if ident: print(f"reporter:counter:M1,dup_identical,{ident}", file=sys.stderr)
    if key: print(f"reporter:counter:M1,dup_key,{key}", file=sys.stderr)
    print("\t".join(max(uniq, key=lambda l: l.split("\t", 2)[1]).split("\t")[2:]))

cur, rows, mx = None, [], ""
for line in sys.stdin:
    line = line.rstrip("\n")
    k = line.split("\t", 1)[0]
    if k == "~MAX":
        mx = max(mx, line.split("\t")[1])
        continue
    if k != cur:
        flush(rows)
        cur, rows = k, []
    rows.append(line)
flush(rows)
if mx:
    print(f"~MAX\t{mx}")
