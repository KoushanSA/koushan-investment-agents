# -*- coding: utf-8 -*-
"""aqar.fm — every active Jeddah listing. Writes aqar.json.

Exit codes:  0 ok · 2 verification failed · 3 network (host named on stderr)

Verified 2026-09-27:
  * Listing pages are server-rendered. Each page embeds schema.org JSON-LD
    (mainEntity.itemListElement[]: name, price, floorSize, address.addressLocality, geo, url)
    plus mainEntity.numberOfItems for the slice. 20 items per page.
  * Pagination is CAPPED (~146 pages). /عقارات/جدة holds ~39k items, so the market is sliced
    by sector → district, and any district above AQAR_PAGE_CAP_ITEMS is sliced again by category.
  * The listing date is NOT on list pages. It is on the detail page's RSC payload:
    create_time (= «تاريخ الإضافة»), published_at (re-publish), last_update. JSON-LD
    datePosted equals published_at, NOT the original listing date — do not use it as the date.
  * District in the URL/breadcrumb is aqar's geocoded district; the title/free text can name a
    different one (ad 6809543: URL حي الزمرد, text حي المروج). Both are kept; mismatches flagged.
  * /graphql is disallowed in robots.txt and is not used.
"""
import argparse, json, re, sys, time, html, threading, queue, datetime, urllib.parse
from config import (AQAR, AQAR_CITY_SLUG, AQAR_ALL, AQAR_SECTORS, AQAR_PAGE_CAP_ITEMS, AQAR_MAX_PAGES,
                    AQAR_PER_PAGE, AQAR_DELAY, AQAR_WORKERS, DETAIL_CAP_PER_RUN, CATEGORY_SLUGS,
                    AQAR_COVERAGE_MIN, ALL_CATEGORY_SLUGS, SMALL_CATEGORY, classify)
from net import request, Blocked
from codec import unpack_dates

LD_RE = re.compile(r'<script type="application/ld\+json"[^>]*>(.*?)</script>', re.S)
LINK_RE = re.compile(r'href="([^"]+)"[^>]*>(.*?)</a>', re.S)


def url(path):
    return AQAR + urllib.parse.quote(path)


def fetch(path):
    st, body, final = request(url(path), timeout=40, tries=4)
    return st, body


def parse_list(page_html):
    """→ (rows, numberOfItems). Pure function; tested against a fixture."""
    rows, n = [], None
    for m in LD_RE.finditer(page_html):
        try:
            j = json.loads(html.unescape(m.group(1)) if "&quot;" in m.group(1) else m.group(1))
        except json.JSONDecodeError:
            continue
        L = j.get("mainEntity") if isinstance(j, dict) else None
        if not (isinstance(L, dict) and L.get("itemListElement") is not None):
            continue
        n = L.get("numberOfItems")
        for e in L["itemListElement"]:
            it = e.get("item") or {}
            me = it.get("mainEntity") or {}
            u = urllib.parse.unquote(it.get("url") or me.get("url") or "")
            segs = [s for s in urllib.parse.urlsplit(u).path.split("/") if s]
            lid = (it.get("@id") or "").rstrip("/").split("/")[-1] or (segs[-1].split("-")[-1] if segs else "")
            addr = me.get("address") or {}
            geo = me.get("geo") or {}
            fs = me.get("floorSize") or {}
            rows.append({
                "id": str(lid),
                "cat": segs[0] if segs else None,
                "sector": segs[2] if len(segs) > 2 else None,
                "url_district": (segs[3][3:].replace("-", " ") if len(segs) > 3 and segs[3].startswith("حي-") else None),
                "title": it.get("name") or me.get("name"),
                "price": me.get("price"),
                "area": fs.get("value"),
                "locality": addr.get("addressLocality"),
                "street": addr.get("streetAddress"),
                "lat": geo.get("latitude"), "lon": geo.get("longitude"),
                "url": u,
            })
    return rows, n


def parse_links(page_html, prefix):
    """District/sector links with their counts, e.g. ('حي-الياقوت', 3644). Deduplicated."""
    out = {}
    for href, text in LINK_RE.findall(page_html):
        h = urllib.parse.unquote(html.unescape(href))
        if not h.startswith(prefix):
            continue
        tail = h[len(prefix):].strip("/")
        if not tail or "/" in tail or tail.isdigit():
            continue
        t = re.sub(r"<[^>]+>", "", text)
        m = re.search(r"\(([\d,]+)\)", t)
        if m:
            out[tail] = int(m.group(1).replace(",", ""))
    return out


RSC_KEYS = ("create_time", "published_at", "last_update", "plan_no", "parcel_no", "rega_total_price",
            "district", "category", "ad_license_number", "deed_area", "rega_licensed", "status")


