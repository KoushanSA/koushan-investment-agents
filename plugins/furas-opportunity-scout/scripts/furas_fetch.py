# -*- coding: utf-8 -*-
"""Discovery + enrichment. Writes data.json. Exits non-zero if a verification gate fails."""
import json, re, sys, time, html, argparse, threading, queue, datetime, math
import urllib.request, urllib.parse, urllib.error
from config import (PROXY, SERVICE, DETAIL, CITY_STORED, CITY_DISPLAY, FIELDS,
                    INCLUDE_TYPES, SANITY_MIN, SANITY_MAX, UA, normalize_ar, AMANA_TO_CITY)

def get(url, tries=4, timeout=60):
    last = None
    for i in range(tries):
        try:
            rq = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "ar"})
            with urllib.request.urlopen(rq, timeout=timeout) as r:
                return r.status, r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code == 404: return 404, ""
            last = e
        except Exception as e:
            last = e
        time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"failed after {tries} tries: {url[:90]} :: {last}")

def q(params):
    return get(PROXY + SERVICE + "/query?f=json&" + params)[1]

def base_where(now_iso):
    """Everything qualifying nationally, before the city filter."""
    types = ",".join("'%s'" % t for t in INCLUDE_TYPES)
    return (f"LASTRFPSELLDATE >= DATE '{now_iso}' "
            f"AND OPPORTUNITYACTIVESTATUS='Announced' "
            f"AND OPPORTUNITYTYPE IN ({types})")

CANDIDATE_KM = 25.0

def _km(a, b, c, d):
    return math.hypot((a - c) * 111.0, (b - d) * 111.0 * math.cos(math.radians((a + c) / 2)))

def fetch_national(now_iso):
    out, off = [], 0
    while True:
        p = ("where=" + urllib.parse.quote(base_where(now_iso)) + "&outFields=" + ",".join(FIELDS) +
             "&returnGeometry=true&outSR=4326&orderByFields=OPPORTUNITYID"
             f"&resultOffset={off}&resultRecordCount=500")
        js = json.loads(q(p))
        if "error" in js: raise RuntimeError("ArcGIS error: %s" % js["error"])
        feats = js.get("features", [])
        for f in feats:
            a = dict(f["attributes"]); g = f.get("geometry") or {}
            x, y = g.get("x"), g.get("y")
            if x is None and g.get("rings"): x, y = g["rings"][0][0][:2]
            a["_lat"], a["_lon"] = y, x
            out.append(a)
        if len(feats) < 500: break
        off += 500
        if off > 8000: break
    return out

def find_candidates(now_iso, labelled):
    """About a third of open national records carry NO city at all (600 of 1,874 on
    2026-08-30) -- the portal's own detail page shows only the amanah for them. Some sit
    inside our four cities, so filtering on CITYNAME alone silently drops real opportunities.

    These are NOT merged into the city counts. Geography cannot settle them: a record 7 km
    from a labelled 'الرياض' point turned out to be in محافظة حريملاء, and the amanah is
    region-wide, not city-wide (104 blank records carry one of our four amanahs, and all but
    a handful are 50-330 km away). Reporting them as 'جدة' would be inventing a label the
    portal does not assert.

    So: surface them separately for a human to judge. Returns records annotated with
    _nnCity / _nnKm (distance to the nearest record the portal DOES label with that city)
    and _amanahCity, sorted nearest first."""
    pts = {}
    for stored in CITY_STORED.values():
        pts[stored] = [(r["_lat"], r["_lon"]) for r in labelled
                       if r.get("CITYNAME") == stored and r.get("_lat") is not None]
    known = {r["OPPORTUNITYID"] for r in labelled}
    nat = fetch_national(now_iso)
    n_blank = sum(1 for r in nat if not str(r.get("CITYNAME") or "").strip())
    cands = []
    for r in nat:
        if r["OPPORTUNITYID"] in known: continue
        if str(r.get("CITYNAME") or "").strip(): continue      # labelled, just not our city
        if r.get("_lat") is None: continue
        km, city = min((min(_km(r["_lat"], r["_lon"], p, o) for p, o in v), s)
                       for s, v in pts.items() if v)
        if km > CANDIDATE_KM: continue
        r["_nnCity"], r["_nnKm"] = city, round(km, 2)
        r["_amanahCity"] = AMANA_TO_CITY.get(str(r.get("AMANA") or "").strip())
        cands.append(r)
    cands.sort(key=lambda r: r["_nnKm"])
    return cands, n_blank, len(nat)

