# -*- coding: utf-8 -*-
"""Turn Chrome-fallback chunks into srem.json and run the same gates as srem_fetch.py."""
import argparse, json, sys
from config import JEDDAH_CITY_CODE, normalize_ar

ap = argparse.ArgumentParser()
ap.add_argument("--parts-dir", required=True, help="folder of chunk files 000.txt, 001.txt … written verbatim")
ap.add_argument("--sums", required=True, help="JSON array from window.__srem.sums")
ap.add_argument("--out", required=True)
a = ap.parse_args()
import os
files = sorted(f for f in os.listdir(a.parts_dir) if f.endswith(".txt"))
sums = json.loads(open(a.sums).read())
parts = [open(os.path.join(a.parts_dir, f), encoding="utf-8").read() for f in files]
if len(parts) != len(sums):
    print(f"VERIFY FAIL: {len(parts)} chunk files but {len(sums)} checksums", file=sys.stderr); sys.exit(2)
bad = []
for i, (c, want) in enumerate(zip(parts, sums)):
    h = 0
    for k, ch in enumerate(c):
        h = (h + (k + 1) * ord(ch)) % 1000000007
    if h != want:
        bad.append(i)
if bad:
    print(f"VERIFY FAIL: chunk(s) {bad} differ from what Chrome produced — re-read and rewrite them", file=sys.stderr)
    sys.exit(2)
out = json.loads("".join(parts))
if out.get("v") == 1:
    # compact hand-over format (srem_chrome.js): expand to the srem_fetch.py shape
    c = out
    t = c["t"]
    out = {"source": "البورصة العقارية", "fetched_at": c.get("at"), "period": "W", "city_code": JEDDAH_CITY_CODE,
           "via": "chrome", "city_attempts": c.get("ca"),
           "total": dict(zip(["Count", "TotalPrices", "TotalAreas", "AveragePrice", "MinPrice", "MaxPrice", "BestBid", "BestAsk"], t)),
           "daily": [{"AggregationDate": d[0] + "T00:00:00", "AreaSerial": d[1], "TotalCount": d[2], "TotalPrice": d[3],
                      "TotalArea": d[4], "AveragePrice": d[5]} for d in c["d"]],
           "ticker": [dict(zip(["Id", "TransAmount", "TransDate", "TransArea", "CityName", "NHName", "Plan", "LandNumber", "UnitType"], k))
                      for k in c["k"]],
           "districts": [{"code": r[0], "name": r[1], "count": r[2], "value": r[3], "area": r[4],
                          "avg_ppm": round(r[3] / r[4]) if r[4] else None} for r in c["r"]] +
                        [{"code": z, "name": "", "count": 0, "value": 0, "area": 0, "avg_ppm": None} for z in c["z"]],
           "gazetteer": {str(r[0]): r[1] for r in c["r"]} | {str(z): "" for z in c["z"]},
           "district_failures": [{"code": f} for f in c.get("f", [])]}
    for tk in out["ticker"]:
        if tk.get("TransAmount") and tk.get("TransArea"):
            tk["PricePerMeterSquare"] = tk["TransAmount"] / tk["TransArea"]
if out.get("error"):
    print("VERIFY FAIL:", out["error"], file=sys.stderr); sys.exit(2)
total, stats = out.get("total") or {}, out.get("daily") or []
days = sorted(s["AggregationDate"][:10] for s in stats)
out["window"] = {"from": days[0] if days else None, "to": days[-1] if days else None, "days": len(days)}
sc, sp = sum(s.get("TotalCount") or 0 for s in stats), sum(s.get("TotalPrice") or 0 for s in stats)
out["gates"] = [
    {"gate": "daily rows sum to weekly total", "ok": sc == total.get("Count") and abs(sp - (total.get("TotalPrices") or 0)) <= max(1, 0.001 * sp),
     "detail": f"count {sc} vs {total.get('Count')}"},
    {"gate": "all rows are Jeddah", "ok": all(s.get("AreaSerial") == JEDDAH_CITY_CODE for s in stats) and
     all(normalize_ar(t.get("CityName")) == normalize_ar("جدة") for t in out.get("ticker") or []), "detail": ""}]
dsum = sum(d["count"] for d in out.get("districts", []))
out["district_coverage"] = dsum / total["Count"] if total.get("Count") else None
out["gates"].append({"gate": "district sum ≤ city total", "ok": dsum <= (total.get("Count") or 0),
                     "detail": f"{dsum} of {total.get('Count')} deals mapped to districts"})
json.dump(out, open(a.out, "w"), ensure_ascii=False, indent=1)
for g in out["gates"]:
    print(("PASS " if g["ok"] else "FAIL ") + g["gate"] + " — " + g["detail"])
sys.exit(0 if all(g["ok"] for g in out["gates"]) else 2)
