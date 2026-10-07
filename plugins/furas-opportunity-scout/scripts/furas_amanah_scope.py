# -*- coding: utf-8 -*-
"""Amanah-offered scope for the Furas scan (decided 28 Sep 2026).

A city now also counts every record that its MAIN amanah offers ITSELF, or through one of its
city sectors (BALADYA = the amanah, or قطاع ... / القطاع ...), even when the portal writes a
different town (أمانة محافظة جدة's ثول listings, أمانة العاصمة المقدسة's بحره) or leaves the city
blank. Records offered by a separate town municipality under the same amanah
(بلدية محافظة الخرج، بلدية محافظة رابغ، بلدية محافظة الجموم ...) stay OUT.

Run from the plugin's scripts directory:
  after furas_fetch.py, before furas_roads.py:  python3 furas_amanah_scope.py --data "$RUN/data.json"
  after furas_dashboard.py:                      python3 furas_amanah_scope.py --data "$RUN/data.json" --html "$RUN/dashboard.html"
No count floor (decided 5 Oct 2026): the total is whatever the portal has open. Every accuracy gate
(duplicates, excluded types, a city at zero, DURATION, ISO dates, coordinates) still applies.
Exit 0 = ok. Exit 2 = an accuracy gate failed: do not publish."""
import json, sys, argparse, urllib.parse, collections
sys.path.insert(0, ".")
import furas_fetch as F
from config import AMANA_TO_CITY, FIELDS, INCLUDE_TYPES, CITY_DISPLAY, normalize_ar

BAND = "outside sanity band"          # legacy count-band message from older plugin versions — never a gate

def core(bal):
    b = normalize_ar(bal or "")
    return b.startswith("امانه") or b.startswith("قطاع") or b.startswith("القطاع")

def fetch_amanah(now_iso):
    ams = ",".join("'%s'" % x for x in AMANA_TO_CITY)
    typ = ",".join("'%s'" % t for t in INCLUDE_TYPES)
    w = (f"LASTRFPSELLDATE >= DATE '{now_iso}' AND OPPORTUNITYACTIVESTATUS='Announced' "
         f"AND OPPORTUNITYTYPE IN ({typ}) AND AMANA IN ({ams})")
    out, off = [], 0
    while True:
        p = ("where=" + urllib.parse.quote(w) + "&outFields=" + ",".join(FIELDS) +
             "&returnGeometry=true&outSR=4326&orderByFields=OPPORTUNITYID"
             f"&resultOffset={off}&resultRecordCount=500")
        js = json.loads(F.q(p))
        if "error" in js: raise RuntimeError("ArcGIS error: %s" % js["error"])
        fs = js.get("features", [])
        for f in fs:
            a = dict(f["attributes"]); g = f.get("geometry") or {}
            x, y = g.get("x"), g.get("y")
            if x is None and g.get("rings"): x, y = g["rings"][0][0][:2]
            a["_lat"], a["_lon"] = y, x
            out.append(a)
        if len(fs) < 500 or off > 5000: break
        off += 500
    return out

def apply_scope(path):
    d = json.load(open(path, encoding="utf-8"))
    if d.get("amanahScope"): print("amanah scope already applied"); return 0
    base = d.get("verification") or []
    if [f for f in base if BAND not in f]:
        print("base run failed a hard gate — not applying:"); [print("  !", f) for f in base]; return 2
    have = {r["OPPORTUNITYID"] for r in d["records"]}
    ours = {normalize_ar(c) for c in AMANA_TO_CITY.values()}
    add = []
    for r in fetch_amanah(d["generatedAt"]):
        town = (r.get("CITYNAME") or "").strip()
        if r["OPPORTUNITYID"] in have or not core(r.get("BALADYA")) or normalize_ar(town) in ours:
            continue
        r["_scope"], r["_portalCity"] = "amanah", (town or None)
        r["CITYNAME"] = AMANA_TO_CITY[r["AMANA"]]
        dist = (r.get("DISTRICT") or "").strip()
        if town:                                   # say where it really is, on every view
            r["_portalDistrict"] = r.get("DISTRICT")
            r["DISTRICT"] = dist if normalize_ar(town) in normalize_ar(dist) else \
                            (f"{town} — {dist}" if dist else town)
        add.append(r)
    F.normalize_dates(add)
    if add:
        F.enrich(add); F.probe_downloads(add)
    ids = {r["OPPORTUNITYID"] for r in add}
    d["records"] = sorted(d["records"] + add,
                          key=lambda r: (str(r.get("CITYNAME") or ""), str(r.get("OPPORTUNITYID"))))
    d["candidates"] = [c for c in d.get("candidates", []) if c["OPPORTUNITYID"] not in ids]
    d["total"] = len(d["records"])
    fails = [f for f in F.verify(d["records"]) if BAND not in f]   # accuracy gates only
    d["baseVerification"], d["verification"] = base, fails
    d["amanahScope"] = {
        "rule": "city label OR offered by the city's own amanah / its city sectors",
        "added": sorted(ids),
        "byCity": dict(collections.Counter(r["CITYNAME"] for r in add)),
        "towns": dict(collections.Counter((r["_portalCity"] or "دون اسم مدينة") for r in add))}
    json.dump(d, open(path, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"amanah scope: +{len(add)} ·", ", ".join(
        f"{CITY_DISPLAY.get(k, k)} +{v}" for k, v in d["amanahScope"]["byCity"].items()) or "none",
        "· towns:", d["amanahScope"]["towns"])
    if fails:
        print("VERIFICATION FAILED:"); [print("  !", f) for f in fails]; return 2
    per = collections.Counter(CITY_DISPLAY.get(r["CITYNAME"], r["CITYNAME"]) for r in d["records"])
    print("OK ·", ", ".join(f"{k} {v}" for k, v in per.items()), f"· total {d['total']}")
    return 0

def patch_html(data_path, html_path):
    d = json.load(open(data_path, encoding="utf-8")); s = d.get("amanahScope") or {}
    h = open(html_path, encoding="utf-8").read()
    i = h.find("<li><b>المدينة:</b>"); j = h.find("</li>", i)
    if i < 0 or j < 0: print("WARNING: city methodology line not found — page text not updated"); return 0
    towns = "، ".join(f"{t} ({n})" for t, n in (s.get("towns") or {}).items())
    n = len(s.get("added") or []); unit = "فرص" if 3 <= n <= 10 else "فرصة"
    li = ("<li><b>المدينة:</b> تُحتسب الفرصة للمدينة إذا كتبت البوابة اسمها (بعد تطبيع الحروف ة/ه، أ/إ/آ/ا، ى/ي — "
          "البوابة تخزّن «مكه المكرمه» و«المدينه المنوره» بالهاء)، <b>أو</b> إذا طرحتها أمانة المدينة نفسها أو أحد "
          "قطاعاتها ولو كتبت البوابة اسم بلدة أخرى أو تركت المدينة فارغة؛ وتظهر البلدة في عمود الموقع "
          "(مثل «ثول — الكورنيش»). "
          + (f"أضافت هذه القاعدة {n} {unit} في هذه الجولة: {towns}. " if n else "")
          + "ما تطرحه البلديات الفرعية للمحافظات (الخرج، رابغ، الجموم وغيرها) خارج النطاق.")
    open(html_path, "w", encoding="utf-8").write(h[:i] + li + h[j:])
    print("dashboard methodology line updated"); return 0

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True); ap.add_argument("--html")
    a = ap.parse_args()
    sys.exit(patch_html(a.data, a.html) if a.html else apply_scope(a.data))
