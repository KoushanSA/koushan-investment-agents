# -*- coding: utf-8 -*-
"""Merge srem.json + aqar.json (+ previous snapshot) into the run's deliverables:
   data.json      — everything the dashboard needs (metrics, districts, opportunities, diff, gates)
   listings.csv   — one row per listing / deal / district-aggregate, the brief's schema (UTF-8 BOM)
   snapshot.json  — compact baseline for the next run (metrics history + id/date cache)
   facts.json     — the numbers the Arabic report may quote, each with its source

Rule: nothing here estimates. A metric without enough data is emitted as None with a reason,
and the report must say so instead of filling the gap."""
import argparse, csv, json, math, re, statistics, datetime
from codec import pack_dates, unpack_dates
from config import (NA, SRC_SREM, SRC_AQAR, MIN_SAMPLE, JEDDAH_CITY_CODE, normalize_ar, district_key)

TITLE_DISTRICT = re.compile(r"حي\s+([^,،]+)[,،]")


def ppm(price, area):
    try:
        p, a = float(price), float(area)
    except (TypeError, ValueError):
        return None
    return p / a if p > 0 and a > 0 else None


def tukey(vals, k=3.0):
    """Split values into kept / excluded by a wide (3×IQR) Tukey fence on log scale.
    Placeholder prices (1 SAR, 1,111,111 for 1 m²) otherwise dominate a mean."""
    if len(vals) < 8:
        return vals, []
    lv = sorted(math.log(v) for v in vals)
    q1, q3 = lv[len(lv) // 4], lv[(3 * len(lv)) // 4]
    lo, hi = q1 - k * (q3 - q1), q3 + k * (q3 - q1)
    keep = [v for v in vals if lo <= math.log(v) <= hi]
    drop = [v for v in vals if not (lo <= math.log(v) <= hi)]
    return keep, drop


def summarize(vals):
    vals = [v for v in vals if v]
    keep, drop = tukey(vals)
    if len(keep) < MIN_SAMPLE:
        return {"n": len(keep), "mean": None, "median": None, "excluded": len(drop),
                "reason": f"عينة غير كافية: {len(keep)} من حد أدنى {MIN_SAMPLE}"}
    return {"n": len(keep), "mean": round(statistics.fmean(keep)), "median": round(statistics.median(keep)),
            "p25": round(statistics.quantiles(keep, n=4)[0]), "p75": round(statistics.quantiles(keep, n=4)[2]),
            "excluded": len(drop)}


def map_srem_to_aqar(srem_names, aqar_names):
    """SREM district → aqar district by normalised prefix, longest aqar name wins.
    'المروة / 2' → المروة ; 'حى السلامة غرب طريق المدينة…' → السلامة ; unmapped → None (kept separately)."""
    akeys = sorted(((normalize_ar(a), a) for a in aqar_names), key=lambda x: -len(x[0]))
    out = {}
    for s in srem_names:
        ns = normalize_ar(re.sub(r"\s*/\s*\d+", "", s))
        hit = None
        for ak, a in akeys:
            for cand in (ak, re.sub(r"^ال", "", ak)):
                if cand and (ns == cand or ns.startswith(cand + " ") or ns.startswith("ال" + cand + " ")
                             or ns == "ال" + cand or re.sub(r"^ال", "", ns) == cand):
                    hit = a
                    break
            if hit:
                break
        out[s] = hit
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--srem", required=True, help="path; may be missing when البورصة was unreachable")
    ap.add_argument("--aqar", required=True)
    ap.add_argument("--previous")
    ap.add_argument("--outdir", required=True)
    a = ap.parse_args()
    A = json.load(open(a.aqar))
    try:
        S = json.load(open(a.srem))
    except (FileNotFoundError, json.JSONDecodeError):
        # البورصة unreachable this run (cloud is refused by MOJ; Chrome fallback unavailable).
        # Publish the aqar half with every البورصة metric as None — never reuse last run's figures.
        S = {"gates": [{"gate": "البورصة العقارية متاحة في هذا التشغيل", "ok": False,
                        "detail": "تعذر الوصول إلى البورصة العقارية من السحابة ومن Chrome"}], "districts": []}
    P = json.load(open(a.previous)) if a.previous else None
    run_at = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=3)))
    L = A["listings"]

    # ── aqar rows ──
    for r in L:
        r["ppm"] = ppm(r.get("price"), r.get("area"))
        m = TITLE_DISTRICT.search(r.get("title") or "")
        r["title_district"] = m.group(1).strip() if m else None
        r["district"] = r.get("url_district") or (r.get("locality") or "").replace("حي ", "") or None
        r["district_mismatch"] = bool(r["title_district"] and r["district"] and
                                      district_key(r["title_district"]) != district_key(r["district"]))
    sale = [r for r in L if r["tx"] == "بيع"]
    rent = [r for r in L if r["tx"] == "إيجار"]
    types = sorted({r["type"] for r in L})

    city_aqar = {"active_total": len(L), "sale": len(sale), "rent": len(rent),
                 "by_type": {}, "market_total_reported": A.get("market_total"), "coverage": A.get("coverage")}
    for t in types:
        city_aqar["by_type"][t] = {
            "sale_n": sum(1 for r in sale if r["type"] == t), "rent_n": sum(1 for r in rent if r["type"] == t),
            "sale_ppm": summarize([r["ppm"] for r in sale if r["type"] == t]),
            "rent_ppm_year": summarize([r["ppm"] for r in rent if r["type"] == t]),
        }

    # ── SREM city ──
    T = S.get("total") or {}
    srem_city = {"deals": T.get("Count"), "value": T.get("TotalPrices"), "area": T.get("TotalAreas"),
                 "avg_ppm": T.get("AveragePrice"), "min_ppm": T.get("MinPrice"), "max_ppm": T.get("MaxPrice"),
                 "best_bid": T.get("BestBid"), "window": S.get("window"), "daily": [
                     {"date": d["AggregationDate"][:10], "count": d["TotalCount"], "value": d["TotalPrice"],
                      "area": d["TotalArea"], "avg_ppm": d.get("AveragePrice")} for d in sorted(
                         S.get("daily") or [], key=lambda x: x["AggregationDate"])],
                 "land_vs_apartment": None,
                 "land_vs_apartment_reason": "البورصة العقارية لا تنشر تقسيم الصفقات حسب نوع العقار في إحصائياتها العامة"}
    supply = None
    if srem_city["deals"] is not None and city_aqar["sale"]:
        supply = city_aqar["sale"] / (city_aqar["sale"] + srem_city["deals"])

    # ── districts ──
    aqar_d = {}
    for r in L:
        if r["district"]:
            aqar_d.setdefault(r["district"], []).append(r)
    smap = map_srem_to_aqar([d["name"] for d in S.get("districts", [])], list(aqar_d))
    srem_by_aqar, srem_unmapped, srem_dupes = {}, [], []
    # The البورصة answers several gazetteer entries with the SAME aggregate (28 Sep 2026:
    # «المروة» = «المروة / 2», «المنار» = «المنار / 3», and «البغدادية الغربية» = «البغدادية الشرقية / 2»,
    # 1 deal · 3,500,000 · 821 m² each). Summing them double counts. Identical (count, value, area)
    # rows are one aggregate: kept once when they map to one aqar district, and withheld from
    # district figures (reported) when they map to different districts — we cannot tell which.
    groups = {}
    for d in S.get("districts", []):
        if d["count"]:
            groups.setdefault((d["count"], d["value"], d["area"]), []).append(d)
    for key, ds in groups.items():
        tgts = {smap.get(d["name"]) for d in ds}
        names = [d["name"] for d in ds]
        if len(ds) > 1:
            srem_dupes.append({"names": names, "count": key[0], "value": key[1], "area": key[2],
                               "resolved": len(tgts) == 1})
            if len(tgts) > 1:
                srem_unmapped.append({**ds[0], "name": " = ".join(names), "reason": "رقم مطابق في أكثر من حي"})
                continue
        d, tgt = ds[0], next(iter(tgts))
        if tgt:
            x = srem_by_aqar.setdefault(tgt, {"count": 0, "value": 0, "area": 0, "parts": []})
            x["count"] += d["count"]; x["value"] += d["value"]; x["area"] += d["area"]
            x["parts"].append(" = ".join(names))
        else:
            srem_unmapped.append(d)
    mapped_deals = sum(x["count"] for x in srem_by_aqar.values())

    districts = []
    for name, rs in aqar_d.items():
        ds = [r for r in rs if r["tx"] == "بيع"]
        cen = [(r["lat"], r["lon"]) for r in rs if r.get("lat") and r.get("lon")]
        sx = srem_by_aqar.get(name)
        row = {"name": name, "sector": rs[0].get("sector"), "active": len(rs), "sale": len(ds),
               "rent": len(rs) - len(ds),
               "land_ppm": summarize([r["ppm"] for r in ds if r["type"] == "أرض"]),
               "apt_ppm": summarize([r["ppm"] for r in ds if r["type"] == "شقة"]),
               "villa_ppm": summarize([r["ppm"] for r in ds if r["type"] == "فيلا"]),
               "apt_rent_year": summarize([r["ppm"] for r in rs if r["tx"] == "إيجار" and r["type"] == "شقة"]),
               "lat": statistics.fmean(c[0] for c in cen) if cen else None,
               "lon": statistics.fmean(c[1] for c in cen) if cen else None,
               "srem_deals": sx["count"] if sx else 0, "srem_value": sx["value"] if sx else 0,
               "srem_avg_ppm": round(sx["value"] / sx["area"]) if sx and sx["area"] else None,
               "srem_parts": sx["parts"] if sx else [],
               "mismatch": sum(1 for r in rs if r["district_mismatch"])}
        row["supply_ratio"] = (row["sale"] / (row["sale"] + row["srem_deals"])) if (row["sale"] + row["srem_deals"]) else None
        districts.append(row)
    districts.sort(key=lambda d: -d["active"])

    # ── opportunities (facts only; the report adds the prose) ──
    def km(a1, o1, a2, o2):
        return math.hypot((a1 - a2) * 111, (o1 - o2) * 111 * math.cos(math.radians((a1 + a2) / 2)))
    geo = [d for d in districts if d["lat"] and d["land_ppm"]["median"]]
    opps = []
    for d in geo:
        nb = sorted((km(d["lat"], d["lon"], o["lat"], o["lon"]), o) for o in geo if o is not d)[:5]
        if len(nb) < 3:
            continue
        nmed = statistics.median(o["land_ppm"]["median"] for _, o in nb)
        disc = 1 - d["land_ppm"]["median"] / nmed
        d["land_vs_neighbours"] = round(disc, 3)
        d["neighbours"] = [o["name"] for _, o in nb]
        score, why = 0.0, []
        if disc >= 0.15:
            score += disc
            why.append(f"وسيط سعر متر الأرض المعروضة {d['land_ppm']['median']:,} ر.س أقل بـ {disc:.0%} "
                       f"من وسيط الأحياء المجاورة ({nmed:,.0f} ر.س): {'، '.join(o['name'] for _, o in nb)}")
        if d["srem_deals"] >= 5 and d["supply_ratio"] is not None and d["supply_ratio"] < (supply or 1):
            score += (supply - d["supply_ratio"]) if supply else 0
            why.append(f"{d['srem_deals']} صفقات منفذة هذا الأسبوع مقابل {d['sale']} إعلان بيع — نسبة معروض "
                       f"{d['supply_ratio']:.0%} أقل من متوسط جدة ({supply:.0%})")
        if why:
            opps.append({"district": d["name"], "score": round(score, 3), "why": why,
                         "land_ppm_median": d["land_ppm"]["median"], "land_n": d["land_ppm"]["n"],
                         "srem_deals": d["srem_deals"], "supply_ratio": d["supply_ratio"]})
    opps.sort(key=lambda o: -o["score"])
    opps = opps[:5]

    # ── ticker deals ↔ aqar (only deal-level join available: plan + parcel) ──
    conflicts, ticker_rows = [], []
    by_plan = {}
    for r in L:
        if r.get("plan_no") and r.get("parcel_no"):
            by_plan.setdefault((normalize_ar(r["plan_no"]).replace(" ", ""),
                                normalize_ar(r["parcel_no"]).replace(" ", "")), []).append(r)
    for t in S.get("ticker") or []:
        key = (normalize_ar(t.get("Plan") or "").replace(" ", ""), normalize_ar(t.get("LandNumber") or "").replace(" ", ""))
        m = by_plan.get(key) if all(key) else None
        ticker_rows.append(t)
        if m:
            for r in m:
                conflicts.append({"srem": {"amount": t["TransAmount"], "area": t["TransArea"], "district": t["NHName"],
                                           "date": t["TransDate"][:10], "plan": t.get("Plan"), "parcel": t.get("LandNumber")},
                                  "aqar": {"id": r["id"], "price": r["price"], "area": r["area"], "district": r["district"],
                                           "url": r["url"]},
                                  "price_gap": (r["price"] - t["TransAmount"]) / t["TransAmount"] if r.get("price") and t.get("TransAmount") else None})

    # ── diff vs previous run ──
    diff = None
    prev_ids = set(unpack_dates(P.get("aqar_ids")).keys()) if P and P.get("aqar_ids") else None
    if P:
        cur_ids = {r["id"] for r in L}
        pc = P.get("city", {})
        diff = {"previous_run": P.get("run_at"),
                "new_listings": len(cur_ids - prev_ids) if prev_ids is not None else None,
                "removed_listings": len(prev_ids - cur_ids) if prev_ids is not None else None,
                "srem_deals_prev": pc.get("srem_deals"), "srem_avg_ppm_prev": pc.get("srem_avg_ppm"),
                "land_median_prev": pc.get("land_median"), "apt_median_prev": pc.get("apt_median"),
                "supply_prev": pc.get("supply_ratio"), "active_prev": pc.get("active")}

    land = city_aqar["by_type"].get("أرض", {}).get("sale_ppm", {})
    apt = city_aqar["by_type"].get("شقة", {}).get("sale_ppm", {})
    city = {"srem_deals": srem_city["deals"], "srem_value": srem_city["value"], "srem_avg_ppm": srem_city["avg_ppm"],
            "active": city_aqar["active_total"], "sale": city_aqar["sale"], "rent": city_aqar["rent"],
            "supply_ratio": supply, "land_median": land.get("median"), "land_mean": land.get("mean"),
            "apt_median": apt.get("median"), "apt_mean": apt.get("mean")}

    gates = [dict(g, source=SRC_SREM) for g in S.get("gates", [])] + [dict(g, source=SRC_AQAR) for g in A.get("gates", [])]
    partial = not all(g["ok"] for g in gates)
    data = {"run_at": run_at.isoformat(timespec="minutes"), "partial": partial, "gates": gates,
            "period": srem_city["window"], "city": city, "srem": srem_city, "aqar": city_aqar,
            "districts": districts, "srem_unmapped": srem_unmapped, "srem_duplicates": srem_dupes,
            "srem_district_coverage": (mapped_deals / srem_city["deals"]) if srem_city.get("deals") else None,
            "opportunities": opps, "ticker": ticker_rows, "conflicts": conflicts, "diff": diff,
            "history": (P.get("history", []) if P else []) + [{"run_at": run_at.isoformat(timespec="minutes"), **city}],
            "dates": {"fetched_this_run": A.get("details_fetched"),
                      "known": sum(1 for r in L if r.get("create_iso")), "total": len(L)},
            "notes": {"supply_definition": "نسبة المعروض = إعلانات البيع النشطة في aqar ÷ (إعلانات البيع النشطة + صفقات البورصة العقارية المنفذة خلال آخر 7 أيام)"}}
    json.dump(data, open(f"{a.outdir}/data.json", "w"), ensure_ascii=False)

    # ── CSV (brief schema) ──
    cols = ["المصدر", "المعرّف", "نوع العقار", "نوع المعاملة", "الحي", "الحي حسب نص الإعلان", "المساحة (م²)",
            "السعر الإجمالي (ر.س)", "سعر المتر (ر.س)", "عدد الصفقات", "تاريخ الإعلان/البيع", "الرابط", "ملاحظة"]
    with open(f"{a.outdir}/listings.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in L:
            w.writerow([SRC_AQAR, r["id"], r["type"], r["tx"], r["district"] or NA, r["title_district"] or NA,
                        r["area"] or NA, r["price"] or NA, round(r["ppm"]) if r["ppm"] else NA, "",
                        r.get("create_iso") or NA, r["url"],
                        ("تعارض الحي بين الرابط والعنوان" if r["district_mismatch"] else "") +
                        ("؛ السعر سنوي (إيجار)" if r["tx"] == "إيجار" else "")])
        for d in S.get("districts", []):
            if d["count"]:
                w.writerow([SRC_SREM, d["code"], NA, "بيع", d["name"], "", d["area"], d["value"],
                            round(d["value"] / d["area"]) if d["area"] else NA, d["count"],
                            f"{(S.get('window') or {}).get('from')} → {(S.get('window') or {}).get('to')}",
                            "https://srem.moj.gov.sa/", "إجمالي أسبوعي للحي (البورصة لا تنشر الصفقات منفردة)"])
        for t in ticker_rows:
            w.writerow([SRC_SREM, t.get("Id"), t.get("UnitType") or NA, "بيع", t.get("NHName") or NA, "",
                        t.get("TransArea") or NA, t.get("TransAmount") or NA,
                        round(t["PricePerMeterSquare"]) if t.get("PricePerMeterSquare") else NA, 1,
                        (t.get("TransDate") or "")[:10] or NA, "https://srem.moj.gov.sa/",
                        f"صفقة منفردة (آخر 5 صفقات فقط) — مخطط {t.get('Plan') or NA} قطعة {t.get('LandNumber') or NA}"])

    # ── snapshot for next run ──
    known = unpack_dates(P.get("aqar_ids")) if P and P.get("aqar_ids") else {}
    for r in L:
        if not r.get("create_iso") and known.get(r["id"]):
            r["create_iso"] = known[r["id"]]
    snap = {"run_at": data["run_at"], "city": city, "history": data["history"][-60:],
            "gazetteer": {**((P or {}).get("gazetteer") or {}), **(S.get("gazetteer") or {})},
            "districts": [{k: d[k] for k in ("name", "active", "sale", "srem_deals")} |
                          {"land_median": d["land_ppm"]["median"], "apt_median": d["apt_ppm"]["median"]} for d in districts],
            "aqar_ids": pack_dates(L)}
    json.dump(snap, open(f"{a.outdir}/snapshot.json", "w"), ensure_ascii=False, separators=(",", ":"))
    small = {k: v for k, v in snap.items() if k != "aqar_ids"}     # project copy: no listing ids
    json.dump(small, open(f"{a.outdir}/snapshot_small.json", "w"), ensure_ascii=False, separators=(",", ":"))
    facts = {k: data[k] for k in ("run_at", "partial", "period", "city", "opportunities", "diff", "conflicts",
                                  "srem_district_coverage", "notes", "dates")}
    facts["srem_land_vs_apartment"] = srem_city["land_vs_apartment_reason"]
    facts["gates_failed"] = [g for g in gates if not g["ok"]]
    facts["by_type"] = {t: {"sale_n": v["sale_n"], "rent_n": v["rent_n"], "sale_ppm": v["sale_ppm"]}
                        for t, v in city_aqar["by_type"].items()}
    json.dump(facts, open(f"{a.outdir}/facts.json", "w"), ensure_ascii=False, indent=1)
    print(json.dumps({"partial": partial, "listings": len(L), "districts": len(districts), "opps": len(opps),
                      "srem_deals": srem_city["deals"], "supply": supply}, ensure_ascii=False))


if __name__ == "__main__":
    main()
