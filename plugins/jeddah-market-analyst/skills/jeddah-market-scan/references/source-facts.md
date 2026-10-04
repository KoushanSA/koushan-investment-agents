# Source facts — verified 27 Sep 2026. Read before "fixing" anything.

## البورصة العقارية (srem.moj.gov.sa)

- Public JSON API, anonymous. `POST https://prod-srem-api-srem.moj.gov.sa/api/v1/Dashboard/GetAreaInfo`
  body `{"periodCategory":"W","period":1,"areaType":"C","areaSerial":37528,"cityCode":37528}`.
  Pasting the host in a browser shows nothing — it only answers POSTed JSON. That is normal.
- `Data.Total` is the headline. `Data.Stats` is one row per day and **must sum exactly** to
  `Total` (27 Sep: 346 deals, SAR 524,278,705 — exact). The gate enforces it.
- `AveragePrice` is area-weighted: TotalPrices ÷ TotalAreas (524.28M ÷ 118,714 = 4,416).
- `Data.Transactions` is the **latest 5 deals only** (a live ticker), not the week. There is
  no anonymous per-deal list. Do not describe the ticker as "this week's deals".
- No property-type split in any aggregate. Ticker rows carry `UnitType` («شقة» or blank);
  blank is **not** "land" — write «غير متوفر».
- Monthly (`M`) and yearly (`Y`) city queries usually fail server-side (Redis 5 s timeout →
  HTTP 500 with JSON body). Weekly works with retries (~4 attempts on 27 Sep). Keep `W`.
- `GetTrendingDistricts` **ignores the city filter** and returns the national top 5. Useless
  for Jeddah; do not use it for district figures.
- District gazetteer is deed-based: one aqar district maps to several البورصة districts
  («المروة», «المروة / 2»), and names carry free text («البوادى على يمين الصاعد الى المدينة المنورة بجده»).
  Spelling differs from aqar (الوادى/الوادي, الربوه/الربوة). `SearchAddress` returns ≤ 10 hits.
  Mapping is by normalised prefix; unmapped البورصة districts are reported, never dropped.
- Trap: a name search for «جدة» returns «حي طريق جدة السريع، مدينة الرياض» (city code 1).
  Always filter `CityCode == 37528`.
- Probably geo-restricted: connect timeout from a US fetcher, fine from a Saudi browser.

## aqar.fm

- Listing pages are server-rendered; schema.org JSON-LD `mainEntity.itemListElement` holds
  name, price, floorSize, address.addressLocality, geo, url. 20 per page.
- `numberOfItems` on `/عقارات/جدة` = the market total (39,305 on 27 Sep; the 43 category
  counts summed to 39,306). The district link counts on sector pages are inflated/stale
  (حي مشرفة: link 742, `numberOfItems` 588). Use `numberOfItems`.
- Pagination is capped (~146 pages). Boosted ads repeat across pages, so a large slice
  surfaces fewer unique ads than it claims (حي مشرفة all-categories: 505 of 588). Slicing the
  same district by category surfaced 564 of 578. Hence: big categories × district, small
  categories city-wide, plus district/sector/city catch-alls. Coverage is gated at 90%.
- The listing date is only on the detail page RSC payload: `create_time` = «تاريخ الإضافة».
  JSON-LD `datePosted` = `published_at` (re-publish date) — **not** the listing date.
  Dates are cached in the snapshot and fetched for at most 8,000 new listings per run,
  newest first; the rest are «غير متوفر» until fetched.
- District from the URL can differ from the title/free text (ad 6809543: URL حي الزمرد, title
  حي المروج). Both are kept; the CSV flags it.
- Discounted ads: JSON-LD `price` is the current price; `rega_total_price` is the original.
- Rent prices are annual. Rent ÷ area is reported as rent per m² per year, never mixed with sale.
- aqar never marks an ad sold. A disappeared ad is "removed", not "sold".
- `/graphql` is disallowed in robots.txt and is not used. Category listing pages are allowed.
- «آخر الصفقات العقارية» and «مؤشرات عقار» require login — out of scope.

## Learned on the first live run (28 Sep 2026)

- The cloud can reach aqar only with Python's urllib: `curl` gets Cloudflare's «تم حظرك» page
  (fingerprint block). gzip is requested to keep a full run near 1–2 GB instead of ~8 GB.
- The MOJ hosts are allowlisted but reset the connection from the cloud. البورصة runs via Chrome.
- One JSON-LD item carried the site root as its url (ad 6893772, حي الروضة). `fill_from_slice`
  rebuilds category/sector/district from the slice it was listed under; the gate accepts it
  only if its title also says جدة.
- ~15% of «شقة للبيع» ads carry a land/building area (e.g. 2,985 m² for SAR 287,000). The 3×IQR
  log fence removed 3,721 of 23,828 — expected; report the excluded count, never the raw mean.
- البورصة returns the SAME aggregate for sibling gazetteer entries («المروة» = «المروة / 2»,
  «المنار» = «المنار / 3», and even «البغدادية الغربية» = «البغدادية الشرقية / 2»). `build.py`
  counts identical (count, value, area) rows once, and withholds them from district figures
  when they map to different aqar districts.
- District mismatches URL vs title are mostly sub-plan names (الزمرد ↔ الفنار/البحيرات/النور,
  طيبة ↔ حكومي1) and الصفا/الصفاء spelling (normalised). ~2,950 remain; they are naming, not errors.
- Supply ratio with the chosen definition sits at ~99% city-wide (30k listings vs ~350 weekly
  deals). District differences are the signal; the city figure barely moves.
- District coverage of البورصة deals was 44% on the first run: its gazetteer has many more
  sub-districts than aqar districts. The city total is complete; coverage grows as names are learned.
