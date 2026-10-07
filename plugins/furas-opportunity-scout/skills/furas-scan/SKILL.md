---
name: furas-scan
description: Scan the Saudi Furas (فرص) municipal investment portal for currently-open long-term investment opportunities in Riyadh, Jeddah, Mecca and Medina, verify the results, and publish an Arabic dashboard. Use when the user says "run the Furas scan", "check Furas", "what investment opportunities are open", "scan the opportunities portal", "فرص الاستثمارية", "update the opportunities dashboard", or when a scheduled weekly opportunity scan fires.
---

# Furas opportunity scan

Run the full scan, verify it, and publish. Never publish a run that fails verification.

## Run

Work from `${CLAUDE_PLUGIN_ROOT}/scripts`. Keep each run in a dated folder.

```bash
cd ${CLAUDE_PLUGIN_ROOT}/scripts
RUN=runs/$(date +%Y-%m-%d); mkdir -p "$RUN"
python3 furas_fetch.py --out "$RUN/data.json"
```

`furas_fetch.py` discovers, enriches from each opportunity's detail page, and runs every
verification gate. It exits non-zero and prints a diagnosis if anything fails.

- **Exit 0** — proceed.
- **Exit 2** — verification failed. `data.json` is written for inspection. Report which gate
  failed and stop. Do not publish.
- **Exit 3** — network failure. The message names the exact hostname to allowlist. Stop.
  When reporting this, ask for **`gisapps.balady.gov.sa` only**. `gisOppertunities.momra.gov.sa`
  shows up in the request URL and in proxy logs but is fetched server-side by balady's proxy —
  this environment never dials it. Requesting two hosts when one suffices makes the ask harder
  to approve for no benefit.

There is **no count floor or ceiling** — the total is whatever the portal has open and is
reported as found. Only accuracy gates stop a run.

Apply the amanah scope (a city also counts what its own amanah or city sectors offer, even when
the portal writes another town or leaves the city blank; separate town municipalities stay out):

```bash
python3 furas_amanah_scope.py --data "$RUN/data.json"
```

Exit 0 — proceed. Exit 2 — an accuracy gate failed on the combined set: stop, do not publish.

Then build:

```bash
python3 furas_roads.py     --data "$RUN/data.json"
python3 furas_dashboard.py --data "$RUN/data.json" --out "$RUN/dashboard.html"
python3 furas_amanah_scope.py --data "$RUN/data.json" --html "$RUN/dashboard.html"
```

The last line rewrites the dashboard's city-methodology line to state the amanah rule and how
many records it added this run.

**Run `furas_roads.py` before the dashboard.** It bakes the real main-road network into
`data.json` as a per-city frame plus a road image. It is the only source of roads available:
OpenStreetMap, its tile servers and Overpass are ALL blocked by the egress allowlist, while
MOMRA's own ArcGIS basemap (`BaseMap/MomraBasemap`, layers 14-16 "MOT Roads Level 1-3") is
reachable through the same balady proxy the scan already uses. That service has **Query
disabled**, so road geometry cannot be pulled as lines — Map `export` works, so the roads
arrive as a rendered PNG that is recoloured and embedded. It also computes the map FRAME and
stores it; the dashboard adopts that stored frame rather than recomputing, so the roads and
the dots can never drift apart. If a city's fetch fails the page simply omits that city's
roads — never substitute a drawn-from-memory road. Street Centerlines (layers 17+) do not
render at a city-wide scale, so asking for them changes nothing.

The page carries three views off one payload — الجدول (table), الفرز (screening funnel) and
الخريطة (map). They are generated, not hand-written: nothing to update weekly.

A bid-calendar view existed and was removed on request; do not reinstate it unless asked.

**Every district must be reachable.** The district table lists all of them, not a "top N" —
an earlier cut at 2+ opportunities hid 50 of 78 districts and the top-7 map labelling hid 50
more, which reads to the user as the map having lost a district. Map labels are dropped only
on collision, and a dropped label is always still a table row. Clicking a district filters the
table to that whole district, never to one reference.

