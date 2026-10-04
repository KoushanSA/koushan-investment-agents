---
name: jeddah-market-scan
description: Run the Jeddah real estate market analysis — pull executed-deal statistics from البورصة العقارية (MOJ Real Estate Exchange) and every active Jeddah listing from aqar.fm, verify them, build the structured dataset and an Arabic market report, and update the «مرصد جدة العقاري» dashboard. Use when the user says "run the Jeddah market scan", "update the Jeddah dashboard", "تقرير سوق جدة", "حلل سوق جدة العقاري", "كم صفقة في جدة هذا الأسبوع", "متوسط سعر المتر في جدة", "نسبة المعروض", or when the Sunday/Tuesday scheduled market run fires.
---

# Jeddah market scan

Role: a real estate market analyst for Jeddah. Turn raw deals and listings into a structured
dataset and a short periodic report. **Never invent a number.** Every figure must trace to
البورصة العقارية or aqar.fm; when data is insufficient for a metric, say so explicitly.

If the user hands over a single listing URL or pasted listing text instead of asking for the
market run, use the `jeddah-listing-analyze` skill instead.

## Run

Work from `${CLAUDE_PLUGIN_ROOT}/scripts`, one dated folder per run.

```bash
cd ${CLAUDE_PLUGIN_ROOT}/scripts
RUN=runs/$(date +%Y-%m-%d_%H%M); mkdir -p "$RUN"
```

### 1. Load the previous baseline (before fetching)

The container is fresh every run — `runs/` is always empty. The baseline lives in two places:

1. **Full baseline** — the dashboard artifact's published file `data/snapshot.json` (listing
   ids + listing dates + history). `Artifact` `action: "read"`, `url` = the user's dashboard URL
   (see `references/state.md`), `path: "data/snapshot.json"` → copy to `$RUN/prev.json`.
2. **Fallback** — if that read fails, `project_read` `claude/jeddah_market_snapshot.json`
   (history + gazetteer, no listing ids) → `$RUN/prev.json`. New/removed listing counts are
   then unavailable: say so; do not report "0 new".
3. Neither exists → first run. Skip `--previous` everywhere and say "لا توجد بيانات سابقة للمقارنة".

### 2. Fetch

**aqar.fm runs in the cloud** (verified 28 Sep 2026: Python gets 200; `curl` gets a Cloudflare
"تم حظرك" page — never switch the fetcher to curl). Start it in the background; it takes
10–25 min (≈3,600 list pages + up to 8,000 detail pages):

```bash
nohup python3 aqar_fetch.py --out "$RUN/aqar.json" --previous "$RUN/prev.json" > "$RUN/aqar.log" 2>&1 &
```

**البورصة العقارية runs through Chrome.** The MOJ hosts accept the cloud's tunnel and then
reset it (verified 28 Sep 2026, after the allowlist was added) — they refuse non-Saudi traffic.
Try the cloud once (fails in < 1 min), then go straight to the Chrome path in
`references/network.md` while aqar is still crawling:

```bash
python3 srem_fetch.py --out "$RUN/srem.json" --seed-districts "$RUN/seeds.json" --cached-gazetteer "$RUN/gaz.json"
```

`seeds.json` = the union of: aqar district names (`prev.json` → `districts[].name`, or
`aqar.json` on a first run), every name already in `prev.json` → `gazetteer`, and the
`NHName` of each ticker deal seen so far. The البورصة gazetteer has far more sub-districts than
aqar has districts, so district coverage grows run over run as new names are learned; the
city total is complete regardless. `gaz.json` = `prev.json` → `gazetteer` (or `{}`).

Exit codes for both scripts: **0** ok · **2** a verification gate failed (file written; read it)
· **3** network — the message names the host.

- aqar exit 2 (a non-Jeddah row, no market total) → stop, publish nothing, report the gate.
- aqar coverage below 90% is **not** exit 2: the run continues as PARTIAL and the dashboard
  shows a banner. Never present a partial crawl as the whole market.
