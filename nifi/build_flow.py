"""Bangun SATU flow NiFi Modul 1 lewat REST API untuk ketiga dataset (crime, crashes, 311):
[GenerateFlowFile bulanan | ListenHTTP dari web] -> SplitText -> ExtractText -> InvokeHTTP -> UpdateAttribute -> PutFile (simpan lokal) -> PutHDFS.
Pakai: NIFI_PASS=... python3 nifi/build_flow.py   (user: env NIFI_USER, default nifiadmin)
"""
import json, os, ssl, urllib.request, urllib.parse, datetime as dt

API = "https://localhost:8443/nifi-api"
CTX = ssl._create_unverified_context()  # sertifikat self-signed lokal
HADOOP = "/usr/local/hadoop/etc/hadoop/core-site.xml,/usr/local/hadoop/etc/hadoop/hdfs-site.xml"
START, END = dt.date(2023, 10, 25), dt.date(2026, 11, 1)
BASE = "https://data.cityofchicago.org/resource/"
LOCAL = "/home/lenovo/tugas-akhir-bigdata/data/landing"  # salinan lokal CSV hasil unduh, sebelum PutHDFS
EXCL = ["311 INFORMATION ONLY CALL", "Aircraft Noise Complaint"]

# (nama, resource, kolom tanggal, filter tambahan statis)
DATASETS = [
    ("crime", "ijzp-q8t2", "date", ""),
    ("crashes", "85ca-t3if", "crash_date", ""),
    ("311", "v6vf-nfxy", "created_date",
     " AND sr_type NOT IN (" + ",".join("'%s'" % t for t in EXCL) + ")"),
]


def months():
    out, d = [], START
    while d < END:
        n = dt.date(d.year + (d.month == 12), d.month % 12 + 1, 1)
        out.append((d, n))
        d = n
    return out


def call(method, path, body=None, token=None):
    req = urllib.request.Request(API + path, method=method)
    if token:
        req.add_header("Authorization", "Bearer " + token)
    data = None
    if body is not None:
        req.add_header("Content-Type", "application/json")
        data = json.dumps(body).encode()
    with urllib.request.urlopen(req, data, context=CTX) as r:
        return json.loads(r.read() or b"{}")


def token():
    d = urllib.parse.urlencode({"username": os.environ.get("NIFI_USER", "nifiadmin"), "password": os.environ["NIFI_PASS"]}).encode()
    return urllib.request.urlopen(urllib.request.Request(API + "/access/token", d), context=CTX).read().decode()


def main():
    t = token()
    root = call("GET", "/flow/process-groups/root", token=t)["processGroupFlow"]["id"]

    def proc(ptype, name, x, y, props, term=(), period=None):
        cfg = {"properties": props, "autoTerminatedRelationships": list(term)}
        if period:
            cfg["schedulingPeriod"] = period
        r = call("POST", f"/process-groups/{root}/processors", {
            "revision": {"version": 0},
            "component": {"type": ptype, "name": name, "position": {"x": x, "y": y}, "config": cfg}}, t)
        return r["id"]

    def link(a, b, rels):
        call("POST", f"/process-groups/{root}/connections", {
            "revision": {"version": 0},
            "component": {
                "source": {"id": a, "groupId": root, "type": "PROCESSOR"},
                "destination": {"id": b, "groupId": root, "type": "PROCESSOR"},
                "selectedRelationships": rels}}, t)

    # Hapus isi canvas lama (3 jalur terpisah) agar hanya ada satu flow.
    call("PUT", f"/flow/process-groups/{root}", {"id": root, "state": "STOPPED"}, t)
    for c in call("GET", f"/process-groups/{root}/connections", token=t)["connections"]:
        call("DELETE", f"/connections/{c['id']}?version={c['revision']['version']}", token=t)
    for q in call("GET", f"/process-groups/{root}/processors", token=t)["processors"]:
        call("DELETE", f"/processors/{q['id']}?version={q['revision']['version']}", token=t)

    # Satu baris per unduhan: dataset|nama|url-lengkap. Web mengirim baris berformat sama lewat ListenHTTP.
    rows = []
    for name, res, col, extra in DATASETS:
        for a, b in months():
            w = urllib.parse.quote(f"{col} >= '{a}T00:00:00' AND {col} < '{b}T00:00:00'" + extra)
            rows.append(f"{name}|{a}|{BASE}{res}.csv?%24where={w}&%24limit=2000000")
    p = "org.apache.nifi.processors."
    g = proc(p + "standard.GenerateFlowFile", "daftar dataset x bulan", 0, 0,
             {"Custom Text": "\n".join(rows), "File Size": "0B"}, period="3600 sec")
    web = proc(p + "standard.ListenHTTP", "terima link dari web", 0, 640,
               {"Base Path": "ingest", "Listening Port": "8081"})
    s = proc(p + "standard.SplitText", "1 baris per dataset-bulan", 520, 0,
             {"Line Split Count": "1", "Header Line Count": "0"}, ["original", "failure"])
    e = proc(p + "standard.ExtractText", "ambil dataset, nama, url", 1040, 0,
             {"ds": r"^([^|]+)\|([^|]+)\|(\S+)"}, ["unmatched", "failure"])
    h = proc(p + "standard.InvokeHTTP", "unduh Socrata", 0, 320,
             {"HTTP Method": "GET",
              "HTTP URL": "${ds.3}",
              "Socket Read Timeout": "30 min", "Connection Timeout": "1 min"},
             ["Original", "Failure", "Retry", "No Retry"])
    u = proc(p + "attributes.UpdateAttribute", "nama file", 520, 320,
             {"filename": "${ds.1}_${ds.2}.csv"})
    l = proc(p + "standard.PutFile", "simpan lokal dulu", 520, 640,
             {"Directory": LOCAL + "/${ds.1}", "Conflict Resolution Strategy": "replace", "Create Missing Directories": "true"},
             ["failure"])
    d = proc(p + "hadoop.PutHDFS", "PutHDFS ke /data/raw/dataset", 1040, 320,
             {"Hadoop Configuration Resources": HADOOP, "Directory": "/data/raw/${ds.1}",
              "Conflict Resolution Strategy": "replace"}, ["success", "failure"])
    link(g, s, ["success"]); link(web, s, ["success"]); link(s, e, ["splits"]); link(e, h, ["matched"])
    link(h, u, ["Response"]); link(u, l, ["success"]); link(l, d, ["success"])
    ids = {"all": [g, web, s, e, h, u, l, d]}
    print(json.dumps({"root": root, "ids": ids}))


if __name__ == "__main__":
    main()