**A district with no open opportunities is absent, and that is correct.** When the user asks
where a district went, check the previous snapshot before assuming a bug: الصفا in Jeddah held
4 opportunities on 30 Aug 2026 with deadlines of 15–17 Sep, so by 17 Sep it was legitimately
gone. Say that, rather than "fixing" it.

**A stale installed plugin silently undoes this work.** The 20 Sep 2026 scheduled run
published fresh data from an old plugin copy and reverted the page to four tabs with no
download, district or map work. The run is only as current as the installed plugin — when a
published version is newer than expected, check what CODE it carries before merging, not just
its data.

**City, authority and activity are multi-select checkbox panels, not dropdowns**, each
showing counts computed against the OTHER active filters so a number is what that option
would really yield. Two rules learned the hard way: do not rebuild the panel on every tick
(it detaches the checkbox under the user's finger and loses focus — patch the counts in
place), and on phones the panel must be a bottom sheet, because anchoring it to a half-width
control put it off-screen where it could not be tapped at all.

**Filters are explicit and chip-backed — never text typed into the search box.** Writing a
reference into the free-text field looks to the user like they searched, cannot be cleared
without knowing to empty the box, and is not a filter. `FDIST` (district) and `FREF` (one
opportunity) are real filter state with a visible, removable chip; the single-opportunity chip
offers a one-click widen to its whole district.

**Several labelled pins on one Google map: export CSV, import to My Maps.** There is no URL
parameter for multiple pins, and `.kml` is not an allowed download extension in the artifact
viewer — `.csv` is, and Google My Maps imports it with latitude/longitude columns and labels
each pin from a column. The export therefore ships as CSV with a UTF-8 BOM (so Excel and
Sheets read the Arabic) through the `downloads` capability, which must stay declared
(`capabilities: {downloads: true}`) or the button silently does nothing in the artifact; the
standalone file falls back to a Blob save. Do not swap this for a prettier-sounding route that
does not work.

**Google Maps cannot draw a polygon or several pins from a URL.** Searching the district
*by name* (`/maps/search/حي <name>، <city>`) makes Google resolve the neighbourhood and shade
its own boundary, which is the closest honest thing to an outline; a bare `@lat,lon` only
centres the view. Do not fabricate a boundary in the page and present it as the district.

**The map is north-up and east-right.** An earlier version mirrored longitude on the theory
that an RTL page should read right-to-left; that made every city unreadable against any
familiar map and had to be undone. A map is not text — do not mirror it. The frame is also
squared in true ground distance (a degree of longitude is only cos(lat) as wide as a degree
of latitude), so cities are not stretched, and each panel carries a compass rose.

Two things in there that must not be "simplified":

- **The area filter is a logarithmic dual slider, not a tier dropdown.** Real areas span
  14 m² to 1.8 M m² and the median is ~2,500 m², so on a linear scale every parcel the CEO
  might actually bid on collapses into the first 1% of the track. Preset breakpoints are
  computed as `v = 1000·ln(area)/ln(2e6)` — never type a guessed slider value; an earlier
  guess put the "1,000 m²" preset at 125 m².
- **`text-anchor="end"` extends text RIGHTWARD in this page**, because the document is
  `direction: rtl`. Use `start` for a right-hand label gutter. Measured, not assumed — `end`
  pushed all 54 calendar row labels off the canvas, and the map's latitude labels the same way.
- **A standalone copy is `--standalone --title "..."`.** The Artifact tool wraps the page in
  its own document skeleton, so the default output has no doctype/head/body; a file the user
  opens locally needs the whole document. Build the local copy with that flag rather than
  hand-editing the output.

## Week-over-week diff — the baseline does NOT survive between runs

Every scheduled run starts in a **fresh container** with the plugin re-synced, so `runs/` is
always empty. There is no previous `data.json` on disk. A diff step that looks for one finds
nothing and silently reports no comparison — which is what happened on 30 Aug 2026.

The baseline lives in the **project**, not on disk. Read it first, diff against it, write the
new one last:

1. **Before diffing** — `project_read` `claude/furas_run_snapshot_latest.json` and save the
   content to `$RUN/prev.json`. If the doc does not exist, this is the first run: skip the
   diff and say so plainly. Do not present "no changes" when the truth is "nothing to
   compare against" — an unchanged total can still hide equal arrivals and departures.