def parse_detail(page_html, lid):
    """Pull the listing's own fields out of the RSC payload. Returns {} when not found."""
    h = page_html.replace('\\"', '"')
    i = h.find(f'"id":{lid},')
    if i < 0:
        return {}
    seg = h[i:i + 20000]
    nxt = re.search(r'"id":\d{6,9},"title"', seg[10:])   # stop before the next listing object
    if nxt:
        seg = seg[:nxt.start() + 10]
    out = {}
    for k in RSC_KEYS:
        m = re.search(r'"%s":("(?:[^"\\]|\\.)*"|-?\d+(?:\.\d+)?|true|false|null)' % k, seg)
        if m:
            v = m.group(1)
            try:
                out[k] = json.loads(v)
            except Exception:
                out[k] = v.strip('"')
    for k in ("create_time", "published_at", "last_update"):
        if isinstance(out.get(k), (int, float)) and out[k] > 1e9:
            out[k + "_iso"] = datetime.datetime.fromtimestamp(out[k], datetime.timezone.utc).date().isoformat()
    return out


def fill_from_slice(r, base):
    """Some JSON-LD items carry the site root as their url (ad 6893772, 28 Sep 2026: a Jeddah
    apartment in حي الروضة whose item url was just https://sa.aqar.fm/). Rebuild what the url
    would have told us from the slice it was listed under, and point the link at /ad/<id>."""
    if r.get("cat"):
        return
    segs = [x for x in base.split("/") if x]
    r["url"] = f"{AQAR}/ad/{r['id']}"
    r["url_from_slice"] = True
    if segs and segs[0] != AQAR_ALL:
        r["cat"] = segs[0]
    if len(segs) > 2:
        r["sector"] = segs[2]
    if len(segs) > 3 and segs[3].startswith("حي-"):
        r["url_district"] = segs[3][3:].replace("-", " ")


def crawl_slice(base, rows, lock, stats):
    for p in range(1, AQAR_MAX_PAGES + 1):
        st, body = fetch(base if p == 1 else f"{base}/{p}")
        with lock:
            stats["pages"] += 1
            if stats["pages"] % 250 == 0:
                print(f"progress: {stats['pages']} pages, {len(rows)} unique listings", flush=True)
        if st != 200:
            if st != 404:
                with lock:
                    stats["errors"].append(f"{st} {base}/{p}")
            break
        got, _ = parse_list(body)
        if not got:
            break
        with lock:
            for r in got:
                if r["id"] and r["id"] not in rows:
                    r["via"] = base
                    fill_from_slice(r, base)
                    rows[r["id"]] = r
        if len(got) < AQAR_PER_PAGE:
            break
        time.sleep(AQAR_DELAY)


