# -*- coding: utf-8 -*-
"""data.json -> a small diff baseline for the project.

Each scheduled run starts in a fresh container, so the previous run's data.json is gone.
The baseline therefore lives in the project doc claude/furas_run_snapshot_latest.json.
A full data.json is ~270 KB, most of it enrichment the comparator never reads; this keeps
only what furas_diff.py actually compares, which is small enough to store every week.
"""
import json, argparse

# exactly what furas_diff.py reads: identity, the four compared fields, and labels for output
KEEP = ("OPPORTUNITYID", "OPPORTUNITYDESCRIPTION", "CITYNAME",
        "LASTRFPSELLDATE", "RFPPRICE", "DURATION", "TOTALSPACEINMETERS")

ap = argparse.ArgumentParser()
ap.add_argument("--data", default="data.json")
ap.add_argument("--out", default="snapshot.json")
a = ap.parse_args()

d = json.load(open(a.data, encoding="utf-8"))
if d.get("verification"):
    raise SystemExit("refusing to snapshot a run that failed verification")

out = {"asOf": d["asOf"], "total": d["total"],
       "records": [{k: r.get(k) for k in KEEP} for r in d["records"]]}
json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))

import os
print(f"wrote {a.out} · {len(out['records'])} records · {os.path.getsize(a.out):,} bytes")