2. **Diff** — `python3 furas_diff.py --current "$RUN/data.json" --previous "$RUN/prev.json"`
3. **After a successful publish** — write this run's snapshot back:
   ```bash
   python3 furas_snapshot.py --data "$RUN/data.json" --out "$RUN/snapshot.json"
   ```
   then `project_write` that file to `claude/furas_run_snapshot_latest.json` with
   `present_to_user: false`. Only overwrite the baseline on a run that verified and published —
   a failed run must leave last week's baseline intact.

## Publish

The dashboard is the deliverable. Publish `dashboard.html` with the Artifact tool, reusing the
existing artifact URL so the link the CEO already has stays current — pass the stored URL as
`url`. Only create a new artifact on the very first run.

**Pass `capabilities: {downloads: true}` on every publish.** Omitting `capabilities` carries
the stored declaration forward, but passing any other non-empty object revokes what is not
restated — and the district pin export depends on it.

### A failed read is not a failed publish — this is the one that bit us

Try `action: "read"` with the stored `url` first; it is the documented prerequisite and it lets
you see what you are replacing.

**If that read fails, publish anyway.** Verified 30 Aug 2026: with the artifact host blocked by
the network allowlist, `read` returns an allowlist error and the publish to the same `url`
**succeeds immediately afterwards**. The two paths are independent.

The first scheduled run (30 Aug 2026) treated the read error as a network failure, applied the
"if the network is blocked, publish nothing" rule, and published nothing — so the CEO's link
went stale for a week over an error that did not actually block anything. Do not repeat that.
A read error is a missing safety check, not a broken publish.

Likewise, if a *publish* is refused for not having read the artifact, the refusal hands back
the live version — that IS the read. Retry immediately; it succeeds.

Only if the publish itself fails, twice, is publishing genuinely unavailable. Then send
`dashboard.html` as a file so the week is not lost.

### Two different hosts can be blocked, and they mean opposite things

| Blocked host | Meaning | What to do |
|---|---|---|
| `gisapps.balady.gov.sa` | Discovery failed. There is no verified data. | Stop. Publish nothing. Ask for that one host. |
| `*.frame.claudeusercontent.com` | Only the artifact **read** is affected. Data is fine; publishing still works. | **Publish normally.** Mention the entry once so the safety check can be restored; do not treat it as a blocker. |

The run-stop rule applies **only** to the portal host during discovery. It never applies to the
artifact host.

To restore the read (recommended, not required):

```
*.frame.claudeusercontent.com
```

environment settings → Code → Network access → Custom → Allowed domains. For a shared
environment, admin settings → Cloud environments.

**Never pass `force: true`.** Forcing discards whatever version is live, and a run that could
not read the artifact cannot know what it would be discarding. Publishing without `force` is
already the correct behaviour — it is what succeeds.

## What to hand over

**The dashboard only.** Publish it, and say in one or two sentences what changed. That is the
whole delivery.

Lead with what moved since last week — new opportunities, and those closing within 14 days.
The full table is on the dashboard; do not restate it in chat.