DATE_FIELDS = ("LASTRFPSELLDATE", "ENDDATE", "ENVELOPESOPENDATE", "STARTDATE", "LASTBIDATE")

def normalize_dates(recs):
    """ArcGIS returns date fields as epoch-MILLISECONDS (UTC). Every consumer -- dashboard,
    workbook, diff -- expects YYYY-MM-DD. Convert once, here, for records from BOTH fetch
    paths. Leaving this out silently produces a dashboard that cannot parse a deadline and a
    diff that reports every row as changed."""
    for r in recs:
        for f in DATE_FIELDS:
            v = r.get(f)
            if v in (None, "", 0): continue
            if isinstance(v, str) and len(v) >= 10 and v[4] == "-": continue   # already ISO
            try: ms = int(float(v))
            except (TypeError, ValueError): continue
            r[f] = datetime.datetime.utcfromtimestamp(ms / 1000).strftime("%Y-%m-%d")
    return recs

def where_clause(now_iso):
    cities = ",".join("'%s'" % c for c in CITY_STORED.values())
    types  = ",".join("'%s'" % t for t in INCLUDE_TYPES)
    return (f"LASTRFPSELLDATE >= DATE '{now_iso}' "
            f"AND OPPORTUNITYACTIVESTATUS='Announced' "
            f"AND OPPORTUNITYTYPE IN ({types}) "
            f"AND CITYNAME IN ({cities})")

def fetch_records(now_iso):
    w = where_clause(now_iso)
    out, off = [], 0
    while True:
        p = ("where=" + urllib.parse.quote(w) + "&outFields=" + ",".join(FIELDS) +
             "&returnGeometry=true&outSR=4326&orderByFields=CITYNAME,OPPORTUNITYID"
             f"&resultOffset={off}&resultRecordCount=500")
        js = json.loads(q(p))
        if "error" in js: raise RuntimeError("ArcGIS error: %s" % js["error"])
        feats = js.get("features", [])
        for f in feats:
            a = dict(f["attributes"]); g = f.get("geometry") or {}
            x, y = g.get("x"), g.get("y")
            if x is None and g.get("rings"): x, y = g["rings"][0][0][:2]
            a["_lat"], a["_lon"] = y, x
            out.append(a)
        if len(feats) < 500: break
        off += 500
        if off > 5000: break
    return out

ATT = re.compile(r'href="(/opportunity/attachment/[^"]+)"')
CARD = re.compile(r'([\d,\.]+)\s*م²\s*مساحة\s*([\d,]+)\s*(شهر|سنة|يوم)\s*مدة العقد\s*([\d,]+)\s*سعر الكراسة')

def enrich(recs, workers=8):
    qq = queue.Queue(); [qq.put(r) for r in recs]
    lock = threading.Lock(); done = [0]
    def work():
        while True:
            try: r = qq.get_nowait()
            except queue.Empty: return
            ref = r["OPPORTUNITYID"]
            try:
                st, h = get(DETAIL.format(ref=urllib.parse.quote(ref)), tries=3, timeout=45)
            except Exception:
                st, h = 0, ""
            r["_detail_status"] = st; r["_docs"] = []; r["_card"] = None
            if st == 200 and h:
                seen = set()
                for m in ATT.finditer(h):
                    p = html.unescape(m.group(1))
                    if p in seen: continue
                    seen.add(p)
                    parts = p.split("/")
                    nm = urllib.parse.unquote(parts[5]) if len(parts) > 5 else "ملف"
                    if "خطأ" in nm or "عذرا" in nm: continue      # portal's own archive errors
                    r["_docs"].append({"name": nm.strip(),
                                       "url": "https://furas.momah.gov.sa" + urllib.parse.quote(p, safe="/")})
                t = html.unescape(re.sub(r"<(script|style)[^>]*>.*?</\1>", "", h, flags=re.S | re.I))
                c = CARD.search(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t)))
                if c: r["_card"] = {"area": c.group(1), "dur": c.group(2), "unit": c.group(3), "price": c.group(4)}
            with lock:
                done[0] += 1
                if done[0] % 25 == 0: print(f"   enriched {done[0]}/{len(recs)}", flush=True)
            qq.task_done()
    ts = [threading.Thread(target=work, daemon=True) for _ in range(workers)]
    [t.start() for t in ts]; [t.join() for t in ts]