- البورصة gate failure (exit 2 / assemble exit 2) → stop; do not publish a total that failed its check.
- البورصة unreachable on both paths (cloud refused **and** Chrome not connected) → continue
  without `srem.json`. `build.py` then marks every البورصة metric «غير متوفر» and the run as
  PARTIAL. Never carry last run's البورصة figures forward.

### 3. Build

```bash
python3 build.py --srem "$RUN/srem.json" --aqar "$RUN/aqar.json" --previous "$RUN/prev.json" --outdir "$RUN"
```

Writes `data.json`, `listings.csv` (the brief's schema, UTF-8 BOM), `snapshot.json`,
`snapshot_small.json`, `facts.json`.

### 4. Write the report (you)

Read `$RUN/facts.json` and write `$RUN/report.md` in Arabic, about half a page, following
`references/report-rules.md` exactly. Also write `$RUN/opp_notes.json`
(`{district: one short sentence}`) only if you have something to add to a computed
opportunity that the numbers support — otherwise `{}`.

### 5. Dashboard

```bash
python3 dashboard.py --data "$RUN/data.json" --report "$RUN/report.md" --opp-notes "$RUN/opp_notes.json" --out "$RUN/dashboard.html"
```

### 6. Publish — one artifact, same link every run

Publish `$RUN/dashboard.html` with the Artifact tool:
- `url` = the user's dashboard URL, resolved as `references/state.md` describes (omit only on the
  user's very first run, then record the new URL in the project doc `claude/jeddah_market_state.md`).
- `capabilities: {downloads: true}` on **every** publish (a non-empty object revokes anything
  not restated; the CSV button depends on it).
- `files`:
  `{"data/latest.csv": "$RUN/listings.csv", "data/snapshot.json": "$RUN/snapshot.json",
    "data/runs/<YYYY-MM-DD_HHMM>.csv": "$RUN/listings.csv", "data/runs/<YYYY-MM-DD_HHMM>.json": "$RUN/facts.json"}`
  Files left out are kept, so the archive accumulates run by run. Artifacts do not serve
  `.gz`/`.zip` (refused 28 Sep 2026), so the archive is plain CSV at ~11 MB a run against a
  256 MB version limit: keep the last 12 run CSVs and drop older ones by passing
  `"data/runs/<old>.csv": null` (list them with `action: "list", scope: "files"`). Keep every
  run's `.json` — they are small and hold the figures the reports quoted.

If the `read` in step 1 failed with an allowlist error, **publish anyway** — the read and the
publish are independent (learned on the Furas agent, 30 Aug 2026). Never pass `force: true`.
If the publish itself fails twice, send `dashboard.html` as a file so the run is not lost.

### 7. Persist the small baseline

After a successful publish only: `project_write` `claude/jeddah_market_snapshot.json` from
`$RUN/snapshot_small.json` (`present_to_user: false`) and `claude/Jeddah_Market_Report_<date>.md`
from `$RUN/report.md`. A failed run leaves the previous baseline untouched.

## What to hand over

The dashboard link, plus two sentences: what moved since the last run, and anything the data
could not answer this run. Do not paste the report or the tables into chat; do not send the
CSV or JSON unless asked.

## Hard rules

- Jeddah only. البورصة: city code **37528**, never a name search ("جدة" also matches
  حي طريق جدة السريع in Riyadh, city code 1). aqar: `/…/جدة/…` URLs only.
- Never log in to aqar or البورصة, never complete Nafath. aqar's «آخر الصفقات» and «مؤشرات»
  are behind login — out of scope.
- Missing field → «غير متوفر». Never estimate an area, a price, a date or a property type.
- البورصة aggregates have **no property-type split**. «بيع أراضي / بيع شقق» as separate
  executed-deal totals is therefore not available — state it; never apportion the total.
- If the two sources disagree on the same plot (plan + parcel), show both figures and the
  gap. Never pick one silently. District-level asking vs executed is a spread, not a conflict.
- Facts that look like bugs but are not: see `references/source-facts.md` before "fixing"
  anything.
