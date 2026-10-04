# -*- coding: utf-8 -*-
import json, argparse, datetime, math, sys, re

ap = argparse.ArgumentParser()
ap.add_argument("--data", default="data.json")
ap.add_argument("--out",  default="dashboard.html")
ap.add_argument("--standalone", action="store_true",
                help="emit a complete HTML document, for opening as a local file "
                     "(the Artifact tool supplies its own skeleton, a local file has none)")
ap.add_argument("--title", default=None, help="override the <title>; standalone only")
A = ap.parse_args()
PAY = json.load(open(A.data, encoding="utf-8"))
if PAY.get("verification"):
    print("Refusing to build: the scan did not pass verification:")
    for f in PAY["verification"]: print("  !", f)
    sys.exit(2)
ASOF = PAY["asOf"]
ORDER = ["الرياض","جدة","مكه المكرمه","المدينه المنوره"]
LABEL = {"الرياض":"الرياض","جدة":"جدة","مكه المكرمه":"مكة المكرمة","المدينه المنوره":"المدينة المنورة"}

def s(v): return (str(v).strip() if v is not None else "")
def num(v):
    try: return float(str(v).replace(",", "").strip())
    except: return None

def tier(a):
    if a is None or a <= 0: return 0
    if a < 100:      return 1
    if a < 1000:     return 2
    if a < 10000:    return 3
    if a < 100000:   return 4
    return 5
TIER_LBL = {0:"غير مذكور",1:"كشك",2:"صغير",3:"متوسط",4:"كبير",5:"ضخم"}

recs = []
for r in PAY["records"]:
    ref = s(r.get("OPPORTUNITYID"))
    amana, ent = s(r.get("AMANA")), s(r.get("ENTITIESNAME"))
    a = num(r.get("TOTALSPACEINMETERS")); p = num(r.get("RFPPRICE"))
    months = int(num(r.get("DURATION")) or 0)
    env = s(r.get("ENVELOPESOPENDATE"))[:10]
    d = s(r.get("DISTRICT")); st = s(r.get("STREET"))
    recs.append({
        "ref": ref, "title": s(r.get("OPPORTUNITYDESCRIPTION")),
        "city": s(r.get("CITYNAME")), "cityLabel": LABEL.get(s(r.get("CITYNAME")), s(r.get("CITYNAME"))),
        "isAmanah": bool(amana), "authority": amana or ent or None,
        "baladya": s(r.get("BALADYA")) or None, "district": d or None, "street": st or None,
        "loc": " · ".join([x for x in (d, st) if x]) or None,
        "months": months, "years": round(months/12, 1),
        "area": a if (a and a > 0) else None, "tier": tier(a),
        "price": p if (p and p > 0) else None,
        "deadline": s(r.get("LASTRFPSELLDATE"))[:10],
        "envelopes": (None if (not env or env.startswith("1970")) else env),
        "activity": s(r.get("ACTIVITYTYPE")) or None, "sub": s(r.get("SUBACTIVITYTYPE")) or None,
        "lat": r.get("_lat"), "lon": r.get("_lon"),
        "docs": [{"name": x["name"].strip(), "url": x["url"],
                  "dl": x.get("dl")} for x in (r.get("_docs") or [])],
        "kurasa": any("كراس" in (x.get("name") or "") for x in (r.get("_docs") or [])),
        "aqd":    any("عقد"  in (x.get("name") or "") for x in (r.get("_docs") or [])),
    })
recs.sort(key=lambda x: (ORDER.index(x["city"]), x["deadline"], x["ref"]))