DL_BASE = "https://furas.momah.gov.sa/sites/default/files/"

def _static_url(att_url):
    """The portal's own attachment link NEVER serves the file — it answers 200 with the
    page shell, which is why a button built on it lands the user on the home page. The file,
    when it exists at all, sits at a flat static path derived from the link's fileId and
    filename. Parse the PATH (the stored url is absolute and percent-encoded) and keep the
    filename exactly, trailing space included."""
    seg = [urllib.parse.unquote(x) for x in urllib.parse.urlparse(att_url).path.split("/") if x]
    if len(seg) < 6 or seg[0] != "opportunity" or seg[1] != "attachment":
        return None
    fid, name, ext = seg[3], seg[4], seg[5]
    return DL_BASE + urllib.parse.quote(f"{fid}_{name}.{ext}", safe="")

def probe_downloads(recs, workers=4):
    """Measured 17 Sep 2026: only 21 of 189 listed documents actually resolve (the rest are a
    hard 404 — the portal's attachment archive is incomplete). So every download link is
    VERIFIED here before it is offered, and a document that does not resolve simply gets no
    download button. Never ship an unverified attachment link: a dead one is
    indistinguishable from a live one to the reader, and that mistake was shipped once."""
    jobs = []
    for r in recs:
        for d in (r.get("_docs") or []):
            u = _static_url(d.get("url", ""))
            if u: jobs.append((d, u))
    if not jobs: return 0
    lock = threading.Lock(); idx = [0]; hits = [0]
    def work():
        while True:
            with lock:
                if idx[0] >= len(jobs): return
                d, u = jobs[idx[0]]; idx[0] += 1
            head = b""
            try:
                rq = urllib.request.Request(u, headers={"User-Agent": UA, "Range": "bytes=0-7"})
                with urllib.request.urlopen(rq, timeout=45) as resp:
                    head = resp.read(8)
            except Exception:
                head = b""
            if head[:4] == b"%PDF":
                d["dl"] = u
                with lock: hits[0] += 1
            time.sleep(0.8)          # the host rate-limits a fast burst into blanket failure
    ts = [threading.Thread(target=work) for _ in range(workers)]
    [t.start() for t in ts]; [t.join() for t in ts]
    return hits[0]