def run_pool(tasks, fn, workers):
    q = queue.Queue()
    for t in tasks:
        q.put(t)
    errs = []

    def w():
        while True:
            try:
                t = q.get_nowait()
            except queue.Empty:
                return
            try:
                fn(t)
            except Blocked as e:
                errs.append(e)
                return
            except Exception as e:  # noqa
                errs.append(e)
    th = [threading.Thread(target=w) for _ in range(workers)]
    [t.start() for t in th]
    [t.join() for t in th]
    blocked = [e for e in errs if isinstance(e, Blocked)]
    if blocked:
        raise blocked[0]
    return errs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--previous", help="previous snapshot json (for known dates / new-vs-removed)")
    ap.add_argument("--detail-cap", type=int, default=DETAIL_CAP_PER_RUN)
    a = ap.parse_args()

    root = f"/{AQAR_ALL}/{AQAR_CITY_SLUG}"
    try:
        st, body = fetch(root)
    except Blocked as e:
        print(f"NETWORK: host blocked or unreachable → {e.host}", file=sys.stderr)
        sys.exit(3)
    _, market_total = parse_list(body)

    # 1) category sizes for Jeddah (56 categories exist; most are tiny)
    cat_n = {}
    for cat in ALL_CATEGORY_SLUGS:
        st, cb = fetch(f"/{cat}/{AQAR_CITY_SLUG}")
        if st == 200:
            _, n = parse_list(cb)
            cat_n[cat] = n or 0
    big = [c for c, n in cat_n.items() if n > SMALL_CATEGORY]
    small = [c for c, n in cat_n.items() if 0 < n <= SMALL_CATEGORY]

    # 2) districts per sector
    plan, districts = [], {}
    for sec in AQAR_SECTORS:
        _, sb = fetch(f"{root}/{sec}")
        for d, c in parse_links(sb, f"{root}/{sec}/").items():
            if not d.startswith("حي-"):
                continue
            districts[(sec, d)] = c
            # district × big category: measured on حي مشرفة, the all-category district listing
            # repeats boosted ads across pages and surfaced 505 of 588; per-category slices of the
            # same district surfaced 564 of 578. Always slice big categories by district.
            plan += [f"/{cat}/{AQAR_CITY_SLUG}/{sec}/{d}" for cat in big]
            plan.append(f"{root}/{sec}/{d}")                 # catch-all for rare categories
    # 3) small categories city-wide (few pages, little repetition) + sector/city sweeps
    plan += [f"/{cat}/{AQAR_CITY_SLUG}" for cat in small]
    plan += [f"{root}/{sec}" for sec in AQAR_SECTORS] + [root]

    rows, lock, stats = {}, threading.Lock(), {"pages": 0, "errors": []}
    t0 = time.time()
    try:
        run_pool(plan, lambda b: crawl_slice(b, rows, lock, stats), AQAR_WORKERS)
    except Blocked as e:
        print(f"NETWORK: host blocked or unreachable → {e.host}", file=sys.stderr)
        sys.exit(3)

    # 3) details for new listings (dates, plan/parcel) — capped, newest first
    prev = json.load(open(a.previous)) if a.previous else {}
    known = unpack_dates(prev.get("aqar_ids"))          # id → create date (or None if never found)
    for lid, r in rows.items():
        if known.get(lid):
            r["create_iso"] = known[lid]
            r["date_status"] = "cached"
    todo = sorted([lid for lid, r in rows.items() if "create_iso" not in r], key=lambda x: -int(x))
    todo = todo[:a.detail_cap]

    def detail(lid):
        r = rows[lid]
        path = urllib.parse.unquote(urllib.parse.urlsplit(r["url"]).path)
        st, b = fetch(path)
        d = parse_detail(b, lid) if st == 200 else {}
        with lock:
            r["create_iso"] = d.get("create_time_iso")
            r["published_iso"] = d.get("published_at_iso")
            r["updated_iso"] = d.get("last_update_iso")
            r["plan_no"], r["parcel_no"] = d.get("plan_no"), d.get("parcel_no")
            r["rega_total_price"] = d.get("rega_total_price")
            r["rsc_district"] = d.get("district")
            r["date_status"] = "fetched" if d.get("create_time_iso") else "missing"
        time.sleep(AQAR_DELAY)
    print(f"list crawl done: {len(rows)} unique of {market_total}; fetching {len(todo)} detail pages", flush=True)
    try:
        run_pool(todo, detail, AQAR_WORKERS)
    except Blocked as e:
        print(f"NETWORK (details): {e.host} — continuing without dates for the rest", file=sys.stderr)
    for r in rows.values():
        r.setdefault("date_status", "pending")
        r["type"], r["tx"] = classify(r.get("cat"))

    # 4) gates
    uniq = len(rows)
    cov = uniq / market_total if market_total else None
    in_jeddah = sum(1 for r in rows.values() if (r["url"] and f"/{AQAR_CITY_SLUG}/" in r["url"]) or
                    (r.get("url_from_slice") and f"/{AQAR_CITY_SLUG}" in r.get("via", "") and "جدة" in (r.get("title") or "")))
    gates = [
        {"gate": "market total read from aqar", "ok": bool(market_total), "detail": str(market_total)},
        {"gate": "every row is a Jeddah URL", "ok": in_jeddah == uniq, "detail": f"{in_jeddah}/{uniq}"},
        {"gate": f"coverage ≥ {AQAR_COVERAGE_MIN:.0%}", "ok": bool(cov and cov >= AQAR_COVERAGE_MIN),
         "detail": f"{uniq:,} unique of {market_total:,} ({(cov or 0):.1%})" if market_total else "n/a"},
    ]
    out = {"source": "aqar.fm", "fetched_at": datetime.datetime.now(
               datetime.timezone(datetime.timedelta(hours=3))).isoformat(timespec="seconds"),
           "market_total": market_total, "coverage": cov, "category_counts": cat_n, "pages": stats["pages"],
           "page_errors": stats["errors"][:50], "seconds": round(time.time() - t0),
           "districts": [{"sector": s, "slug": d, "count": c} for (s, d), c in districts.items()],
           "details_fetched": len(todo), "gates": gates, "listings": list(rows.values())}
    json.dump(out, open(a.out, "w"), ensure_ascii=False)
    for g in gates:
        print(("PASS " if g["ok"] else "FAIL ") + g["gate"] + " — " + g["detail"])
    hard = [g for g in gates[:2] if not g["ok"]]          # coverage shortfall → PARTIAL, not a stop
    sys.exit(2 if hard else 0)


if __name__ == "__main__":
    main()
