# Sources — URLs, pagination, gotchas (verified 27–28 Sep 2026)

## 1. جريدة أم القرى — uqn.gov.sa
- RSS, decisions & regulations: `https://www.uqn.gov.sa/rssFeed/21` — valid RSS 2.0 but only the latest ~8–9 items. Never rely on it alone.
- Listing: `https://www.uqn.gov.sa/decisions/rules-and-regulations?pgno=N` — 6 items/page, ~147 pages. Add a cache-buster (`&x=<timestamp>`); without it results can be stale.
- REGA and other authority decisions sit under `https://www.uqn.gov.sa/decisions-and-regulations/authorities/<id>` and do **not** appear in the rules-and-regulations listing. Check `https://www.uqn.gov.sa/decisions/authorities?pgno=N` too.
- Item pages: `https://www.uqn.gov.sa/decisions-and-regulations/<id>` (numeric, increasing) or `/decisions-and-regulations/rules-and-regulations/<id>`. Older items: `https://uqn.gov.sa/details?p=<n>`. Old `uqn.gov.sa/?p=<n>` links redirect to the home page — treat as unreachable.
- Cabinet session news: `/news/council-of-ministers/<id>` — useful as evidence, not as the instrument.
- The page header shows today's date; the publication date is in the item body. Hijri/Gregorian pairs on the page are sometimes inconsistent — prefer the Hijri and note any conversion.
- Weekly edition on Fridays (occasional mid-week editions): `/digital?date=YYYY-MM-DD`.
- Access: direct curl may be blocked by the cloud egress allowlist; WebFetch works.

## 2. الهيئة العامة للعقار — rega.gov.sa
- Regulations library: `https://rega.gov.sa/الأنظمة-والقرارات/الأنظمة-واللوائح-والأدلة/?page=N&` — page=0 and 1 are the same; 3 real pages (12/12/6 = 30 items on 28 Sep 2026). Stop when a page repeats.
- Each item shows a status («ساري») and a date — the primary status evidence.
- Detail pages have two path forms: `/الأنظمة-والقرارات/الأنظمة-واللوائح-والأدلة/<cat>/<slug>/` and `/الأنظمة-واللوائح-والأدلة/<cat>/<slug>/`, cat ∈ الأنظمة, الانظمة, اللوائح, ضوابط, الادلة. Take detail links from the listing or search; do not build them.
- Fetch Arabic paths in raw (unencoded) form — the percent-encoded form is too long for WebFetch.
- News: `https://rega.gov.sa/media-center/الأخبار-والإعلانات/?page=N&sort=descending` (untested pattern). Rules announced here may not be in the library yet → usually `uncertain` until the text appears.
- Circulars `https://rega.gov.sa/media-center/التعاميم/` — 6 items, all AML/data-protection on 28 Sep 2026 → out of scope unless a real estate rule appears.
- Foreign-ownership platform (zones maps): `saudiproperties.rega.gov.sa` — JavaScript app, not readable by fetchers.
- Access: direct curl may be blocked by the cloud egress allowlist; WebFetch works.

## 3. وزارة البلديات والإسكان — momah.gov.sa
- Regulations list: `https://momah.gov.sa/ar/regulations?pageNumber=N` — 21 pages × 10, newest first; links go straight to PDFs under `/sites/default/files/YYYY-MM/`. Some listed links point to the wrong file (e.g. "مخالفة تقسيم المبنى…" opens a chimney guide) — check the PDF content matches the title before accepting.
- The list does not show status; items from here are usually `uncertain` unless the text or an official announcement proves force.
- White land fees system page: `https://momah.gov.sa/ar/node/15439` (consolidated PDF with amendments). Regulation page: `https://momah.gov.sa/ar/node/15451`.
- News: `https://momah.gov.sa/ar/news` — announcements such as «بدء نفاذ…» serve as status evidence.
- `idlelands.momah.gov.sa` timed out from non-Saudi fetchers — use the user's Chrome if needed.
- Access: reachable by curl and WebFetch.

## Optional allowlist (org Owner)
`www.uqn.gov.sa`, `uqn.gov.sa`, `rega.gov.sa`, `idlelands.momah.gov.sa`, `momah.gov.sa`. Runs work through WebFetch without it.

## Known open items (as of 28 Sep 2026)
- Vacant properties fees regulation (`uqn-4000950`): uncertain until the minister announces zones in the gazette.
- Real estate registration law amendments (Nov 2025): uncertain until published in Umm Al-Qura.
- Foreign ownership geographic zones: uncertain until the decision text is published.