def verify(recs):
    """Hard gates. Any failure returns a reason string; caller must not publish."""
    fails = []
    if not recs: return ["zero records returned — filter or endpoint failure"]
    ids = [r["OPPORTUNITYID"] for r in recs]
    if any(not i for i in ids): fails.append("record(s) with no رقم الفرصة")
    if len(set(ids)) != len(ids): fails.append(f"{len(ids)-len(set(ids))} duplicate رقم الفرصة")
    bad = [r for r in recs if r.get("OPPORTUNITYTYPE") not in INCLUDE_TYPES]
    if bad: fails.append(f"{len(bad)} records of an excluded type leaked through")
    per = {}
    for r in recs: per[r["CITYNAME"]] = per.get(r["CITYNAME"], 0) + 1
    for stored in CITY_STORED.values():
        if per.get(stored, 0) == 0:
            fails.append(f"city '{stored}' returned 0 — check Arabic normalisation before trusting this")
    if not (SANITY_MIN <= len(recs) <= SANITY_MAX):
        fails.append(f"total {len(recs)} outside sanity band {SANITY_MIN}-{SANITY_MAX}")
    # duration cross-check against the portal's own detail card
    checked = [r for r in recs if r.get("_card")]
    mism = [r["OPPORTUNITYID"] for r in checked
            if r["_card"]["unit"] != "شهر"
            or int(r["_card"]["dur"].replace(",", "")) != int(r.get("DURATION") or 0)]
    if checked and len(mism) > len(checked) * 0.02:
        fails.append(f"DURATION disagrees with portal card on {len(mism)}/{len(checked)} — months assumption may have changed")
    badd = [r["OPPORTUNITYID"] for r in recs
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(r.get("LASTRFPSELLDATE") or ""))]
    if badd: fails.append(f"{len(badd)} records with a non-ISO LASTRFPSELLDATE "
                          f"(e.g. {badd[0]}) — normalize_dates() did not run")
    nogeo = [r for r in recs if r.get("_lat") is None]
    if len(nogeo) > len(recs) * 0.1: fails.append(f"{len(nogeo)} records missing coordinates")
    return fails

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data.json")
    ap.add_argument("--skip-enrich", action="store_true")
    a = ap.parse_args()
    now = datetime.datetime.now()
    now_iso = now.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[1/3] discovering (as of {now_iso}) …", flush=True)
    recs = fetch_records(now_iso)
    print(f"      {len(recs)} with a matching city label", flush=True)
    cands, n_blank, n_nat = find_candidates(now_iso, recs)
    if cands:
        print(f"      {len(cands)} blank-city record(s) within {CANDIDATE_KM:.0f} km "
              f"— listed for manual review, NOT counted", flush=True)
    normalize_dates(recs); normalize_dates(cands)
    recs.sort(key=lambda r: (str(r.get("CITYNAME") or ""), str(r.get("OPPORTUNITYID") or "")))
    print(f"      {len(recs)} qualifying records total", flush=True)
    if not a.skip_enrich:
        print("[2/3] enriching from detail pages …", flush=True)
        enrich(recs)
        enrich(cands)
        print("      verifying document downloads …", flush=True)
        nd = probe_downloads(recs)
        tot = sum(len(r.get("_docs") or []) for r in recs)
        print(f"      {nd} of {tot} documents are directly downloadable", flush=True)
    print("[3/3] verifying …", flush=True)
    fails = verify(recs)
    payload = {"asOf": now.strftime("%Y-%m-%d"), "generatedAt": now_iso,
               "total": len(recs), "records": recs, "candidates": cands,
               "candidateRadiusKm": CANDIDATE_KM, "blankCity": n_blank,
               "nationalOpenInvestment": n_nat, "verification": fails}
    json.dump(payload, open(a.out, "w", encoding="utf-8"), ensure_ascii=False)
    if fails:
        print("VERIFICATION FAILED:"); [print("  !", f) for f in fails]
        print(f"\nWrote {a.out} for inspection. Do NOT publish this run.")
        sys.exit(2)
    per = {}
    for r in recs: per[CITY_DISPLAY.get(r["CITYNAME"], r["CITYNAME"])] = per.get(CITY_DISPLAY.get(r["CITYNAME"], r["CITYNAME"]), 0) + 1
    print("OK ·", ", ".join(f"{k} {v}" for k, v in per.items()), f"· total {len(recs)}")
    print(f"Wrote {a.out}")

def diagnose(err):
    m = str(err)
    print("\nSCAN FAILED — not publishing.\n")
    if "403" in m and "gisapps" in m:
        print("  Cause: the opportunities API host is blocked from this environment.")
        print("  Fix:   allowlist ONE hostname for network access:\n")
        print("           gisapps.balady.gov.sa\n")
        print("  This scan dials that host and nothing else. gisOppertunities.momra.gov.sa")
        print("  appears inside the request URL and in proxy logs, but it is fetched")
        print("  SERVER-SIDE by balady's proxy — this environment never connects to it, so")
        print("  it does not need allowlisting. Do not ask for it; a broader request than")
        print("  necessary is more likely to stall.")
        print()
        print("  Note:  the allowlist matches exact hostnames — a parent domain such as")
        print("         balady.gov.sa does NOT cover this subdomain. Confirm with:")
        print("           curl -o /dev/null -w '%{http_code}' \\")
        print("             https://gisapps.balady.gov.sa/opportunities/index.html")
        print("         Expect 200. A 403 means the entry has not applied.")
    elif "furas.momah.gov.sa" in m:
        print("  Cause: the portal detail host is unreachable.")
        print("  Fix:   allowlist furas.momah.gov.sa, or re-run — this host is")
        print("         intermittently slow and the fetcher already retries 4 times.")
    else:
        print("  Cause:", m[:400])
    print("\n  Nothing was published. The previous dashboard is unchanged.")

if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        diagnose(e)
        sys.exit(3)