If `candidates` is non-empty, say so in one line ("N unlabelled records are listed for
review") and leave it at that. Never fold them into the headline count, and never describe
them as belonging to a city — the portal does not say they do.

Do **not** send the workbook, `data.json`, the snapshot, or any intermediate file unless the
user asks for it. They are build artifacts, not deliverables — sending them each week clutters
the conversation and buries the one link that matters.

The workbook still builds on request:

```bash
python3 furas_workbook.py --data "$RUN/data.json" --out "$RUN/opportunities.xlsx"
```

The one exception: if the artifact host is blocked, send `dashboard.html` as a file, because
otherwise the run produces nothing the user can see.

## Facts that are counter-intuitive — do not "fix" them

- **`DURATION` is in MONTHS and is the real contract term.** 300 = 25 years. Verified against
  the portal's own detail card on all records. Do not report it as days, and do not mark it
  غير مذكور — an earlier version made that mistake.
- **Mecca is stored as `مكه المكرمه`** (ه, not ة); Medina as `المدينه المنوره`. Querying the
  standard spelling returns zero. `normalize_ar()` in `config.py` handles this.
- **Match on city, never on Amanah.** around a third of records have a null `AMANA` (57 of 175 on 2026-08-27) — they are
  الجهات الشريكة (partner entities). Amanah-only filtering drops every Mecca opportunity.
- **`?type=Investment` is required** on detail URLs. Without it the portal returns 404.
- **`RFPPRICE` is the booklet fee, not rent.** `ANNUALVALUE` and `MINIMUMGURANTEE` are empty
  on every record — annual rent is not published. Never present it as rent.
- **Attachment links: verify every one, and never offer an unverified one.** The portal's own
  attachment URL (`/opportunity/attachment/...`) NEVER serves the file — it answers `200` with
  the ~1.1 MB page shell, which is why buttons built on it dumped the reader on the home page.
  The file, when it exists, sits at a flat static path built from the link's fileId and
  filename: `/sites/default/files/{fileId}_{name}.{ext}`, percent-encoded, filename kept
  exactly including any trailing space. Parse the PATH of the stored url — it is absolute and
  encoded, so splitting the whole string on "/" lands two segments off.
  `probe_downloads()` checks each one with a `Range: bytes=0-7` request and keeps it only if
  the first four bytes are `%PDF`. On 17 Sep 2026 that was **21 of 189** documents; the other
  168 are a hard 404 because the portal's archive is incomplete. A document that does not
  resolve gets **no button** and is named as a portal-page download instead.
  Pace the probe (~0.8 s per request, 4 workers): a fast burst makes the host fail everything,
  including files that work fine a minute later, which reads as "nothing is downloadable".
- **Use a plain link, never `download`.** The artifact viewer does not grant pages download
  permission, so a `download` attribute produces a button that looks live and does nothing.
  `target="_blank"` on the static URL opens the PDF and the reader saves it from there.
- Zero area, zero price and `1970-01-01` envelope dates mean *unstated* → `غير مذكور`.
  Never estimate.

- **About a third of open national records have NO city at all — do not guess one.**
  On 2026-08-30, 600 of 1,874 qualifying national records had a blank `CITYNAME`, and the
  portal's own detail page shows only the amanah for them. Some really are in our cities, so
  filtering on `CITYNAME` alone drops real opportunities. But geography cannot settle them:
  one record 7 km from a labelled "الرياض" point is in **محافظة حريملاء**, and the amanah is
  *region*-wide — 104 blank records carry one of our four amanahs and all but a handful are
  50–330 km away.
  `find_candidates()` therefore lists blank-city records within `CANDIDATE_KM` (25 km) of the
  nearest record the portal *does* label with one of our cities, annotates them with
  `_nnCity` / `_nnKm` / `_amanahCity`, and returns them **separately**. They go in the
  `candidates` key, the dashboard's review panel and the workbook's «للمراجعة» sheet — never
  into `records`, the city totals or the headline number. An earlier version merged them via
  a lat/lon bounding box; it drew an arbitrary line (accepted a Jeddah candidate at 19.7 km
  while rejecting a near-identical one at 17.0 km). Do not reinstate that. Asserting a city
  the portal does not assert is fabrication, however plausible the coordinates look.
  Also: do not query `CITYNAME IS NULL` — the balady proxy rejects it and returns an HTML
  error page instead of JSON. Fetch the national set and filter locally.
- **ArcGIS returns date fields as epoch-MILLISECONDS, not ISO.** `normalize_dates()` converts
  them once for records from both fetch paths. If it is skipped, the dashboard cannot parse a
  deadline (it raises `month must be in 1..12`) and the diff reports every row as changed —
  which looks like a portal-wide update and is not. A verification gate now fails the run if
  any `LASTRFPSELLDATE` is not `YYYY-MM-DD`; do not relax it, and do not "fix" a bad diff by
  normalising inside the comparator alone.

## Hard constraints

- Never log in, register, or complete Nafath. If a wall appears anywhere, stop at that exact
  point and report what was requested, the URL, and what stayed visible.
- Never include `TemporaryRental` or `DirectRental`.
- If any city returns zero, treat it as a suspected normalisation bug, not a finding.
