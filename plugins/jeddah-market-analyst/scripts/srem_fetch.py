# -*- coding: utf-8 -*-
"""البورصة العقارية — Jeddah weekly deal statistics. Writes srem.json.

Exit codes:  0 ok · 2 verification failed · 3 network (host named on stderr)

What the public API gives (verified 2026-09-27, anonymous, no Nafath):
  POST Dashboard/GetAreaInfo  {"periodCategory":"W","period":1,"areaType":"C","areaSerial":37528,"cityCode":37528}
    Data.Total        → Count, TotalPrices, TotalAreas, Min/Max/AveragePrice (SAR/m²), BestBid, BestAsk
    Data.Stats[]      → one row per day (AggregationDate, TotalCount, TotalPrice, TotalArea, ...)
    Data.Transactions → the LATEST 5 DEALS ONLY (live ticker) — not the week's deals
  areaType "D" + areaSerial=<DistrictCode> → same shape for one district.
What it does NOT give: a per-deal list, or any split by property type in the aggregates.
"""
import argparse, json, sys, time, datetime
from config import (SREM_API, SREM_INQUIRY, JEDDAH_CITY_CODE, SREM_PERIOD, SREM_RETRIES,
                    normalize_ar)
from net import post_json, get_json, Blocked


def area_info(area_type, serial, retries=SREM_RETRIES):
    body = {"periodCategory": SREM_PERIOD, "period": 1, "areaType": area_type,
            "areaSerial": serial, "cityCode": JEDDAH_CITY_CODE}
    last = None
    for i in range(retries):
        st, js = post_json(SREM_API + "Dashboard/GetAreaInfo", body, tries=2)
        if js.get("IsSuccess") and js.get("Data"):
            return js["Data"], i + 1
        last = ((js.get("ErrorDetails") or [{}])[0].get("Exception") or str(js)[:160])
        time.sleep(1.5)
    return None, f"{retries} attempts: {str(last)[:160]}"


def search_address(term):
    st, js = get_json(SREM_INQUIRY, {"Term": term}, tries=3)
    ents = ((js or {}).get("Data") or {}).get("Entities") or []
    return [e for e in ents if e.get("CityCode") == JEDDAH_CITY_CODE and e.get("DistrictCode")]


def discover_districts(seed_names, cached=None):
    """SREM's district gazetteer is deed-based: one aqar district can be several SREM districts
    ("المروة", "المروة / 2") and names carry free text ("البوادى على يمين الصاعد الى المدينة...").
    SearchAddress returns at most 10 entities, so search each seed name plus spelling variants.
    `cached` (from the previous snapshot) is merged in so a district that stops matching a
    search term is not silently lost."""
    found = {int(k): v for k, v in (cached or {}).items()}
    for n in seed_names:
        base = n.replace("حي ", "").replace("-", " ").strip()
        variants = [f"حي {base}", base, base.replace("ة", "ه"),
                    base[:-1] + "ى" if base.endswith("ي") else base,
                    base[2:] if base.startswith("ال") else base]
        for v in dict.fromkeys(variants):
            try:
                hits = search_address(v)
            except Blocked:
                raise
            except Exception:
                hits = []
            for e in hits:
                found[int(e["DistrictCode"])] = e.get("DistrictName") or ""
            if hits:
                break
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed-districts", help="json list of district names (from aqar)")
    ap.add_argument("--cached-gazetteer", help="json {code: name} from the previous snapshot")
    ap.add_argument("--skip-districts", action="store_true")
    a = ap.parse_args()

    run_at = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3)))
    out = {"source": "البورصة العقارية", "fetched_at": run_at.isoformat(timespec="seconds"),
           "period": SREM_PERIOD, "city_code": JEDDAH_CITY_CODE, "gates": [], "districts": []}
    try:
        city, att = area_info("C", JEDDAH_CITY_CODE)
    except Blocked as e:
        print(f"NETWORK: host blocked or unreachable → {e.host}", file=sys.stderr)
        sys.exit(3)
    if city is None:
        out["error"] = f"city query failed: {att}"
        json.dump(out, open(a.out, "w"), ensure_ascii=False, indent=1)
        print("VERIFY FAIL: Jeddah city aggregate never answered —", att, file=sys.stderr)
        sys.exit(2)

    total, stats, ticker = city.get("Total") or {}, city.get("Stats") or [], city.get("Transactions") or []
    out.update(total=total, daily=stats, ticker=ticker, city_attempts=att)
    days = sorted(s["AggregationDate"][:10] for s in stats)
    out["window"] = {"from": days[0] if days else None, "to": days[-1] if days else None, "days": len(days)}

    # Gate 1 — the daily rows must add up to the headline total (they did exactly on 27 Sep: 346).
    sc, sp = sum(s.get("TotalCount") or 0 for s in stats), sum(s.get("TotalPrice") or 0 for s in stats)
    ok1 = sc == total.get("Count") and abs(sp - (total.get("TotalPrices") or 0)) <= max(1, 0.001 * sp)
    out["gates"].append({"gate": "daily rows sum to weekly total", "ok": ok1,
                         "detail": f"count {sc} vs {total.get('Count')}, value {sp:,.0f} vs {total.get('TotalPrices')}"})
    # Gate 2 — every stat/ticker row is Jeddah (catches the Riyadh 'طريق جدة السريع' trap).
    bad = [s.get("AreaName") for s in stats if s.get("AreaSerial") not in (JEDDAH_CITY_CODE,)]
    bad += [t.get("CityName") for t in ticker if normalize_ar(t.get("CityName")) != normalize_ar("جدة")]
    out["gates"].append({"gate": "all rows are Jeddah", "ok": not bad, "detail": ", ".join(map(str, bad[:5]))})

    if not a.skip_districts:
        seeds = json.load(open(a.seed_districts)) if a.seed_districts else []
        cached = json.load(open(a.cached_gazetteer)) if a.cached_gazetteer else {}
        gaz = discover_districts(seeds, cached)
        out["gazetteer"] = {str(k): v for k, v in sorted(gaz.items())}
        failed = []
        for code, name in sorted(gaz.items()):
            d, att = area_info("D", code, retries=5)
            if d is None:
                failed.append({"code": code, "name": name, "why": att})
                continue
            t = d.get("Total") or {}
            out["districts"].append({"code": code, "name": name, "count": t.get("Count") or 0,
                                     "value": t.get("TotalPrices") or 0, "area": t.get("TotalAreas") or 0,
                                     "avg_ppm": t.get("AveragePrice"), "min_ppm": t.get("MinPrice"),
                                     "max_ppm": t.get("MaxPrice"), "attempts": att})
            time.sleep(0.3)
        out["district_failures"] = failed
        dsum = sum(x["count"] for x in out["districts"])
        cov = dsum / total["Count"] if total.get("Count") else None
        out["district_coverage"] = cov
        # Gate 3 — district deals can never exceed the city total. (Under-coverage is expected
        # and reported; over-coverage means double counting or a non-Jeddah district.)
        out["gates"].append({"gate": "district sum ≤ city total", "ok": dsum <= (total.get("Count") or 0),
                             "detail": f"{dsum} of {total.get('Count')} deals mapped to districts"})

    json.dump(out, open(a.out, "w"), ensure_ascii=False, indent=1)
    fails = [g for g in out["gates"] if not g["ok"]]
    for g in out["gates"]:
        print(("PASS " if g["ok"] else "FAIL ") + g["gate"] + " — " + g["detail"])
    sys.exit(2 if fails else 0)


if __name__ == "__main__":
    main()