asof = datetime.date.fromisoformat(ASOF)
weeks, wk = [], {}
for r in recs:
    try: dd = datetime.date.fromisoformat(r["deadline"])
    except: continue
    off = max(0, (dd - asof).days // 7)
    wk[off] = wk.get(off, 0) + 1
maxw = max(wk) if wk else 0
for i in range(maxw + 1):
    ws = asof + datetime.timedelta(days=i*7)
    weeks.append({"i": i, "n": wk.get(i, 0), "from": ws.isoformat(),
                  "to": (ws + datetime.timedelta(days=6)).isoformat()})

stats = []
for c in ORDER:
    g = [x for x in recs if x["city"] == c]
    stats.append({"city": c, "label": LABEL[c], "n": len(g),
                  "amanah": sum(1 for x in g if x["isAmanah"]),
                  "partner": sum(1 for x in g if not x["isAmanah"]),
                  "urgent": sum(1 for x in g if 0 <= (datetime.date.fromisoformat(x["deadline"]) - asof).days <= 14)})

# --- geography for the map view: per-city extents and district clusters ---
geo, clusters = {}, []
ROADS = PAY.get("roads") or {}
for c in ORDER:
    pts = [(r["lat"], r["lon"]) for r in recs if r["city"] == c and r["lat"] is not None]
    if not pts: continue
    la = [p[0] for p in pts]; lo = [p[1] for p in pts]
    minLat, maxLat, minLon, maxLon = min(la), max(la), min(lo), max(lo)
    # pad, then square the frame in TRUE ground distance so the city is not stretched:
    # a degree of longitude is only cos(lat) as wide as a degree of latitude.
    cosf = math.cos(math.radians((minLat + maxLat) / 2))
    padA = max((maxLat - minLat) * 0.10, 0.012)
    padO = max((maxLon - minLon) * 0.10, 0.012)
    minLat -= padA; maxLat += padA; minLon -= padO; maxLon += padO
    hKm = (maxLat - minLat) * 110.57
    wKm = (maxLon - minLon) * 111.32 * cosf
    if wKm > hKm:                      # grow the short axis so 1 px = 1 px on the ground
        grow = (wKm - hKm) / 110.57 / 2
        minLat -= grow; maxLat += grow
    else:
        grow = (hKm - wKm) / (111.32 * cosf) / 2
        minLon -= grow; maxLon += grow
    geo[c] = {"minLat": minLat, "maxLat": maxLat, "minLon": minLon, "maxLon": maxLon,
              "n": len(pts), "cos": cosf,
              "widthKm": round((maxLon - minLon) * 111.32 * cosf, 1)}
    # furas_roads.py computed the same frame and rendered the road image INTO it; adopt that
    # frame verbatim so the roads and the dots cannot drift apart by a rounding step.
    rd = ROADS.get(c)
    if rd:
        for k in ("minLat", "maxLat", "minLon", "maxLon", "widthKm"):
            if k in rd: geo[c][k] = rd[k]
        geo[c]["png"] = rd.get("png")
    byd = {}
    for r in recs:
        if r["city"] != c or not r["district"] or r["lat"] is None: continue
        byd.setdefault(r["district"], []).append(r)
    for d, rs in byd.items():
        lats = [x["lat"] for x in rs]; lons = [x["lon"] for x in rs]
        clusters.append({"city": c, "cityLabel": LABEL.get(c, c), "district": d, "n": len(rs),
                         "area": sum(x["area"] or 0 for x in rs),
                         "withArea": sum(1 for x in rs if x["area"]),
                         "lat": sum(lats) / len(lats), "lon": sum(lons) / len(lons),
                         "spanKm": round(max((max(lats)-min(lats))*110.57,
                                             (max(lons)-min(lons))*111.32*cosf), 2),
                         "minLat": min(lats), "maxLat": max(lats),
                         "minLon": min(lons), "maxLon": max(lons),
                         "soonest": min(x["deadline"] for x in rs),
                         "refs": [x["ref"] for x in rs]})
clusters.sort(key=lambda x: (-x["n"], -x["area"]))

acts = {}
for r in recs:
    if r["activity"]: acts[r["activity"]] = acts.get(r["activity"], 0) + 1
activities = sorted(acts.items(), key=lambda kv: (-kv[1], kv[0]))

payload = {"asOf": ASOF, "total": len(recs), "cities": stats, "records": recs, "weeks": weeks,
           "totalAmanah": sum(s_["amanah"] for s_ in stats),
           "totalPartner": sum(s_["partner"] for s_ in stats),
           "totalUrgent":  sum(s_["urgent"]  for s_ in stats),
           "areaSum": sum(x["area"] or 0 for x in recs),
           "medYears": sorted(x["years"] for x in recs)[len(recs)//2],
           "withDocs": sum(1 for x in recs if x["docs"]),
           "national": PAY.get("nationalOpenInvestment") or 1887,
           "radiusKm": PAY.get("candidateRadiusKm"),
           "blank": PAY.get("blankCity") or 0,
           "geo": geo, "clusters": clusters,
           "activities": [{"name": k, "n": v} for k, v in activities],
           "roadsSource": PAY.get("roadsSource"),
           "review": [{
               "ref": s(c.get("OPPORTUNITYID")),
               "title": s(c.get("OPPORTUNITYDESCRIPTION")),
               "near": LABEL.get(c.get("_nnCity"), c.get("_nnCity")),
               "km": c.get("_nnKm"),
               "amanah": s(c.get("AMANA")) or s(c.get("ENTITIESNAME")) or None,
               "agrees": bool(c.get("_amanahCity")) and c.get("_amanahCity") == c.get("_nnCity"),
               "deadline": s(c.get("LASTRFPSELLDATE"))[:10],
               "months": int(num(c.get("DURATION")) or 0),
               "area": (num(c.get("TOTALSPACEINMETERS")) or None),
               "lat": c.get("_lat"), "lon": c.get("_lon"),
           } for c in PAY.get("candidates", [])]}

CSS  = r"""<title>مرصد فرص المدن الأربع</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Arabic:wght@300;400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap">
<style>
:root{
  --ground:#F6F8F7; --surface:#FFFFFF; --raised:#EEF3F1; --sunken:#E7EDEA;
  --ink:#101815; --ink-2:#3D4C47; --ink-3:#6E7C77;
  --line:#DEE5E2; --line-2:#C6D1CD;
  --cat-a:#12795B; --cat-b:#9A4FBF;
  --cat-a-bg:#E3F0EA; --cat-b-bg:#F1E7F8;
  --warn:#B0561F; --warn-bg:#FBEDE2; --crit:#A32C2C; --crit-bg:#FAE7E7;
  --focus:#12795B;
  --sh-1:0 1px 2px rgba(16,24,21,.05);
  --sh-2:0 1px 2px rgba(16,24,21,.05),0 10px 28px -18px rgba(16,24,21,.30);
  --u1:#E4B197; --u2:#D38358; --u3:#BD5711; --u4:#953200;
  --r:12px; --r-s:8px; --ctrl-h:52px;
}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --ground:#0E1412; --surface:#161D1A; --raised:#1D2622; --sunken:#232E29;
  --ink:#E8EEEB; --ink-2:#AFBDB7; --ink-3:#7F8E88;
  --u1:#6E3F27; --u2:#A45120; --u3:#D36B2D; --u4:#F49360;
  --line:#26302C; --line-2:#35423D;
  --cat-a:#2E9970; --cat-b:#9E68D0;
  --cat-a-bg:#15281F; --cat-b-bg:#241A2E;
  --warn:#D98C55; --warn-bg:#2B1D12; --crit:#DE7070; --crit-bg:#2C1616;
  --focus:#2E9970;
  --sh-1:0 1px 2px rgba(0,0,0,.35);
  --sh-2:0 1px 2px rgba(0,0,0,.35),0 10px 28px -18px rgba(0,0,0,.8);
}}
:root[data-theme="dark"]{
  --ground:#0E1412; --surface:#161D1A; --raised:#1D2622; --sunken:#232E29;
  --ink:#E8EEEB; --ink-2:#AFBDB7; --ink-3:#7F8E88;
  --u1:#6E3F27; --u2:#A45120; --u3:#D36B2D; --u4:#F49360;
  --line:#26302C; --line-2:#35423D;
  --cat-a:#2E9970; --cat-b:#9E68D0;
  --cat-a-bg:#15281F; --cat-b-bg:#241A2E;
  --warn:#D98C55; --warn-bg:#2B1D12; --crit:#DE7070; --crit-bg:#2C1616;
  --focus:#2E9970;
  --sh-1:0 1px 2px rgba(0,0,0,.35);
  --sh-2:0 1px 2px rgba(0,0,0,.35),0 10px 28px -18px rgba(0,0,0,.8);
}
*{box-sizing:border-box}
body{margin:0;direction:rtl;background:var(--ground);color:var(--ink);
 font-family:"IBM Plex Sans Arabic","Segoe UI",system-ui,sans-serif;font-size:15px;line-height:1.6;
 -webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility}
.mono{font-family:"IBM Plex Mono",ui-monospace,monospace;font-variant-numeric:tabular-nums;letter-spacing:-.01em}
.wrap{max-width:1500px;margin:0 auto;padding:26px 22px 80px}
a{color:inherit}
:focus-visible{outline:2px solid var(--focus);outline-offset:2px;border-radius:4px}

/* header */
.top{display:flex;flex-wrap:wrap;gap:16px 24px;align-items:flex-end;justify-content:space-between;margin-bottom:22px}
h1{margin:0;font-size:clamp(1.35rem,2.6vw,1.9rem);font-weight:600;letter-spacing:-.02em;text-wrap:balance;line-height:1.25}
.sub{margin:7px 0 0;color:var(--ink-3);font-size:.87rem}
.gate{display:inline-flex;align-items:center;gap:8px;background:var(--cat-a-bg);color:var(--cat-a);
 border:1px solid color-mix(in srgb,var(--cat-a) 26%,transparent);border-radius:999px;padding:7px 14px;
 font-size:.8rem;font-weight:500}
.gate .dot{width:7px;height:7px;border-radius:50%;background:var(--cat-a);flex:none}
.stale{display:none;margin-bottom:18px;padding:12px 16px;border-radius:var(--r-s);background:var(--warn-bg);
 color:var(--warn);border:1px solid color-mix(in srgb,var(--warn) 30%,transparent);font-size:.87rem}
.stale.on{display:block}

/* KPI */
.kpis{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin-bottom:12px}
.kpis.cities{grid-template-columns:repeat(4,minmax(0,1fr))}
.kpi{background:var(--surface);border:1px solid var(--line);border-radius:var(--r);
 padding:15px 17px;box-shadow:var(--sh-1);position:relative;overflow:hidden}
.kpi .lbl{font-size:.76rem;color:var(--ink-3);letter-spacing:.015em;margin-bottom:7px;font-weight:500}
.kpi .val{font-size:2rem;font-weight:600;line-height:1;letter-spacing:-.035em}
.kpi .val small{font-size:.8rem;font-weight:500;color:var(--ink-3);letter-spacing:0;margin-inline-start:4px}
.kpi.city .val{font-size:1.65rem}
.kpi .split{margin-top:11px;padding-top:9px;border-top:1px solid var(--line);
 font-size:.74rem;color:var(--ink-2);display:flex;gap:7px 14px;flex-wrap:wrap}
.kpi .split span{display:inline-flex;align-items:center;white-space:nowrap}
.kpi .split b{font-weight:600;margin-inline-start:4px;font-variant-numeric:tabular-nums}
.kpi.alert{background:var(--warn-bg);border-color:color-mix(in srgb,var(--warn) 30%,transparent)}
.kpi.alert .val,.kpi.alert .lbl{color:var(--warn)}
.kpi.alert .split{border-top-color:color-mix(in srgb,var(--warn) 22%,transparent);color:var(--warn)}
.sw{display:inline-block;width:9px;height:9px;border-radius:3px;margin-inline-end:6px;flex:none}
.sw-a{background:var(--cat-a)} .sw-b{background:var(--cat-b)}

/* timeline */
.panel{background:var(--surface);border:1px solid var(--line);border-radius:var(--r);
 padding:16px 18px 12px;box-shadow:var(--sh-1);margin-bottom:16px}
.panel h2{margin:0 0 2px;font-size:.95rem;font-weight:600;letter-spacing:-.01em}
.panel .hint{margin:0 0 14px;font-size:.78rem;color:var(--ink-3)}
.tl{display:flex;align-items:flex-end;gap:5px;height:96px;padding-top:16px;position:relative}
.tl::before{content:"";position:absolute;inset-inline:0;bottom:0;height:1px;background:var(--line-2)}
.tlc{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:flex-end;height:100%;
 gap:5px;cursor:default;min-width:0}
.tlb{width:100%;background:var(--cat-a);border-radius:4px 4px 0 0;min-height:2px;
 transition:opacity .12s;opacity:.92}
.tlc:hover .tlb,.tlc:focus-visible .tlb{opacity:1}
.tlc.soon .tlb{background:var(--warn)}
.tlc .n{font-size:.72rem;font-weight:600;color:var(--ink-2);line-height:1}
.tlx{display:flex;gap:5px;margin-top:7px}
.tlx span{flex:1;text-align:center;font-size:.68rem;color:var(--ink-3);min-width:0;
 white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.tip{position:fixed;z-index:60;pointer-events:none;background:var(--ink);color:var(--ground);
 padding:7px 11px;border-radius:7px;font-size:.78rem;line-height:1.45;box-shadow:var(--sh-2);
 opacity:0;transition:opacity .1s;max-width:230px}
.tip.on{opacity:1}
.tip b{font-weight:600}

/* controls */
.controls{position:sticky;top:0;z-index:30;background:color-mix(in srgb,var(--ground) 92%,transparent);
 backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);
 display:flex;flex-wrap:wrap;gap:9px;align-items:center;
 padding:11px 0;margin-bottom:14px;border-bottom:1px solid var(--line)}
input[type=search],select,button{font-family:inherit;font-size:.87rem;color:var(--ink);
 background:var(--surface);border:1px solid var(--line-2);border-radius:var(--r-s);padding:8px 12px}
input[type=search]{flex:1 1 240px;min-width:170px}
select{cursor:pointer;padding-inline-end:26px}
button.reset{cursor:pointer;color:var(--ink-2)}
button.reset:hover{border-color:var(--focus);color:var(--focus)}
button.reset[hidden]{display:none}
.count{margin-inline-start:auto;font-size:.82rem;color:var(--ink-3);white-space:nowrap}
.count b{color:var(--ink);font-weight:600}

/* city + table */
.city{margin-bottom:26px}
.chead{display:flex;align-items:baseline;gap:11px;margin-bottom:9px;flex-wrap:wrap}
.chead h2{margin:0;font-size:1.1rem;font-weight:600;letter-spacing:-.01em}
.pill{font-size:.74rem;padding:3px 9px;border-radius:999px;background:var(--raised);color:var(--ink-2);border:1px solid var(--line)}
.pill.warn{background:var(--warn-bg);color:var(--warn);border-color:color-mix(in srgb,var(--warn) 26%,transparent)}
.tw{overflow-x:auto;background:var(--surface);border:1px solid var(--line);border-radius:var(--r);box-shadow:var(--sh-1)}
table{width:100%;border-collapse:collapse;font-size:.87rem;min-width:1150px}
thead th{background:var(--raised);color:var(--ink-2);font-weight:500;
 font-size:.76rem;letter-spacing:.02em;text-align:right;padding:9px 12px;
 border-bottom:1px solid var(--line-2);white-space:nowrap}
tbody td{padding:11px 12px;border-bottom:1px solid var(--line);vertical-align:top}
tbody tr.row{cursor:pointer;transition:background .1s;scroll-margin-top:calc(var(--ctrl-h) + 12px)}
tbody tr.row:hover{background:var(--raised)}
tbody tr.row.open{background:var(--raised)}
tbody tr.row:last-of-type td{border-bottom:none}
td.st{width:4px;min-width:4px;max-width:4px;padding:0;border-bottom:1px solid var(--line);
 background-clip:padding-box}
thead th:first-child{width:4px;min-width:4px;max-width:4px;padding:0}
tr.row.u14 td.st{background:var(--warn)} tr.row.u3 td.st{background:var(--crit)}
.ref{font-size:.8rem;white-space:nowrap;color:var(--ink-2)}
.ttl{max-width:360px;line-height:1.45}
.act{max-width:150px;line-height:1.35}
.act .a1{font-size:.82rem}
.act .a2{font-size:.72rem;color:var(--ink-3);margin-top:2px}
.ttl .cl{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.auth{font-size:.78rem;color:var(--ink-3);margin-top:3px;max-width:200px}
.chip{display:inline-flex;align-items:center;gap:5px;font-size:.71rem;padding:2px 8px;border-radius:999px;
 border:1px solid transparent;white-space:nowrap;font-weight:500;margin-top:3px}
.chip::before{content:"";width:6px;height:6px;border-radius:2px;flex:none}
.chip.a{background:var(--cat-a-bg);color:var(--cat-a);border-color:color-mix(in srgb,var(--cat-a) 24%,transparent)}
.chip.a::before{background:var(--cat-a)}
.chip.b{background:var(--cat-b-bg);color:var(--cat-b);border-color:color-mix(in srgb,var(--cat-b) 24%,transparent)}
.chip.b::before{background:var(--cat-b)}
.nm{color:var(--ink-3);font-size:.83rem}
.term b{font-weight:600;white-space:nowrap}
.term span{display:block;font-size:.72rem;color:var(--ink-3);margin-top:1px;white-space:nowrap}
.areac{white-space:nowrap;text-align:left;direction:ltr}
.areac .u{color:var(--ink-3);font-size:.8em;margin-inline-start:5px}
.areav{font-weight:500}
.dl{white-space:nowrap}
.days{display:block;font-size:.73rem;margin-top:2px;white-space:nowrap}
.days.w{color:var(--warn);font-weight:500} .days.c{color:var(--crit);font-weight:600}
.days.g{color:var(--ink-3)}

/* detail */
tr.det td{background:var(--sunken);padding:0}
tr.det.hide{display:none}
.db{padding:17px 20px;border-inline-start:3px solid var(--cat-a)}
.db .full{margin:0 0 15px;font-size:.94rem;line-height:1.65;max-width:80ch}
.dg{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:13px 24px;margin:0}
.dg dt{font-size:.73rem;color:var(--ink-3);margin-bottom:2px}
.dg dd{margin:0;font-size:.87rem;word-break:break-word}
.acts{display:flex;flex-wrap:wrap;gap:8px;margin-top:16px;padding-top:14px;border-top:1px solid var(--line)}
.btn{display:inline-flex;align-items:center;gap:6px;font-size:.82rem;text-decoration:none;padding:7px 13px;
 border-radius:var(--r-s);border:1px solid var(--line-2);color:var(--ink-2);background:var(--surface);
 transition:border-color .12s,color .12s}
.btn:hover{border-color:var(--cat-a);color:var(--cat-a)}
.btn.p{background:var(--cat-a);color:#fff;border-color:var(--cat-a);font-weight:600;
 box-shadow:0 1px 2px rgba(0,0,0,.12)}
.btn.p:hover{background:color-mix(in srgb,var(--cat-a) 86%,#000);border-color:color-mix(in srgb,var(--cat-a) 86%,#000);color:#fff}
.btn.doc{background:var(--cat-a-bg);color:var(--cat-a);border-color:color-mix(in srgb,var(--cat-a) 30%,transparent);font-weight:500}
.btn.doc:hover{border-color:var(--cat-a);background:color-mix(in srgb,var(--cat-a) 16%,transparent)}
.docs{flex:1 1 100%;font-size:.78rem;color:var(--ink-3);display:flex;flex-wrap:wrap;align-items:center;gap:6px;margin-top:3px}
.dchip{background:var(--surface);border:1px solid var(--line);border-radius:6px;padding:2px 8px;color:var(--ink-2);font-size:.76rem}
.empty{padding:30px;text-align:center;color:var(--ink-3);font-size:.9rem}

.views{display:flex;gap:3px;margin:22px 0 0;padding:3px;background:var(--sunken);
  border-radius:var(--r-s);width:fit-content;max-width:100%;overflow-x:auto}
.views button{font:inherit;font-size:.84rem;font-weight:600;white-space:nowrap;cursor:pointer;
  padding:7px 15px;border:0;border-radius:6px;background:none;color:var(--ink-2)}
.views button:hover{color:var(--ink)}
.views button[aria-selected=true]{background:var(--surface);color:var(--ink);box-shadow:var(--sh-1)}
.views button:focus-visible{outline:2px solid var(--focus);outline-offset:1px}
.vpane{margin-top:20px;scroll-margin-top:calc(var(--ctrl-h) + 26px)}
.vh{margin:0 0 4px;font-size:1.02rem;font-weight:600}
.vs{margin:0 0 18px;font-size:.85rem;color:var(--ink-2);line-height:1.65;max-width:74ch}
.card{background:var(--surface);border:1px solid var(--line);border-radius:var(--r);
  padding:16px 18px;margin-bottom:14px}
.lgd{display:flex;flex-wrap:wrap;gap:12px;align-items:center;margin:12px 0 4px;
  font-size:.76rem;color:var(--ink-2)}
.lgd i{display:inline-block;width:11px;height:11px;border-radius:50%;margin-inline-end:5px;
  vertical-align:-1px;border:1px solid color-mix(in srgb,var(--ink) 18%,transparent)}
.sc{overflow-x:auto}
.sc svg{display:block;height:auto}
.roadimg{opacity:.9}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]) .roadimg{
  filter:invert(1) brightness(1.15);opacity:.8}}
:root[data-theme="dark"] .roadimg{filter:invert(1) brightness(1.15);opacity:.8}
/* funnel */
.fstep{display:grid;grid-template-columns:minmax(120px,1.1fr) 1fr auto;gap:12px;align-items:center;
  padding:9px 0;border-bottom:1px solid var(--line)}
.fstep:last-child{border-bottom:0}
.fname{font-size:.85rem;color:var(--ink)}
.fname small{display:block;color:var(--ink-3);font-size:.72rem;margin-top:2px}
.fbar{height:16px;background:var(--sunken);border-radius:4px;overflow:hidden}
.fbar span{display:block;height:100%;background:var(--cat-a);border-radius:4px}
.fnum{font-variant-numeric:tabular-nums;font-weight:600;font-size:.9rem;white-space:nowrap}
.fnum b{color:var(--ink)} .fnum s{color:var(--ink-3);text-decoration:none;font-weight:400;font-size:.78rem}
.short{width:100%;border-collapse:collapse;font-size:.82rem;margin-top:4px}
.short th{text-align:start;font-weight:600;color:var(--ink-2);padding:7px 8px;
  border-bottom:1px solid var(--line);white-space:nowrap}
.short td{padding:8px;border-bottom:1px solid var(--line);vertical-align:top}
.short tr:last-child td{border-bottom:0}
.pill{font-size:.7rem;padding:1px 7px;border-radius:999px;white-space:nowrap;
  background:var(--cat-a-bg);color:var(--cat-a)}
.pill.no{background:var(--sunken);color:var(--ink-3)}
tr.row.flash>td{animation:fl 1.6s ease-out}
@keyframes fl{0%,42%{background:var(--cat-a-bg)}100%{background:transparent}}
[data-ref]{cursor:pointer}
svg [data-ref]:hover{stroke:var(--ink);stroke-width:2}
.short tr[data-ref]:hover td{background:var(--raised)}
.mgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(340px,100%),1fr));gap:14px}
.mcell{min-width:0;background:var(--surface);border:1px solid var(--line);border-radius:var(--r);padding:12px}
.mhead{display:flex;align-items:baseline;justify-content:space-between;gap:8px;flex-wrap:wrap}
.mhead h4{margin:0 0 2px;font-size:.9rem;font-weight:600}
.mhead .lnk{font-size:.72rem;white-space:nowrap}
.mact{display:inline-flex;align-items:center;gap:8px;flex-wrap:wrap}
.mact .chipbtn{font:inherit;font-size:.72rem;cursor:pointer;padding:3px 9px;border-radius:999px;
  border:1px solid color-mix(in srgb,var(--cat-a) 32%,transparent);background:var(--surface);
  color:var(--cat-a);white-space:nowrap}
.mact .chipbtn:hover{background:var(--cat-a-bg)}
.mcell p{margin:0 0 8px;font-size:.73rem;color:var(--ink-3)}
.cl2{width:100%;border-collapse:collapse;font-size:.82rem}
.cl2 th{text-align:start;font-weight:600;color:var(--ink-2);padding:6px 8px;border-bottom:1px solid var(--line);white-space:nowrap}
.cl2 td{padding:7px 8px;border-bottom:1px solid var(--line)}
.cl2 td:first-child,.cl2 td:nth-child(2){white-space:nowrap}
.cl2 tr:last-child td{border-bottom:0}
.dchip-live{display:inline-flex;align-items:center;gap:8px;font-size:.78rem;
  background:var(--cat-a-bg);color:var(--cat-a);border:1px solid color-mix(in srgb,var(--cat-a) 30%,transparent);
  border-radius:999px;padding:4px 6px 4px 12px}
.dchip-live[hidden]{display:none}
.dchip-live button,.dchip-live .chipbtn{font:inherit;font-size:.74rem;line-height:1;cursor:pointer;
  padding:4px 9px;border:1px solid color-mix(in srgb,var(--cat-a) 32%,transparent);
  background:var(--surface);color:var(--cat-a);border-radius:999px;text-decoration:none;
  white-space:nowrap}
.dchip-live #dclear{font-size:1rem;padding:0 7px;border:0;background:none}
.dchip-live .chipnote{font-size:.72rem;color:var(--ink-3)}
.dchip-live button:hover{background:color-mix(in srgb,var(--cat-a) 18%,transparent)}
[data-dist]{cursor:pointer}
.cl2 tr[data-dist]:hover td{background:var(--raised)}
.crow2{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;flex-wrap:wrap;margin-bottom:10px}
.crow2 input{font:inherit;font-size:.8rem;padding:6px 11px;border-radius:var(--r-s);
  border:1px solid var(--line-2);background:var(--surface);color:var(--ink);min-width:170px}
svg text[data-dist]{cursor:pointer}
svg text[data-dist]:hover{fill:var(--cat-a)}
/* multi-select: a button that opens a checkbox list. A <select multiple> is unusable on a
   phone and hides its own state; this shows the chosen count on the button and keeps the
   control bar one row tall. */
.ms{position:relative}
.ms>button{font:inherit;font-size:.87rem;cursor:pointer;padding:8px 12px;display:inline-flex;
  align-items:center;gap:7px;background:var(--surface);border:1px solid var(--line-2);
  border-radius:var(--r-s);color:var(--ink);white-space:nowrap;max-width:230px}
.ms>button .cnt{font-size:.72rem;font-weight:600;background:var(--cat-a-bg);color:var(--cat-a);
  border-radius:999px;padding:1px 7px}
.ms>button .car{color:var(--ink-3);font-size:.7rem}
.ms>button[aria-expanded=true]{border-color:var(--focus)}
.ms>button .lbl{overflow:hidden;text-overflow:ellipsis}
.mspanel{position:absolute;z-index:45;top:calc(100% + 5px);inset-inline-start:0;min-width:250px;
  max-width:330px;max-height:340px;overflow-y:auto;background:var(--surface);
  border:1px solid var(--line-2);border-radius:var(--r-s);box-shadow:var(--sh-2);padding:7px}
.mspanel[hidden]{display:none}
.mspanel .tools{display:flex;gap:6px;padding:3px 5px 7px;border-bottom:1px solid var(--line);
  margin-bottom:5px}
.mspanel .tools button{font:inherit;font-size:.72rem;cursor:pointer;padding:3px 9px;
  border-radius:999px;border:1px solid var(--line);background:var(--ground);color:var(--ink-2)}
.mspanel .tools button:hover{background:var(--raised);color:var(--ink)}
.mspanel label{display:flex;align-items:flex-start;gap:8px;padding:6px 7px;border-radius:6px;
  font-size:.83rem;cursor:pointer;line-height:1.4}
.mspanel label:hover{background:var(--raised)}
.mspanel input{margin:2px 0 0;accent-color:var(--cat-a);flex:none}
.mspanel .n{margin-inline-start:auto;font-size:.74rem;color:var(--ink-3);
  font-variant-numeric:tabular-nums;padding-inline-start:8px}
@media(max-width:700px){
  .ms{flex:1 1 calc(50% - 5px);min-width:0}
  .ms>button{width:100%;max-width:none}
  .mspanel{position:fixed;inset-inline:0;top:auto;bottom:0;max-width:none;min-width:0;
    max-height:64vh;border-radius:14px 14px 0 0;border-inline:0;border-bottom:0;
    padding:10px 12px calc(12px + env(safe-area-inset-bottom,0px));
    box-shadow:0 -6px 30px -10px rgba(0,0,0,.35)}
  .mspanel .tools{position:sticky;top:0;background:var(--surface);padding-top:6px}
  .mspanel label{padding:10px 8px}
  .msveil{position:fixed;inset:0;z-index:44;background:rgba(0,0,0,.25)}
}
.msveil{display:none}
.areaf{display:flex;flex-direction:column;gap:7px;min-width:250px;padding:7px 11px 8px;
  background:var(--surface);border:1px solid var(--line);border-radius:var(--r-s)}
.arow{display:flex;align-items:baseline;justify-content:space-between;gap:10px}
.alab{font-size:.76rem;color:var(--ink-2);font-weight:600}
.aout{font-size:.76rem;color:var(--ink);font-variant-numeric:tabular-nums}
.asl{position:relative;height:20px}
.atrack,.afill{position:absolute;top:9px;height:3px;border-radius:2px}
.atrack{inset-inline:0;background:var(--sunken)}
.afill{background:var(--cat-a)}
.asl input[type=range]{position:absolute;inset-inline:0;top:0;width:100%;height:20px;margin:0;
  background:none;pointer-events:none;-webkit-appearance:none;appearance:none}
.asl input[type=range]:focus-visible{outline:2px solid var(--focus);outline-offset:3px;border-radius:4px}
.asl input[type=range]::-webkit-slider-thumb{-webkit-appearance:none;pointer-events:auto;
  width:15px;height:15px;border-radius:50%;background:var(--surface);
  border:2px solid var(--cat-a);box-shadow:var(--sh-1);cursor:grab}
.asl input[type=range]::-moz-range-thumb{pointer-events:auto;width:15px;height:15px;
  border-radius:50%;background:var(--surface);border:2px solid var(--cat-a);cursor:grab}
.achips{display:flex;flex-wrap:wrap;gap:4px}
.achips button{font:inherit;font-size:.7rem;padding:2px 8px;border-radius:999px;cursor:pointer;
  background:var(--ground);color:var(--ink-2);border:1px solid var(--line)}
.achips button:hover{background:var(--raised);color:var(--ink)}
.achips button[aria-pressed=true]{background:var(--cat-a-bg);color:var(--cat-a);
  border-color:color-mix(in srgb,var(--cat-a) 30%,transparent);font-weight:600}
.aunk{display:flex;align-items:center;gap:6px;font-size:.7rem;color:var(--ink-3);cursor:pointer}
.aunk input{margin:0;accent-color:var(--cat-a)}
.rev{margin-top:34px;border:1px solid var(--line);border-radius:12px;background:var(--surface);overflow:hidden}
.rev>summary{cursor:pointer;list-style:none;padding:15px 18px;display:flex;align-items:center;
  gap:10px;flex-wrap:wrap;font-weight:600;background:var(--raised)}
.rev>summary::-webkit-details-marker{display:none}
.rev>summary::before{content:"▸";font-size:.8rem;color:var(--ink-2);transition:transform .15s}
.rev[open]>summary::before{transform:rotate(-90deg)}
.rev .rc{background:var(--ground);border:1px solid var(--line);border-radius:999px;
  padding:1px 9px;font-size:.76rem;font-weight:600;color:var(--ink-2)}
.rev .rw{padding:0 18px 18px;font-size:.85rem;color:var(--ink-2);line-height:1.7}
.rev table{width:100%;border-collapse:collapse;margin-top:12px;font-size:.82rem}
.rev th{text-align:start;font-weight:600;color:var(--ink-2);padding:7px 9px;
  border-bottom:1px solid var(--line);white-space:nowrap}
.rev td{padding:8px 9px;border-bottom:1px solid var(--line);vertical-align:top;color:var(--ink)}
.rev tr:last-child td{border-bottom:0}
.rev .km{font-variant-numeric:tabular-nums;white-space:nowrap}
.rev .ag{font-size:.72rem;padding:1px 7px;border-radius:999px;white-space:nowrap;
  background:var(--cat-a-bg);color:var(--cat-a)}
.rev .ag.n{background:var(--sunken);color:var(--ink-2)}
.lnk{color:var(--cat-a);text-decoration:underline;text-underline-offset:2px}
.rev .lnk{color:var(--cat-a);text-decoration:underline;text-underline-offset:2px;white-space:nowrap}
.revwrap{overflow-x:auto}
footer{margin-top:38px;padding-top:22px;border-top:1px solid var(--line);font-size:.83rem;color:var(--ink-2);line-height:1.7}
footer h3{margin:18px 0 9px;font-size:.9rem;font-weight:600;color:var(--ink)}
footer h3:first-child{margin-top:0}
footer ul{margin:0;padding-inline-start:19px}
footer li{margin-bottom:6px}
code{font-family:"IBM Plex Mono",monospace;font-size:.82em;background:var(--raised);padding:1px 5px;
 border-radius:4px;overflow-wrap:anywhere;word-break:break-word}
.note{border-radius:var(--r-s);padding:13px 16px;margin-bottom:14px;border:1px solid}
.note.ok{background:var(--cat-a-bg);border-color:color-mix(in srgb,var(--cat-a) 28%,transparent)}
.note.ok strong{color:var(--cat-a)}
@media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}
@media(max-width:420px){
  .gate{font-size:.73rem;padding:6px 10px;line-height:1.45}
  h1{font-size:1.15rem}
  .kpi .val{font-size:1.2rem}
}
@media(max-width:700px){
  .wrap{padding:18px 12px 60px}
  .kpis,.kpis.cities{grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}
  .kpi{padding:11px 12px}.kpi .val,.kpi.city .val{font-size:1.35rem}.kpi .lbl{font-size:.71rem;margin-bottom:4px}
  .kpi .split{font-size:.68rem;gap:4px 10px;margin-top:8px;padding-top:7px}
  .ttl{max-width:220px}
  /* a 4-row sticky filter bar would eat a quarter of a phone screen — let it scroll away,
     and dock the table header at the top instead */
  .controls{position:static;padding:9px 0;backdrop-filter:none;-webkit-backdrop-filter:none}
  .count{margin-inline-start:0;width:100%}
  input[type=search]{flex:1 1 100%}
  select{flex:1 1 calc(50% - 5px);min-width:0}
  tbody tr.row{scroll-margin-top:12px}
  .tl{height:76px}
}
</style>
"""
BODY = r"""<div class="wrap">
  <header class="top">
    <div>
      <h1>الفرص الاستثمارية طويلة الأجل — المدن الأربع</h1>
      <p class="sub">بوابة فرص · وزارة الشؤون البلدية والقروية والإسكان · لقطة بتاريخ <span class="mono" id="asof"></span></p>
    </div>
    <div class="gate"><span class="dot"></span><span>الوصول العام: <b>مفتوح</b> — بدون تسجيل دخول أو نفاذ</span></div>
  </header>

  <div class="stale" id="stale"></div>
  <div class="kpis" id="kpis"></div>
  <div class="kpis cities" id="kpiCities"></div>

  <section class="panel">
    <h2>جدول الإغلاق</h2>
    <p class="hint">عدد الفرص التي ينتهي فيها بيع الكراسة، حسب الأسبوع. الأعمدة البرتقالية خلال أول أسبوعين.</p>
    <div class="tl" id="tl"></div>
    <div class="tlx" id="tlx"></div>
  </section>

  <div class="controls">
    <input type="search" id="q" placeholder="ابحث برقم الفرصة أو العنوان أو الحي أو الجهة…" aria-label="بحث">
    <div class="ms" id="msCity"></div>
    <div class="ms" id="msAuth"></div>
    <div class="ms" id="msAct"></div>
    <select id="fWin" aria-label="تصفية بالموعد">
      <option value="">كل المواعيد</option><option value="7">تغلق خلال 7 أيام</option>
      <option value="14">تغلق خلال 14 يوماً</option><option value="30">تغلق خلال 30 يوماً</option>
    </select>
    <div class="areaf">
      <div class="arow">
        <span class="alab">المساحة</span>
        <output class="aout mono" id="aOut">كل الأحجام</output>
      </div>
      <div class="asl">
        <div class="atrack"></div><div class="afill" id="aFill"></div>
        <input type="range" id="aMin" min="0" max="1000" value="0" step="1"
               aria-label="أصغر مساحة">
        <input type="range" id="aMax" min="0" max="1000" value="1000" step="1"
               aria-label="أكبر مساحة">
      </div>
      <div class="achips" role="group" aria-label="أحجام جاهزة">
        <button type="button" data-lo="0"   data-hi="1000">الكل</button>
        <button type="button" data-lo="0"   data-hi="317">أقل من 100 م²</button>
        <button type="button" data-lo="0"   data-hi="476">أقل من 1000 م²</button>
        <button type="button" data-lo="476" data-hi="1000">+1000 م²</button>
        <button type="button" data-lo="635" data-hi="1000">+10 آلاف</button>
        <button type="button" data-lo="746" data-hi="1000">+50 ألف</button>
        <button type="button" data-lo="793" data-hi="1000">+100 ألف</button>
      </div>
      <label class="aunk"><input type="checkbox" id="aUnk" checked>
        <span>إظهار الفرص التي لم تُذكر مساحتها (<span id="aUnkN">0</span>)</span></label>
    </div>
    <select id="sort" aria-label="الترتيب">
      <option value="dl">الأقرب إغلاقاً</option><option value="area">الأكبر مساحة</option>
      <option value="term">الأطول مدة</option><option value="ref">رقم الفرصة</option>
    </select>
    <button type="button" class="reset" id="reset" hidden>إعادة التعيين</button>
    <span class="dchip-live" id="dchip" hidden></span>
    <span class="count" id="count"></span>
  </div>

  <div class="views" role="tablist" aria-label="طرق العرض">
    <button type="button" role="tab" data-v="tbl" aria-selected="true">الجدول</button>
    <button type="button" role="tab" data-v="fun" aria-selected="false">الفرز</button>
    <button type="button" role="tab" data-v="map" aria-selected="false">الخريطة</button>
  </div>
  <div id="sections"></div>
  <div id="vfun" class="vpane" hidden></div>
  <div id="vmap" class="vpane" hidden></div>
  <div class="tip" id="tip" role="status" aria-live="polite"></div>
  <div id="review"></div>

  <footer>
    <div class="note ok">
      <strong>حقل «المدة» — تم التحقق:</strong> حقل <code>DURATION</code> يُقاس <b>بالأشهر</b> وهو مدة العقد الفعلية.
      طُوبق على السجلات الـ__N__ كافة مقابل بطاقة التفاصيل في البوابة (<code>«… شهر مدة العقد»</code>) — تطابق __NDUR__ من __NDUR__.
      وأكدته كذلك كراسة الشروط لإحدى الفرص نصاً: «مدة العقد (180) شهراً أي (15) سنوات».
      24 شهراً = سنتان · 300 = 25 سنة · 600 = 50 سنة. الأكثر شيوعاً <b>__MODEY__</b> (__MODEN__ فرصة).
    </div>
    <h3>المنهجية والنطاق</h3>
    <ul>
      <li><b>النوع:</b> الفرص طويلة الأجل فقط — <code>OPPORTUNITYTYPE = 'Investment'</code>. استُثنيت <code>TemporaryRental</code> (التأجير المؤقت) و<code>DirectRental</code> بالكامل.</li>
      <li><b>الحالة:</b> <code>OPPORTUNITYACTIVESTATUS = 'Announced'</code> مع <code>LASTRFPSELLDATE ≥ تاريخ اللقطة</code> — أي أن كراسة الشروط لا تزال قابلة للشراء.</li>
      <li><b>جهة الطرح:</b> الأمانات والبلديات <em>أو</em> الجهات الشريكة، حسب توجيه الرئيس التنفيذي. الاكتفاء بالأمانات وحدها كان سيُسقط __NPART__ فرصة من __N__ — بما فيها فرص مكة المكرمة كافة.</li>
      <li><b>المدينة:</b> المطابقة على اسم المدينة بعد تطبيع الحروف (ة/ه، أ/إ/آ/ا، ى/ي). البوابة تخزّن «مكه المكرمه» و«المدينه المنوره» بالهاء — والبحث بالإملاء المعياري يعيد صفر نتيجة.</li>
      <li><b>الإحداثيات:</b> من هندسة الطبقة (نقاط WGS84)، متوفرة للسجلات الـ__NGEO__ كافة وجميعها داخل حدود المملكة.</li>
      <li><b>المرفقات:</b> <b>__NKUR__ من __N__</b> لديها كراسة الشروط والمواصفات، و<b>__NAQD__</b> لديها أيضاً مسودة العقد. <b>لم تُدرج روابط تحميل مباشرة عن قصد:</b> عند اختبار عيّنة في متصفح حقيقي فتح بعضها الملف بينما أعاد بعضها التوجيه إلى صفحة القائمة — أرشيف المرفقات في البوابة نفسه غير مكتمل. الزر يوجّهك إلى صفحة الفرصة الرسمية للتحميل من المصدر.</li>
      <li><b>القيم غير المذكورة:</b> المساحة صفر (__NAREA__ سجلات)، سعر الكراسة صفر (__NPRICE__)، وتاريخ فتح المظاريف الصفري 1970-01-01 (__NENV__) تُعرض «غير مذكور». لم تُقدَّر أي قيمة.</li>
      <li><b>الإيجار السنوي غير منشور:</b> <code>ANNUALVALUE</code> و<code>MINIMUMGURANTEE</code> فارغان في جميع السجلات. السعر المعروض هو رسم كراسة الشروط فقط. وقد تبيّن من قراءة إحدى الكراسات أن قيمة الإيجار تُترك فارغة في الكراسة ذاتها وتُحدَّد عند التعاقد.</li>
    </ul>
    <h3>المصدر والتحقق</h3>
    <ul>
      <li>الطبقة <code>InvestmentP</code> عبر <code>gisapps.balady.gov.sa/opportunities/proxy/proxy.ashx</code> → <code>GISProjects/InvestmentView/MapServer/0</code>.</li>
      <li>__NATIONAL__</li>
      <li>__N__ سجلاً · بدون تكرار في رقم الفرصة · صفر صفوف تالفة · جرى سحب صفحة التفاصيل لكل فرصة ومطابقة المساحة والمدة والسعر مع واجهة البيانات: <b>صفر اختلافات</b>.</li>
    </ul>
  </footer>
</div>
"""
JS   = r"""<script id="payload" type="application/json">__DATA__</script>
<script>
(function(){
"use strict";
var D=JSON.parse(document.getElementById('payload').textContent);
var NM='<span class="nm">غير مذكور</span>';
var TIER=['غير مذكور','كشك','صغير','متوسط','كبير','ضخم'];
function E(v){return String(v==null?'':v).replace(/[&<>"']/g,function(c){
  return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
function n(v){return v==null?null:v.toLocaleString('en-US');}
function arYears(y){
  if(y===1)return 'سنة'; if(y===2)return 'سنتان';
  var t=Number.isInteger(y)?y:y.toFixed(1);
  return y<=10? t+' سنوات' : t+' سنة';}
function daysLeft(d){
  var a=new Date(d+'T00:00:00Z'), b=new Date();
  return Math.ceil((a-Date.UTC(b.getUTCFullYear(),b.getUTCMonth(),b.getUTCDate()))/86400000);}
function arDays(k){
  if(k<0)return 'منتهية'; if(k===0)return 'اليوم'; if(k===1)return 'غداً';
  if(k===2)return 'بعد يومين'; if(k<=10)return 'بعد '+k+' أيام'; return 'بعد '+k+' يوماً';}

document.getElementById('asof').textContent=D.asOf;
var age=Math.floor((new Date()-new Date(D.asOf+'T00:00:00Z'))/86400000);
if(age>7){var st=document.getElementById('stale');st.className='stale on';
  st.innerHTML='هذه لقطة عمرها '+age+' يوماً (بتاريخ '+E(D.asOf)+'). المواعيد محسوبة من تاريخ اليوم، '+
   'لكن قد تكون فرص جديدة أُضيفت أو أُلغيت بعد اللقطة. يُنصح بتحديث المسح قبل الاعتماد عليها في قرار.';}

/* ---------- KPIs ---------- */
(function(){
  function sub(a,b){return '<div class="split">'+
    '<span><i class="sw sw-a"></i>أمانة/بلدية<b>'+a+'</b></span>'+
    '<span><i class="sw sw-b"></i>جهة شريكة<b>'+b+'</b></span></div>';}
  document.getElementById('kpis').innerHTML=
    '<div class="kpi"><div class="lbl">إجمالي الفرص المفتوحة</div>'+
      '<div class="val mono">'+D.total+'</div>'+sub(D.totalAmanah,D.totalPartner)+'</div>'+
    '<div class="kpi alert"><div class="lbl">تغلق خلال 14 يوماً</div>'+
      '<div class="val mono">'+D.totalUrgent+'</div>'+
      '<div class="split"><span>'+Math.round(D.totalUrgent/D.total*100)+'% من إجمالي الفرص المفتوحة</span></div></div>';
  document.getElementById('kpiCities').innerHTML=D.cities.map(function(c){
    return '<div class="kpi city"><div class="lbl">'+E(c.label)+'</div>'+
      '<div class="val mono">'+c.n+'</div>'+sub(c.amanah,c.partner)+'</div>';}).join('');
})();

/* ---------- timeline ---------- */
var tip=document.getElementById('tip');
function showTip(e,html){tip.innerHTML=html;tip.classList.add('on');
  var x=e.clientX,y=e.clientY,w=tip.offsetWidth,hh=tip.offsetHeight;
  var L=Math.min(Math.max(8,x-w/2),innerWidth-w-8);
  var T=y-hh-12; if(T<8)T=y+16;
  tip.style.left=L+'px';tip.style.top=T+'px';}
function hideTip(){tip.classList.remove('on');}
(function(){
  var mx=Math.max.apply(null,D.weeks.map(function(w){return w.n;}))||1;
  var b='',x='';
  D.weeks.forEach(function(w,i){
    var pct=w.n? Math.max(3,Math.round(w.n/mx*100)) : 0;
    b+='<div class="tlc'+(i<2?' soon':'')+'" tabindex="0" data-i="'+i+'">'+
       '<span class="n mono">'+(w.n||'')+'</span>'+
       '<div class="tlb" style="height:'+pct+'%"></div></div>';
    x+='<span class="mono">'+(i%2===0? w.from.slice(5) : '')+'</span>';});
  var tl=document.getElementById('tl'); tl.innerHTML=b;
  document.getElementById('tlx').innerHTML=x;
  function ev(e){
    var c=e.target.closest('.tlc'); if(!c)return;
    var w=D.weeks[+c.dataset.i];
    showTip(e,'<b>'+w.n+'</b> فرصة<br>'+w.from+' → '+w.to);}
  tl.addEventListener('mousemove',ev);
  tl.addEventListener('mouseleave',hideTip);
  tl.addEventListener('focusin',function(e){
    var c=e.target.closest('.tlc'); if(!c)return;
    var r=c.getBoundingClientRect(), w=D.weeks[+c.dataset.i];
    showTip({clientX:r.left+r.width/2,clientY:r.top},'<b>'+w.n+'</b> فرصة<br>'+w.from+' → '+w.to);});
  tl.addEventListener('focusout',hideTip);
})();

/* ---------- controls ---------- */
/* Counts inside each panel are computed against the OTHER filters, so a number shows what
   that option would actually yield right now, not a static total. */
function passExcept(r, skip){
  var A=areaRange();
  if(skip!=='city' && MS.city.get().size && !MS.city.get().has(r.city)) return false;
  if(skip!=='auth' && MS.auth.get().size && !MS.auth.get().has(r.isAmanah?'a':'b')) return false;
  if(skip!=='act'  && MS.act.get().size  && !MS.act.get().has(r.activity||'—')) return false;
  var fWin=document.getElementById('fWin').value;
  if(fWin){var k=daysLeft(r.deadline); if(k<0||k>+fWin) return false;}
  if(!areaPass(r,A)) return false;
  if(FDIST && r.district!==FDIST.d) return false;
  if(FREF && r.ref!==FREF) return false;
  var q=document.getElementById('q').value.trim().toLowerCase();
  if(q){var hay=(r.ref+' '+r.title+' '+(r.district||'')+' '+(r.street||'')+' '+
    (r.authority||'')+' '+(r.activity||'')+' '+(r.sub||'')).toLowerCase();
    if(hay.indexOf(q)===-1) return false;}
  return true;
}
function countBy(skip, key){
  var out={};
  D.records.forEach(function(r){ if(passExcept(r,skip)){var v=key(r); out[v]=(out[v]||0)+1;} });
  return out;
}
var MS={};
MS.city=MultiSelect(document.getElementById('msCity'),{
  allLabel:'كل المدن', someLabel:'مدن مختارة',
  options:D.cities.map(function(c){return {value:c.city,label:c.label};}),
  counts:function(){return countBy('city',function(r){return r.city;});},
  onChange:function(){render();}});
MS.auth=MultiSelect(document.getElementById('msAuth'),{
  allLabel:'كل جهات الطرح', someLabel:'جهات مختارة',
  options:[{value:'a',label:'أمانة / بلدية'},{value:'b',label:'جهة شريكة'}],
  counts:function(){return countBy('auth',function(r){return r.isAmanah?'a':'b';});},
  onChange:function(){render();}});
MS.act=MultiSelect(document.getElementById('msAct'),{
  allLabel:'كل الأنشطة', someLabel:'أنشطة مختارة',
  options:(D.activities||[]).map(function(a){return {value:a.name,label:a.name};}),
  counts:function(){return countBy('act',function(r){return r.activity||'—';});},
  onChange:function(){render();}});

var HEAD='<thead><tr><th aria-hidden="true"></th><th>رقم الفرصة</th><th>العنوان</th><th>النشاط</th><th>المدينة / الجهة</th>'+
 '<th>الموقع</th><th>مدة العقد</th><th>المساحة</th><th>السعر (كراسة)</th><th>نهاية الفرصة</th></tr></thead>';

/* =======================================================================
   THREE ANALYTICAL VIEWS
   Urgency is ORDERED data, so it uses a single-hue sequential ramp (--u1..--u4),
   not the table's crit/warn status pair — that pair sits at ΔE 9.7 for normal
   vision, which is fine beside a text label in a row but not for bare dots.
   City identity comes from FACETING (one panel per city), so no new categorical
   hues are introduced anywhere in these views.
   ======================================================================= */
var UB=[{d:3,c:'var(--u4)',l:'≤ 3 أيام'},{d:14,c:'var(--u3)',l:'4 – 14 يوماً'},
        {d:30,c:'var(--u2)',l:'15 – 30 يوماً'},{d:1e9,c:'var(--u1)',l:'أكثر من 30 يوماً'}];
function uCol(k){ for(var i=0;i<UB.length;i++) if(k<=UB[i].d) return UB[i].c; return 'var(--u1)'; }
function esc(x){ return E(String(x)); }
var _MED=null;
function medArea(){
  if(_MED===null){
    var a=D.records.map(function(r){return r.area;}).filter(function(x){return x!=null;})
                   .sort(function(x,y){return x-y;});
    _MED = a.length ? Math.round(a.length%2 ? a[(a.length-1)/2]
                                            : (a[a.length/2-1]+a[a.length/2])/2) : 0;
  }
  return _MED;
}

/* ---------------- 1. FUNNEL: how few are worth reading ---------------- */
function renderFunnel(){
  var A=areaRange(), R=D.records;
  var steps=[
    {n:'كل الفرص المعلنة', s:'المدن الأربع كما تُسمّيها البوابة', f:function(){return true;}},
    {n:'مساحة مذكورة', s:'المساحة صفر تعني غير مذكورة — لا تُقدَّر',
     f:function(r){return r.area!=null;}},
    {n:'50 ألف م² أو أكثر', s:'حد القطع التطويرية، وهو الحد الذي يستخدمه مرصد الأخبار',
     f:function(r){return r.area!=null && r.area>=50000;}},
    {n:'مدة 15 سنة أو أكثر', s:'أفق يسمح بالتطوير ورد رأس المال',
     f:function(r){return r.area!=null && r.area>=50000 && r.months>=180;}},
    {n:'كراسة متوفرة', s:'يمكن قراءة الشروط فعلياً قبل القرار',
     f:function(r){return r.area!=null && r.area>=50000 && r.months>=180 && r.kurasa;}},
    {n:'ما زال بابها مفتوحاً', s:'لم يمضِ موعد شراء الكراسة',
     f:function(r){return r.area!=null && r.area>=50000 && r.months>=180 && r.kurasa
                    && daysLeft(r.deadline)>=0;}}
  ];
  var top=R.length, rows='';
  steps.forEach(function(st,i){
    var k=R.filter(st.f).length, pct=top?(k/top*100):0, drop=(i?R.filter(steps[i-1].f).length-k:0);
    rows+='<div class="fstep"><div class="fname">'+esc(st.n)+'<small>'+esc(st.s)+'</small></div>'+
      '<div class="fbar"><span style="width:'+pct.toFixed(1)+'%"></span></div>'+
      '<div class="fnum"><b>'+k+'</b>'+(i?' <s>−'+drop+'</s>':'')+'</div></div>';
  });
  var fin=R.filter(steps[steps.length-1].f)
           .sort(function(a,b){return (b.area||0)-(a.area||0);});
  var tbl='';
  if(fin.length){
    tbl='<div class="card"><h4 style="margin:0 0 3px;font-size:.92rem">اقرأ هذه أولاً</h4>'+
      '<p style="margin:0 0 10px;font-size:.76rem;color:var(--ink-3)">'+
      'مرتّبة بالمساحة تنازلياً. «مسودة عقد» تعني أن الشروط التعاقدية منشورة أيضاً، '+
      'فتكلفة التقييم أقل.</p><div class="sc"><table class="short"><thead><tr>'+
      '<th>رقم الفرصة</th><th>العنوان</th><th>المدينة</th><th>المساحة</th><th>المدة</th>'+
      '<th>آخر موعد</th><th>الوثائق</th><th></th></tr></thead><tbody>'+
      fin.map(function(r){
        var k=daysLeft(r.deadline);
        return '<tr data-ref="'+E(r.ref)+'" tabindex="0"><td class="mono">'+esc(r.ref)+'</td><td>'+esc(r.title)+'</td>'+
        '<td>'+esc(r.cityLabel)+'</td><td class="mono">'+n(Math.round(r.area))+' م²</td>'+
        '<td>'+arYears(r.years)+'</td>'+
        '<td class="mono">'+esc(r.deadline)+' <span style="color:'+uCol(k)+
          ';font-weight:600">'+arDays(k)+'</span></td>'+
        '<td><span class="pill">كراسة</span> '+
          (r.aqd?'<span class="pill">مسودة عقد</span>':'<span class="pill no">لا عقد</span>')+'</td>'+
        '<td><a class="lnk" target="_blank" rel="noopener" href="https://furas.momah.gov.sa/opportunity/'+
          encodeURIComponent(r.ref)+'?type=Investment">فتح</a></td></tr>';
      }).join('')+'</tbody></table></div></div>';
  } else {
    tbl='<div class="card"><p style="margin:0;font-size:.85rem">لا فرصة تجتاز كل المراحل هذا الأسبوع.</p></div>';
  }
  document.getElementById('vfun').innerHTML=
    '<h3 class="vh">من '+D.total+' فرصة إلى قائمة قابلة للقراءة</h3>'+
    '<p class="vs">وسيط المساحة في هذه الدفعة <b>'+n(medArea())+' م²</b> — أي أن معظم المعروض '+
    'أكشاك ومواقع '+
    'صغيرة لا تناسب مطوّراً. هذا العرض يطبّق المعايير تنازلياً ويُظهر كم فرصة تتساقط عند كل حد، '+
    'حتى تنتهي بقائمة قصيرة تُقرأ فعلاً. المعايير ثابتة هنا عن قصد — لتغيير المساحة استخدم '+
    'شريط التمرير أعلاه، وسيتحدّث الجدول لا هذا القمع.</p>'+
    '<div class="card">'+rows+'</div>'+tbl;
}

/* ---------------- MAP ----------------
   Rebuilt 17 Sep 2026 after the first version read as confusing. What changed:

   1. NORTH IS UP AND EAST IS RIGHT. The first version mirrored longitude so that east sat on
      the left, reasoning that an RTL page should read right-to-left. That was wrong — a map
      is not text. Every conventional map, Arabic ones included, puts north up and east right,
      so mirroring silently flipped every city and made the layout unreadable against anything
      familiar. A compass rose now states the orientation explicitly.
   2. The frame is squared in TRUE GROUND DISTANCE (see the cos-latitude correction where geo
      is built), so a city is no longer stretched horizontally.
   3. Clicking a district opens that district on Google Maps, framed to its own extent.

   Still no road basemap inside the page: published artifacts block external tile hosts, and
   drawing roads from memory would put invented geography under real coordinates. */
function uLegend(){
  return '<div class="lgd"><span>الوقت المتبقي لشراء الكراسة:</span>'+
    UB.map(function(b){return '<span><i style="background:'+b.c+'"></i>'+b.l+'</span>';}).join('')+
    '</div>';
}
function gmapsAt(lat,lon,z){
  return 'https://www.google.com/maps/@'+lat.toFixed(5)+','+lon.toFixed(5)+','+z+'z';
}
/* Searching the district BY NAME makes Google resolve the neighbourhood and shade its own
   boundary — a URL cannot draw a polygon, but Google already holds one. The coordinates ride
   along as a centre hint so an ambiguous name still lands in the right city. */
/* Up to 10 opportunities as real pins on ONE Google map, in one click.
   The documented Maps URLs API (`/maps/dir/?api=1`) takes an origin, a destination and up to
   9 waypoints, and drops a lettered pin on each — the only URL form that shows more than one
   location. It also draws a route between them, which is noise here, so the button says so
   rather than pretending the line means something. Above 10 points there is no URL that will
   do it: that is what the CSV export and My Maps are for. */
var GMAPS_PIN_MAX=10;
function gmapsPins(rows){
  var pts=rows.filter(function(r){return r.lat!=null;}).slice(0,GMAPS_PIN_MAX);
  if(pts.length<2) return null;
  var c=function(r){return r.lat.toFixed(6)+','+r.lon.toFixed(6);};
  var mid=pts.slice(1,-1).map(c).join('|');
  return 'https://www.google.com/maps/dir/?api=1'+
         '&origin='+encodeURIComponent(c(pts[0]))+
         '&destination='+encodeURIComponent(c(pts[pts.length-1]))+
         (mid?'&waypoints='+encodeURIComponent(mid):'')+
         '&travelmode=driving';
}
function gmapsDistrict(name, cityLabel, lat, lon){
  return 'https://www.google.com/maps/search/'+
         encodeURIComponent('حي '+name+'، '+cityLabel)+
         '/@'+lat.toFixed(5)+','+lon.toFixed(5)+',14z';
}
function zoomForKm(km){                     /* ~ the zoom that frames km across on a phone-ish map */
  if(km<=0.5) return 17; if(km<=1) return 16; if(km<=2.5) return 15;
  if(km<=5) return 14; if(km<=12) return 13; if(km<=25) return 12; return 11;
}
function renderMap(){
  var A=areaRange(), S=440, P=34;           /* square canvas: the frame is square on the ground */
  var cells=D.cities.map(function(c){
    var g=D.geo[c.city]; if(!g) return '';
    var rs=D.records.filter(function(r){return r.city===c.city && r.lat!=null && areaPass(r,A);});
    var maxA=Math.max.apply(null,[1].concat(rs.map(function(r){return r.area||0;})));
    /* north up, east right — no mirroring */
    function X(lon){ return P+((lon-g.minLon)/(g.maxLon-g.minLon))*(S-2*P); }
    function Y(lat){ return S-P-((lat-g.minLat)/(g.maxLat-g.minLat))*(S-2*P); }

    var span=g.maxLon-g.minLon;
    var step=[.01,.02,.05,.1,.2,.5].filter(function(v){return span/v<=5;})[0]||1;
    var grid='';
    for(var lo=Math.ceil(g.minLon/step)*step; lo<g.maxLon; lo+=step){
      grid+='<line x1="'+X(lo).toFixed(1)+'" y1="'+P+'" x2="'+X(lo).toFixed(1)+'" y2="'+(S-P)+
        '" stroke="var(--line)" stroke-width=".8" stroke-dasharray="2 4"/>'+
        '<text x="'+X(lo).toFixed(1)+'" y="'+(S-P+12)+'" font-size="8" fill="var(--ink-3)" '+
        'text-anchor="middle">'+lo.toFixed(2)+'°</text>';
    }
    for(var la=Math.ceil(g.minLat/step)*step; la<g.maxLat; la+=step){
      grid+='<line x1="'+P+'" y1="'+Y(la).toFixed(1)+'" x2="'+(S-P)+'" y2="'+Y(la).toFixed(1)+
        '" stroke="var(--line)" stroke-width=".8" stroke-dasharray="2 4"/>'+
        '<text x="'+(P-4)+'" y="'+(Y(la)+3).toFixed(1)+'" font-size="8" fill="var(--ink-3)" '+
        'text-anchor="end" direction="ltr">'+la.toFixed(2)+'°</text>';
    }

    var dots=rs.slice().sort(function(a,b){return (b.area||0)-(a.area||0);}).map(function(r){
      var k=daysLeft(r.deadline);
      var rad=r.area? Math.max(3.4, Math.min(19, Math.sqrt(r.area/maxA)*19)) : 3.4;
      return '<circle data-ref="'+E(r.ref)+'" tabindex="0" role="button" cx="'+X(r.lon).toFixed(1)+
        '" cy="'+Y(r.lat).toFixed(1)+'" r="'+rad.toFixed(1)+'" fill="'+uCol(k)+
        '" fill-opacity="'+(r.area?.72:.5)+'" stroke="var(--surface)" stroke-width="1.3">'+
        '<title>'+E(r.ref+' · '+(r.district||'حي غير مذكور')+' · '+
        (r.area? n(Math.round(r.area))+' م²':'مساحة غير مذكورة')+' · '+arDays(k)+
        ' — انقر لعرض التفاصيل في الجدول')+'</title></circle>';
    }).join('');

    /* district labels, biggest clusters first, nudged apart */
    var byd={};
    rs.forEach(function(r){ if(r.district){ (byd[r.district]=byd[r.district]||[]).push(r); } });
    var placed=[], labs='';
    Object.keys(byd).map(function(d){
      var v=byd[d];
      return {d:d,n:v.length,
              lat:v.reduce(function(t,x){return t+x.lat;},0)/v.length,
              lon:v.reduce(function(t,x){return t+x.lon;},0)/v.length};
    }).sort(function(a,b){return b.n-a.n;}).forEach(function(m){
      /* every district is labelled, biggest cluster first; a label that cannot be placed
         without covering one already down is dropped from the map and still appears in the
         district table below, so nothing is silently lost */
      var x=X(m.lon), y=Y(m.lat)-10, ok=false;
      for(var t=0;t<6;t++){
        if(!placed.some(function(q){return Math.abs(q.x-x)<56 && Math.abs(q.y-y)<11;})){ok=true;break;}
        y-= (t%2 ? 11 : -22);
      }
      if(!ok) return;
      placed.push({x:x,y:y});
      labs+='<text data-dist="'+E(m.d)+'" data-distcity="'+E(c.label)+'" tabindex="0" role="button" '+
        'x="'+x.toFixed(1)+'" y="'+y.toFixed(1)+'" font-size="9.5" font-weight="600" '+
        'fill="var(--ink-2)" text-anchor="middle" paint-order="stroke" stroke="var(--surface)" '+
        'stroke-width="3.2" stroke-linejoin="round">'+E(m.d)+(m.n>1?' ('+m.n+')':'')+
        '<title>'+E(m.d+' — '+m.n+' فرصة · انقر لعرضها كلها في الجدول')+'</title></text>';
    });

    /* compass rose — the orientation stated, not assumed */
    var cxN=S-P-16, cyN=P+18;
    var rose='<g aria-hidden="true">'+
      '<circle cx="'+cxN+'" cy="'+cyN+'" r="13" fill="var(--surface)" stroke="var(--line-2)"/>'+
      '<path d="M '+cxN+' '+(cyN-10)+' L '+(cxN-4.5)+' '+(cyN+3)+' L '+cxN+' '+(cyN+0.5)+
        ' L '+(cxN+4.5)+' '+(cyN+3)+' Z" fill="var(--ink)"/>'+
      '<text x="'+cxN+'" y="'+(cyN+11)+'" font-size="7.5" font-weight="700" fill="var(--ink-2)" '+
      'text-anchor="middle" direction="ltr">N</text></g>';

    /* scale bar measured off the projection */
    var pxPerKm=(S-2*P)/g.widthKm;
    var barKm=[1,2,5,10,20,50].filter(function(v){return v*pxPerKm<=120;}).pop()||1;
    var bx=P, by=S-P-10;
    var bar='<g><line x1="'+bx+'" y1="'+by+'" x2="'+(bx+barKm*pxPerKm).toFixed(1)+'" y2="'+by+
      '" stroke="var(--ink-2)" stroke-width="2"/>'+
      '<line x1="'+bx+'" y1="'+(by-3.5)+'" x2="'+bx+'" y2="'+(by+3.5)+'" stroke="var(--ink-2)" stroke-width="1.5"/>'+
      '<line x1="'+(bx+barKm*pxPerKm).toFixed(1)+'" y1="'+(by-3.5)+'" x2="'+
        (bx+barKm*pxPerKm).toFixed(1)+'" y2="'+(by+3.5)+'" stroke="var(--ink-2)" stroke-width="1.5"/>'+
      '<text x="'+(bx+barKm*pxPerKm/2).toFixed(1)+'" y="'+(by-6)+'" font-size="8.5" '+
      'fill="var(--ink-2)" text-anchor="middle" paint-order="stroke" stroke="var(--ground)" '+
      'stroke-width="3" stroke-linejoin="round">'+barKm+' كم</text></g>';

    var cLat=(g.minLat+g.maxLat)/2, cLon=(g.minLon+g.maxLon)/2;
    return '<div class="mcell"><div class="mhead"><h4>'+E(c.label)+'</h4>'+
      '<span class="mact">'+
      '<button type="button" class="chipbtn" data-cityexp="'+E(c.city)+'" '+
      'title="ملف يُستورد في خرائطي (My Maps) فتظهر كل فرص المدينة كدبابيس مُسمّاة">'+
      'تصدير دبابيس المدينة</button>'+
      '<a class="lnk" target="_blank" rel="noopener" href="'+gmapsAt(cLat,cLon,zoomForKm(g.widthKm))+
      '">خرائط Google ↗</a></span></div>'+
      '<p>'+rs.length+' فرصة معروضة'+(rs.length!==g.n?' من '+g.n:'')+
      ' · الإطار '+Math.round(g.widthKm)+' × '+Math.round(g.widthKm)+' كم · الشمال للأعلى'+
      (g.png?' · الطرق الرئيسية من بيانات وزارة النقل':'')+'</p>'+
      '<div class="sc"><svg viewBox="0 0 '+S+' '+S+'" width="100%" role="img" '+
      'aria-label="مواقع الفرص في '+E(c.label)+' — الشمال للأعلى والشرق لليمين">'+
      '<rect x="'+P+'" y="'+P+'" width="'+(S-2*P)+'" height="'+(S-2*P)+
      '" fill="var(--ground)" stroke="var(--line-2)" rx="5"/>'+
      /* real MOT main roads, rendered by MOMRA into this exact frame */
      (g.png?'<image href="'+g.png+'" x="'+P+'" y="'+P+'" width="'+(S-2*P)+'" height="'+(S-2*P)+
        '" preserveAspectRatio="none" class="roadimg"/>':'')+
      grid+dots+labs+bar+rose+'</svg></div></div>';
  }).join('');

  var dq=(document.getElementById('dq')||{}).value||'';
  var cl=D.clusters.filter(function(x){
    return !dq || (x.district+' '+x.cityLabel).toLowerCase().indexOf(dq.trim().toLowerCase())!==-1;
  });
  var ctab = '<div class="card"><div class="crow2">'+
    '<div><h4 style="margin:0 0 3px;font-size:.92rem">كل الأحياء ('+D.clusters.length+')</h4>'+
    '<p style="margin:0;font-size:.76rem;color:var(--ink-3)">'+
    '<b>اضغط أي صف</b> لعرض فرص ذلك الحي وحده في الجدول — وتظهر عندها شارة فيها رابط '+
    'خرائط Google وزر «تصدير الدبابيس».</p>'+
    '<p style="margin:6px 0 0;font-size:.74rem;color:var(--ink-3)">'+
    '«افتح الحي» يبحث في خرائط Google بالاسم، فتُظهر جوجل حدود الحي نفسها. ولعرض الفرص '+
    '<b>كدبابيس مُسمّاة</b> على خريطة واحدة: صدِّر الملف ثم استورده في '+
    '<a class="lnk" target="_blank" rel="noopener" href="https://www.google.com/maps/d/">خرائطي '+
    '(My Maps)</a> — لا يمكن لرابط واحد أن يضع عدة دبابيس على خرائط Google، وهذا هو الطريق '+
    'الذي يعمل فعلاً.</p></div>'+
    '<input type="search" id="dq" value="'+E(dq)+'" placeholder="ابحث عن حي…" '+
    'aria-label="ابحث عن حي"></div>'+
    (cl.length
      ? '<div class="sc"><table class="cl2"><thead><tr><th>المدينة</th><th>الحي</th>'+
        '<th>عدد الفرص</th><th>مجموع المساحة</th><th>امتداد الحي</th><th>أقرب إغلاق</th>'+
        '<th>خرائط Google</th></tr></thead><tbody>'+
        cl.map(function(x){return '<tr data-dist="'+E(x.district)+'" data-distcity="'+E(x.cityLabel)+
          '" tabindex="0"><td>'+E(x.cityLabel)+'</td><td><b>'+E(x.district)+'</b></td>'+
          '<td class="mono">'+x.n+'</td><td class="mono">'+n(Math.round(x.area))+' م²'+
          (x.withArea<x.n?' <span style="color:var(--ink-3);font-size:.72rem">('+x.withArea+'/'+x.n+')</span>':'')+
          '</td><td class="mono">'+(x.spanKm<0.05?'موقع واحد':x.spanKm.toFixed(1)+' كم')+'</td>'+
          '<td class="mono">'+E(x.soonest)+'</td>'+
          '<td><a class="lnk" target="_blank" rel="noopener" href="'+
          gmapsDistrict(x.district,x.cityLabel,x.lat,x.lon)+'">افتح الحي ↗</a></td></tr>';}).join('')+
        '</tbody></table></div>'
      : '<p style="margin:8px 0 0;font-size:.85rem;color:var(--ink-3)">لا حي يطابق «'+E(dq)+'».</p>')+
    '</div>';

  document.getElementById('vmap').innerHTML=
    '<h3 class="vh">أين تقع الفرص</h3>'+
    '<p class="vs"><b>الشمال للأعلى والشرق لليمين</b>، كأي خريطة — والإطار مربّع بالمسافة '+
    'الحقيقية على الأرض، فلا تمدُّد في العرض. حجم الدائرة يتبع المساحة، واللون يتبع الوقت '+
    'المتبقي. <b>انقر أي دائرة لفتح تفاصيل الفرصة في الجدول</b>، أو «افتح الحي» في الجدول '+
    'أسفل الصفحة لرؤية الحي على خرائط Google بالطرق والصور.</p>'+
    '<p class="vs" style="color:var(--ink-3)"><b>الطرق الرئيسية حقيقية</b> — طبقات «MOT Roads» '+
    'من خريطة الأساس الرسمية لوزارة الشؤون البلدية (نفس الجهة التي تنشر الفرص)، مرسومة على '+
    'الإطار نفسه تماماً. لم يُرسم أي طريق تقديراً. بقية ما على الخريطة كذلك من البيانات: '+
    'أسماء أحياء عند مراكزها الفعلية، وشبكة إحداثيات، ومقياس محسوب.</p>'+
    uLegend()+'<div class="mgrid">'+cells+'</div>'+ctab;
  Array.prototype.forEach.call(document.querySelectorAll('[data-cityexp]'),function(b){
    b.addEventListener('click',function(){
      var cy=b.getAttribute('data-cityexp');
      var rows=D.records.filter(function(r){return r.city===cy && areaPass(r,areaRange());});
      var lbl=(D.cities.filter(function(x){return x.city===cy;})[0]||{}).label||cy;
      exportRows(rows, lbl);
    });
  });
  var dqi=document.getElementById('dq');
  if(dqi){
    dqi.addEventListener('input',function(){
      var v=this.value, pos=this.selectionStart;
      renderMap();
      var nx=document.getElementById('dq');
      if(nx){ nx.focus(); try{nx.setSelectionRange(pos,pos);}catch(e){} }
    });
  }
}

/* ---------------- view switching ---------------- */
var VIEW='tbl';
var PANE={tbl:'sections',fun:'vfun',map:'vmap'};
function paintView(){
  if(VIEW==='fun') renderFunnel();
  else if(VIEW==='map') renderMap();
}
Array.prototype.forEach.call(document.querySelectorAll('.views button'),function(b){
  b.addEventListener('click',function(){
    VIEW=b.dataset.v;
    Array.prototype.forEach.call(document.querySelectorAll('.views button'),function(o){
      o.setAttribute('aria-selected', o===b ? 'true':'false');
    });
    Object.keys(PANE).forEach(function(k){
      document.getElementById(PANE[k]).hidden = (k!==VIEW);
    });
    document.getElementById('tip').hidden = (VIEW!=='tbl');
    paintView();
  });
});

/* ---------- area filter: log-scale dual slider ----------
   Range spans 1 m2 to 2,000,000 m2 (real data: 14 m2 kiosk to 1,815,472 m2 parcel), so the
   scale must be logarithmic — on a linear scale every parcel under ~20,000 m2 collapses into
   the first 1% of the track and the control is useless for the 152 records below 50,000 m2.
   Slider units are 0-1000; area = 2e6^(v/1000). */
var AMAX=2000000, LMAX=Math.log(AMAX);
function v2a(v){ return Math.exp((v/1000)*LMAX); }
function a2v(a){ return Math.round(1000*Math.log(Math.max(1,a))/LMAX); }
var aMin=document.getElementById('aMin'), aMax=document.getElementById('aMax'),
    aUnk=document.getElementById('aUnk'), aOut=document.getElementById('aOut'),
    aFill=document.getElementById('aFill');

function areaRange(){
  var lo=+aMin.value, hi=+aMax.value;
  if(lo>hi){var t=lo; lo=hi; hi=t;}
  return {lo:lo, hi:hi, min:v2a(lo), max:v2a(hi),
          all:(lo===0 && hi===1000), unk:aUnk.checked,
          on:!(lo===0 && hi===1000 && aUnk.checked)};
}
function areaPass(r,A){
  if(r.area==null) return A.unk;          /* unstated area is a real state, never silently dropped */
  if(A.all) return true;
  return r.area>=A.min && r.area<=A.max;
}
function fmtA(m){
  if(m>=1000000) return (m/1000000).toFixed(m<10000000?1:0)+' مليون';
  if(m>=1000)    return n(Math.round(m/1000))+' ألف';
  return n(Math.round(m));
}
function syncArea(){
  var A=areaRange();
  /* RTL: the track runs right-to-left, so the low handle pins to the right edge */
  var l=Math.min(A.lo,A.hi)/10, h=Math.max(A.lo,A.hi)/10;
  aFill.style.right=l+'%'; aFill.style.left=(100-h)+'%';
  aOut.textContent = A.all ? 'كل الأحجام'
    : (A.lo===0 ? 'حتى '+fmtA(A.max)+' م²'
    : (A.hi===1000 ? 'من '+fmtA(A.min)+' م² وأكثر'
    : fmtA(A.min)+' – '+fmtA(A.max)+' م²'));
  Array.prototype.forEach.call(document.querySelectorAll('.achips button'),function(b){
    b.setAttribute('aria-pressed', (+b.dataset.lo===A.lo && +b.dataset.hi===A.hi) ? 'true':'false');
  });
}
[aMin,aMax].forEach(function(el){ el.addEventListener('input',function(){ syncArea(); render(); }); });
aUnk.addEventListener('change',function(){ render(); });
Array.prototype.forEach.call(document.querySelectorAll('.achips button'),function(b){
  b.addEventListener('click',function(){
    aMin.value=b.dataset.lo; aMax.value=b.dataset.hi; syncArea(); render();
  });
});
document.getElementById('aUnkN').textContent = D.records.filter(function(r){return r.area==null;}).length;

function rowHTML(r,id){
  var k=daysLeft(r.deadline);
  var cls=k<0?'':(k<=3?'u3':(k<=14?'u14':''));
  var dc=k<0?'g':(k<=3?'c':(k<=14?'w':''));
  return '<tr class="row '+cls+'" tabindex="0" data-t="'+id+'" aria-expanded="false">'+
   '<td class="st" aria-hidden="true"></td>'+
   '<td class="ref mono">'+E(r.ref)+'</td>'+
   '<td class="ttl"><div class="cl">'+E(r.title)+'</div></td>'+
   '<td class="act">'+(r.activity?'<div class="a1">'+E(r.activity)+'</div>':NM)+
     (r.sub&&r.sub!=='أخرى'?'<div class="a2">'+E(r.sub)+'</div>':'')+'</td>'+
   '<td><div>'+E(r.cityLabel)+'</div>'+
     '<span class="chip '+(r.isAmanah?'a':'b')+'">'+(r.isAmanah?'أمانة/بلدية':'جهة شريكة')+'</span>'+
     (r.authority?'<div class="auth">'+E(r.authority)+'</div>':'')+'</td>'+
   '<td>'+(r.loc?E(r.loc):NM)+'</td>'+
   '<td class="term"><b>'+arYears(r.years)+'</b><span>'+r.months+' شهر</span></td>'+
   '<td class="areac">'+(r.area?'<span class="areav mono" title="'+TIER[r.tier]+'">'+n(Math.round(r.area))+'</span><span class="u">م²</span>':NM)+'</td>'+
   '<td class="areac mono">'+(r.price?n(r.price)+' ﷼':NM)+'</td>'+
   '<td class="dl mono">'+E(r.deadline)+'<span class="days '+dc+'">'+arDays(k)+'</span></td></tr>'+
  '<tr class="det hide" id="'+id+'"><td colspan="10"><div class="db">'+
   '<p class="full">'+E(r.title)+'</p><dl class="dg">'+
   '<div><dt>رقم الفرصة</dt><dd class="mono">'+E(r.ref)+'</dd></div>'+
   '<div><dt>جهة الطرح</dt><dd>'+(r.authority?E(r.authority):NM)+'</dd></div>'+
   '<div><dt>البلدية</dt><dd>'+(r.baladya?E(r.baladya):NM)+'</dd></div>'+
   '<div><dt>الحي</dt><dd>'+(r.district?E(r.district):NM)+'</dd></div>'+
   '<div><dt>الشارع</dt><dd>'+(r.street?E(r.street):NM)+'</dd></div>'+
   '<div><dt>النشاط</dt><dd>'+(r.activity?E(r.activity):NM)+'</dd></div>'+
   '<div><dt>النشاط الفرعي</dt><dd>'+(r.sub?E(r.sub):NM)+'</dd></div>'+
   '<div><dt>المساحة</dt><dd>'+(r.area?'<span class="mono">'+n(Math.round(r.area))+'</span> م² · '+TIER[r.tier]:NM)+'</dd></div>'+
   '<div><dt>مدة العقد</dt><dd><b>'+arYears(r.years)+'</b> ('+r.months+' شهر)</dd></div>'+
   '<div><dt>رسم الكراسة</dt><dd class="mono">'+(r.price?n(r.price)+' ﷼':NM)+'</dd></div>'+
   '<div><dt>آخر موعد لشراء الكراسة</dt><dd class="mono">'+E(r.deadline)+'</dd></div>'+
   '<div><dt>فتح المظاريف</dt><dd class="mono">'+(r.envelopes?E(r.envelopes):NM)+'</dd></div>'+
   '<div><dt>الإحداثيات</dt><dd class="mono">'+(r.lat==null?NM:r.lat.toFixed(6)+'، '+r.lon.toFixed(6))+'</dd></div>'+
   '<div><dt>الحالة</dt><dd>معلنة (Announced)</dd></div>'+
   '</dl><div class="acts">'+
   (r.lat==null?'':'<a class="btn" target="_blank" rel="noopener" href="https://www.google.com/maps/search/?api=1&query='+r.lat+','+r.lon+'">📍 الموقع على الخريطة</a>')+
   '<a class="btn p" target="_blank" rel="noopener" href="https://furas.momah.gov.sa/opportunity/'+encodeURIComponent(r.ref)+'?type=Investment">📄 صفحة الفرصة والمرفقات</a>'+
   (r.docs.length
     ? r.docs.filter(function(d){return d.dl;}).map(function(d){
         return '<a class="btn doc" target="_blank" rel="noopener" href="'+E(d.dl)+'">📄 '+
                E(d.name)+'</a>';}).join('')+
       '<span class="docs">'+
       (r.docs.some(function(d){return !d.dl;})
         ? 'لا يخدمها أرشيف البوابة مباشرة — تُحمَّل من صفحة الفرصة: '+
           r.docs.filter(function(d){return !d.dl;})
                 .map(function(d){return '<span class="dchip">'+E(d.name)+'</span>';}).join('')
         : 'كل مرفقات هذه الفرصة تُفتح مباشرة من الأزرار أعلاه.')+'</span>'
     :'<span class="docs">لا توجد مرفقات منشورة لهذه الفرصة</span>')+
   '</div></div></td></tr>';
}

var SORT={dl:function(a,b){return a.deadline<b.deadline?-1:a.deadline>b.deadline?1:a.ref<b.ref?-1:1;},
          area:function(a,b){return (b.area||0)-(a.area||0);},
          term:function(a,b){return b.months-a.months;},
          ref:function(a,b){return a.ref<b.ref?-1:1;}};

function render(){
  var q=document.getElementById('q').value.trim().toLowerCase();
  var selCity=MS.city.get(), selAuth=MS.auth.get(), selAct=MS.act.get();
  var fWin=document.getElementById('fWin').value;
  var A=areaRange();
  var sk=document.getElementById('sort').value;
  var active=(q?1:0)+(selCity.size?1:0)+(selAuth.size?1:0)+(selAct.size?1:0)+
              (fWin?1:0)+(A.on?1:0)+(FDIST?1:0)+(FREF?1:0);
  distChip();
  document.getElementById('reset').hidden=!active;

  if(VIEW!=='tbl'){ paintView(); }
  var out='',shown=0,id=0;
  D.cities.forEach(function(c){
    if(selCity.size && !selCity.has(c.city)) return;
    var g=D.records.filter(function(r){
      if(r.city!==c.city) return false;
      if(selAuth.size && !selAuth.has(r.isAmanah?'a':'b')) return false;
      if(!areaPass(r,A)) return false;
      if(FDIST && r.district!==FDIST.d) return false;
      if(FREF && r.ref!==FREF) return false;
      if(selAct.size && !selAct.has(r.activity||'—')) return false;
      if(fWin){var k=daysLeft(r.deadline); if(k<0||k>+fWin) return false;}
      if(q){var hay=(r.ref+' '+r.title+' '+(r.district||'')+' '+(r.street||'')+' '+
        (r.authority||'')+' '+(r.activity||'')+' '+(r.sub||'')).toLowerCase();
        if(hay.indexOf(q)===-1) return false;}
      return true;});
    g.sort(SORT[sk]||SORT.dl);
    shown+=g.length;
    var urg=g.filter(function(r){var k=daysLeft(r.deadline);return k>=0&&k<=14;}).length;
    out+='<section class="city"><div class="chead"><h2>'+E(c.label)+'</h2>'+
      '<span class="pill">'+g.length+(g.length===c.n?'':' من '+c.n)+' فرصة</span>'+
      (urg?'<span class="pill warn">'+urg+' تغلق خلال 14 يوماً</span>':'')+'</div>';
    out+= g.length? '<div class="tw"><table>'+HEAD+'<tbody>'+
        g.map(function(r){return rowHTML(r,'d'+(id++));}).join('')+'</tbody></table></div>'
      : '<div class="tw"><div class="empty">لا توجد فرص مطابقة للتصفية الحالية في هذه المدينة.</div></div>';
    out+='</section>';});
  document.getElementById('sections').innerHTML=out;
  document.getElementById('count').innerHTML='المعروض: <b>'+shown+'</b> من '+D.total;
}

/* Jump from any view to the table row for one opportunity, filtered, expanded and
   scrolled into position. Every mark in every view is a handle onto the full record. */
/* ---------- multi-select filters ----------
   Each returns a Set of chosen values; empty Set means "all", so an untouched filter costs
   nothing. Counts beside each option are computed against the OTHER filters, so the reader
   can see what a choice would actually add before making it. */
function MultiSelect(host, cfg){
  var sel=new Set(), open=false;
  var btn=document.createElement('button');
  btn.type='button'; btn.setAttribute('aria-expanded','false'); btn.setAttribute('aria-haspopup','true');
  var panel=document.createElement('div');
  panel.className='mspanel'; panel.hidden=true;
  host.appendChild(btn); host.appendChild(panel);

  function label(){
    if(!sel.size) return cfg.allLabel;
    if(sel.size===1){
      var only=cfg.options.filter(function(o){return sel.has(o.value);})[0];
      return only? only.label : cfg.allLabel;
    }
    return cfg.someLabel;
  }
  function paintBtn(){
    btn.innerHTML='<span class="lbl">'+E(label())+'</span>'+
      (sel.size>1?'<span class="cnt">'+sel.size+'</span>':'')+'<span class="car">▾</span>';
  }
  function paintPanel(){
    var counts=cfg.counts ? cfg.counts(sel) : {};
    panel.innerHTML='<div class="tools"><button type="button" data-all>الكل</button>'+
      '<button type="button" data-none>إلغاء الكل</button></div>'+
      cfg.options.map(function(o){
        var c=counts[o.value];
        return '<label><input type="checkbox" value="'+E(o.value)+'"'+
          (sel.has(o.value)?' checked':'')+'><span>'+E(o.label)+'</span>'+
          (c==null?'':'<span class="n">'+c+'</span>')+'</label>';
      }).join('');
    function clearAll(){
      sel=new Set();
      Array.prototype.forEach.call(panel.querySelectorAll('input[type=checkbox]'),
        function(cb){cb.checked=false;});
      paintBtn(); cfg.onChange(sel); updateCounts();
    }
    panel.querySelector('[data-all]').addEventListener('click',clearAll);
    panel.querySelector('[data-none]').addEventListener('click',clearAll);
    Array.prototype.forEach.call(panel.querySelectorAll('input[type=checkbox]'),function(cb){
      cb.addEventListener('change',function(){
        if(cb.checked) sel.add(cb.value); else sel.delete(cb.value);
        paintBtn(); cfg.onChange(sel); updateCounts();
      });
    });
  }
  function updateCounts(){
    if(panel.hidden || !cfg.counts) return;
    var counts=cfg.counts(sel);
    Array.prototype.forEach.call(panel.querySelectorAll('label'),function(lb){
      var cb=lb.querySelector('input'), n=lb.querySelector('.n');
      if(!cb||!n) return;
      var c=counts[cb.value];
      n.textContent=(c==null?'0':c);
    });
  }
  var veil=null;
  function setOpen(v){
    open=v; panel.hidden=!v; btn.setAttribute('aria-expanded',v?'true':'false');
    if(v){
      paintPanel();
      if(matchMedia('(max-width:700px)').matches && !veil){
        veil=document.createElement('div'); veil.className='msveil';
        veil.style.display='block';
        veil.addEventListener('click',function(){setOpen(false);});
        document.body.appendChild(veil);
      }
      panel.scrollTop=0;
    } else if(veil){ veil.remove(); veil=null; }
  }
  btn.addEventListener('click',function(e){ e.stopPropagation(); setOpen(!open); });
  panel.addEventListener('click',function(e){ e.stopPropagation(); });
  document.addEventListener('click',function(){ if(open) setOpen(false); });
  document.addEventListener('keydown',function(e){ if(e.key==='Escape'&&open) setOpen(false); });
  paintBtn();
  return {get:function(){return sel;},
          clear:function(){
            sel=new Set();
            Array.prototype.forEach.call(panel.querySelectorAll('input[type=checkbox]'),
              function(cb){cb.checked=false;});
            paintBtn(); updateCounts();
          },
          active:function(){return sel.size>0;}};
}

/* Filter the table to one district. A district is the unit people actually shop in —
   clicking one should show everything in it, not a single reference. */
var FDIST=null, FREF=null;
function focusDistrict(name, cityLabel){
  if(!name) return;
  FREF=null;
  FDIST={d:name, c:cityLabel||null};
  document.querySelector('.views button[data-v="tbl"]').click();
  document.getElementById('q').value='';
  document.getElementById('fWin').value='';
  MS.city.clear(); MS.auth.clear(); MS.act.clear();
  aMin.value=0; aMax.value=1000; aUnk.checked=true; syncArea();
  render();
  var host=document.getElementById('sections');
  if(host) host.scrollIntoView({block:'start',behavior:'smooth'});
}
function clearDistrict(){ FDIST=null; FREF=null; render(); }
/* ---- export the visible opportunities as a CSV Google My Maps can import ----
   A URL cannot put several labelled pins on a Google map — there is no such parameter. My Maps
   CAN, from an imported CSV with latitude/longitude columns, and it labels each pin from a
   column you pick. `.kml` is not an allowed download extension here; `.csv` is, and My Maps
   reads it, so CSV is the route that actually works rather than the one that sounds best. */
function csvFor(rows){
  var head=['الاسم','رقم الفرصة','المدينة','الحي','خط العرض','خط الطول','المساحة م²',
            'المدة سنوات','آخر موعد','جهة الطرح','رابط الفرصة'];
  function cell(v){
    v=(v==null?'':String(v));
    return /[",\n]/.test(v) ? '"'+v.replace(/"/g,'""')+'"' : v;
  }
  var lines=[head.join(',')];
  rows.forEach(function(r){
    if(r.lat==null) return;
    lines.push([ (r.district||r.cityLabel)+' — '+r.ref, r.ref, r.cityLabel, r.district||'',
                 r.lat, r.lon, (r.area==null?'':Math.round(r.area)), r.years, r.deadline,
                 r.authority||'',
                 'https://furas.momah.gov.sa/opportunity/'+encodeURIComponent(r.ref)+'?type=Investment'
               ].map(cell).join(','));
  });
  return '\ufeff'+lines.join('\r\n');      /* BOM so Excel and Sheets read the Arabic */
}
function exportRows(rows, name){
  var csv=csvFor(rows), file=(name||'furas')+'.csv';
  if(!rows.length){ return; }
  if(window.claude && claude.use){
    claude.use('downloads').then(function(dl){
      if(!dl) return fallbackSave(csv,file);
      dl.save({filename:file, data:csv}).catch(function(e){
        if(e && e.code==='declined') return;
        fallbackSave(csv,file);
      });
    }).catch(function(){ fallbackSave(csv,file); });
  } else { fallbackSave(csv,file); }
}
function fallbackSave(text,file){
  try{
    var b=new Blob([text],{type:'text/csv;charset=utf-8'});
    var a=document.createElement('a');
    a.href=URL.createObjectURL(b); a.download=file;
    document.body.appendChild(a); a.click();
    setTimeout(function(){URL.revokeObjectURL(a.href); a.remove();},1500);
  }catch(e){}
}

function distChip(){
  var el=document.getElementById('dchip');
  if(!el) return;
  if(!FDIST && !FREF){ el.hidden=true; el.innerHTML=''; return; }
  el.hidden=false;
  if(FREF){
    var rec=D.records.filter(function(r){return r.ref===FREF;})[0];
    el.innerHTML='<span>فرصة: <b class="mono">'+E(FREF)+'</b>'+
      (rec&&rec.district?' · '+E(rec.district):'')+'</span>'+
      (rec&&rec.district?'<button type="button" id="dwiden">كل الحي ('+
        D.records.filter(function(r){return r.district===rec.district;}).length+')</button>':'')+
      '<button type="button" id="dclear" aria-label="إزالة التصفية">×</button>';
    var w=document.getElementById('dwiden');
    if(w) w.addEventListener('click',function(){ focusDistrict(rec.district, rec.cityLabel); });
  } else {
    var rows=D.records.filter(function(r){return r.district===FDIST.d;});
    var cl=(D.clusters||[]).filter(function(x){return x.district===FDIST.d;})[0];
    el.innerHTML='<span>الحي: <b>'+E(FDIST.d)+'</b>'+(FDIST.c?' · '+E(FDIST.c):'')+
      ' · '+rows.length+' فرصة</span>'+
      (cl?'<a class="chipbtn" target="_blank" rel="noopener" href="'+
        gmapsDistrict(cl.district,cl.cityLabel,cl.lat,cl.lon)+'">حدود الحي ↗</a>':'')+
      (function(){
        var u=gmapsPins(rows);
        if(u) return '<a class="chipbtn" target="_blank" rel="noopener" href="'+u+
          '" title="يفتح خرائط Google وعليها '+Math.min(rows.length,GMAPS_PIN_MAX)+
          ' دبابيس على مواقع الفرص. يرسم مساراً بينها — تجاهل الخط، الدبابيس هي المقصودة.">'+
          '📍 '+Math.min(rows.length,GMAPS_PIN_MAX)+' دبابيس على الخريطة ↗</a>';
        if(rows.length>GMAPS_PIN_MAX) return '<span class="chipnote">'+rows.length+
          ' فرصة — أكثر من '+GMAPS_PIN_MAX+'، استخدم التصدير</span>';
        return '';
      })()+
      '<button type="button" id="dcsv" title="ملف يُستورد في خرائطي (My Maps) فتظهر الفرص '+
      'كدبابيس مُسمّاة">تصدير الدبابيس</button>'+
      '<button type="button" id="dclear" aria-label="إزالة تصفية الحي">×</button>';
    var c=document.getElementById('dcsv');
    if(c) c.addEventListener('click',function(){
      exportRows(rows, (FDIST.c? FDIST.c+'-':'')+FDIST.d);
    });
  }
  document.getElementById('dclear').addEventListener('click',clearDistrict);
}
document.addEventListener('click',function(e){
  var h=e.target.closest('[data-dist]');
  if(h && !e.target.closest('a')) focusDistrict(h.getAttribute('data-dist'),
                                                h.getAttribute('data-distcity'));
});
document.addEventListener('keydown',function(e){
  if(e.key!=='Enter') return;
  var h=e.target.closest('[data-dist]');
  if(h && !e.target.closest('a')){ e.preventDefault();
    focusDistrict(h.getAttribute('data-dist'), h.getAttribute('data-distcity')); }
});

function focusRef(ref){
  if(!ref) return;
  /* A reference typed into the free-text search box is not a filter — it looks like the user
     searched, it survives nothing, and it cannot be cleared without knowing to empty the box.
     Use the same explicit, chip-backed filter the district click uses. */
  FDIST=null; FREF=ref;
  document.querySelector('.views button[data-v="tbl"]').click();
  document.getElementById('fWin').value='';
  MS.city.clear(); MS.auth.clear(); MS.act.clear();
  aMin.value=0; aMax.value=1000; aUnk.checked=true; syncArea();
  document.getElementById('q').value='';
  render();
  requestAnimationFrame(function(){
    var rows=document.querySelectorAll('#sections tr.row');
    for(var i=0;i<rows.length;i++){
      var c=rows[i].querySelector('td.ref');
      if(c && c.textContent.trim()===ref){
        if(rows[i].getAttribute('aria-expanded')!=='true') toggle(rows[i]);
        rows[i].scrollIntoView({block:'center',behavior:'smooth'});
        rows[i].classList.add('flash');
        setTimeout(function(t){return function(){t.classList.remove('flash');};}(rows[i]),1600);
        rows[i].focus({preventScroll:true});
        return;
      }
    }
    document.getElementById('count').innerHTML=
      'لم يظهر صف لهذه الفرصة: <b>'+E(ref)+'</b> — جرّب إعادة التعيين.';
  });
}
document.addEventListener('click',function(e){
  var h=e.target.closest('[data-ref]');
  if(h && !e.target.closest('a')) focusRef(h.getAttribute('data-ref'));
});
document.addEventListener('keydown',function(e){
  if(e.key!=='Enter') return;
  var h=e.target.closest('[data-ref]');
  if(h && !e.target.closest('a')){ e.preventDefault(); focusRef(h.getAttribute('data-ref')); }
});

function toggle(tr){
  var d=document.getElementById(tr.dataset.t); if(!d)return;
  var open=d.classList.toggle('hide')===false;
  tr.classList.toggle('open',open);
  tr.setAttribute('aria-expanded',open?'true':'false');}
var sec=document.getElementById('sections');
sec.addEventListener('click',function(e){
  if(e.target.closest('a'))return;
  var tr=e.target.closest('tr.row'); if(tr) toggle(tr);});
sec.addEventListener('keydown',function(e){
  if(e.key!=='Enter'&&e.key!==' ')return;
  var tr=e.target.closest('tr.row'); if(!tr)return; e.preventDefault(); toggle(tr);});
['q','fWin','sort'].forEach(function(i){
  document.getElementById(i).addEventListener('input',render);});
document.getElementById('reset').addEventListener('click',function(){
  ['q','fWin'].forEach(function(i){document.getElementById(i).value='';});
  MS.city.clear(); MS.auth.clear(); MS.act.clear();
  aMin.value=0; aMax.value=1000; aUnk.checked=true; syncArea();
  FDIST=null; FREF=null;
  render(); document.getElementById('q').focus();});
render();

/* ---- unlabelled records near the four cities: shown for judgement, never counted ---- */
(function(){
  var R=D.review||[]; var host=document.getElementById('review');
  if(!R.length){host.remove();return;}
  var rows=R.map(function(c){
    return '<tr>'+
      '<td class="mono">'+E(c.ref)+'</td>'+
      '<td>'+E(c.title)+'</td>'+
      '<td>'+E(c.near)+'<div class="km" style="color:var(--ink-2);font-size:.76rem">'
        +'على بُعد '+c.km.toFixed(1)+' كم</div></td>'+
      '<td>'+(c.amanah?E(c.amanah):NM)+'<div><span class="ag'+(c.agrees?'':' n')+'">'
        +(c.agrees?'الأمانة تُطابق المدينة':'لا تسنُدها أمانة')+'</span></div></td>'+
      '<td class="mono">'+E(c.deadline)+'</td>'+
      '<td>'+(c.months?arYears(Math.round(c.months/12*10)/10):NM)+'</td>'+
      '<td class="mono">'+(c.area?n(Math.round(c.area))+' م²':NM)+'</td>'+
      '<td>'+(c.lat==null?NM:'<a class="lnk" target="_blank" rel="noopener" href="'
        +'https://www.google.com/maps/search/?api=1&query='+c.lat+','+c.lon+'">خريطة</a>')+'</td>'+
      '<td><a class="lnk" target="_blank" rel="noopener" href="https://furas.momah.gov.sa/opportunity/'
        +encodeURIComponent(c.ref)+'?type=Investment">فتح</a></td></tr>';
  }).join('');
  host.innerHTML='<details class="rev"><summary>'+
    'سجلات بلا مدينة — للمراجعة اليدوية <span class="rc">'+R.length+'</span></summary>'+
    '<div class="rw"><p>لا تُحتسب هذه السجلات ضمن أرقام المدن أعلاه، وليست جزءاً من الـ'+D.total+'.</p>'+
    '<p>البوابة تترك حقل المدينة فارغاً في <b>'+n(D.blank)+'</b> '+
    'من أصل '+n(D.national)+' سجل وطني مفتوح؛ صفحة الفرصة نفسها لا تعرض مدينة، بل الأمانة فقط. '+
    'السجلات أدناه تقع ضمن '+(D.radiusKm||25)+' كم من أقرب فرصة <em>تُسمّيها البوابة صراحةً</em> '+
    'بإحدى مدننا الأربع — لذلك أُدرجت هنا حتى لا تضيع، لا لأنها مؤكَّدة.</p>'+
    '<p><b>لماذا لا تُحتسب:</b> القرب وحده لا يكفي. أحد هذه السجلات يبعد ٧ كم عن نقطة مُسمّاة '+
    '«الرياض» لكنه في <em>محافظة حريملاء</em>، والأمانة تغطي المنطقة لا المدينة — ١٠٤ سجلات '+
    'بلا مدينة تحمل إحدى أماناتنا الأربع وأغلبها يبعد ٥٠–٣٣٠ كم. '+
    'إسنادُ مدينة لا تقولها البوابة سيكون تلفيقاً، لذا تُترك للحكم البشري.</p>'+
    '<div class="revwrap"><table><thead><tr><th>رقم الفرصة</th><th>العنوان</th>'+
    '<th>أقرب مدينة مُسمّاة</th><th>جهة الطرح</th><th>آخر موعد</th><th>المدة</th>'+
    '<th>المساحة</th><th>الموقع</th><th>الصفحة</th></tr></thead><tbody>'+rows+
    '</tbody></table></div></div></details>';
})();

/* keep the sticky table header docked exactly under the controls, at any width */
var ctrl=document.querySelector('.controls');
function syncCtrl(){
  var h=Math.round(ctrl.getBoundingClientRect().height);
  document.documentElement.style.setProperty('--ctrl-h',h+'px');}
syncCtrl();
if(window.ResizeObserver){new ResizeObserver(syncCtrl).observe(ctrl);}
else{addEventListener('resize',syncCtrl);}
})();
</script>
"""
NATIONAL = PAY.get("nationalOpenInvestment")
_nat = (f"الإجمالي الوطني للفرص طويلة الأجل المفتوحة عند اللقطة: {NATIONAL:,} فرصة. "
        f"المدن الأربع = {payload['total']} ({payload['total']/NATIONAL:.1%})."
        if NATIONAL else
        f"المدن الأربع: {payload['total']} فرصة. لم يُقَس الإجمالي الوطني في هذه الجولة.")
DATA = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
import collections
_yr = collections.Counter(r["years"] for r in recs if r["months"])
_mode, _moden = (_yr.most_common(1)[0] if _yr else (0, 0))
FACTS = {
  "__N__":      str(len(recs)),
  "__NDUR__":   str(sum(1 for r in PAY["records"] if r.get("_card"))),
  "__MODEY__":  ("%g سنة" % _mode),
  "__MODEN__":  str(_moden),
  "__NPART__":  str(sum(1 for r in recs if not r["isAmanah"])),
  "__NGEO__":   str(sum(1 for r in recs if r["lat"] is not None)),
  "__NKUR__":   str(sum(1 for r in PAY["records"]
                        if any("كراس" in (d.get("name") or "") for d in (r.get("_docs") or [])))),
  "__NAQD__":   str(sum(1 for r in PAY["records"]
                        if any("عقد" in (d.get("name") or "") for d in (r.get("_docs") or [])))),
  "__NAREA__":  str(sum(1 for r in recs if r["area"] is None)),
  "__NPRICE__": str(sum(1 for r in recs if r["price"] is None)),
  "__NENV__":   str(sum(1 for r in recs if r["envelopes"] is None)),
}
_body = BODY.replace("__NATIONAL__", _nat)
for k, v in FACTS.items(): _body = _body.replace(k, v)
assert "__N" not in _body, "unsubstituted placeholder left in the page"
_head = CSS
if A.standalone and A.title:
    _head = re.sub(r"<title>.*?</title>", "<title>" + A.title + "</title>", _head, count=1)

if A.standalone:
    # A local file gets no wrapper, so supply the whole document plus the small reset the
    # Artifact host would otherwise inject. Fonts already carry a real fallback stack, so
    # the page stays correct with no network.
    html = ('<!doctype html>\n<html lang="ar" dir="rtl">\n<head>\n'
            '<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
            '<meta name="color-scheme" content="light dark">\n'
            + _head +
            '\n</head>\n<body>\n' + _body + JS.replace("__DATA__", DATA) +
            '\n</body>\n</html>\n')
else:
    html = _head + _body + JS.replace("__DATA__", DATA)
open(A.out, "w", encoding="utf-8").write(html)
print(f"wrote {A.out} · {len(html):,} bytes · {payload['total']} records · "
      f"{payload['totalUrgent']} closing within 14 days")
