# Furas Opportunity Scout

Scans MOMRAH's **Furas (فرص)** municipal investment portal for currently-open **long-term**
investment opportunities in **Riyadh, Jeddah, Mecca and Medina**, verifies the results, and
publishes an Arabic dashboard plus an Excel workbook.

Built for Koushan · Claude AI 2.0.

## What it produces

- **Dashboard** (`dashboard.html`) — Arabic RTL, grouped by city. A closings-per-week
  timeline, KPI strip, sortable tables (deadline / area / term), filters for city, authority,
  closing window and site size, a per-row urgency stripe, and an ordinal size meter. Each row
  expands to coordinates, a maps link, the portal page, and which documents exist. Published
  as an Artifact so one URL stays current.
  The categorical palette is validated for colour-vision deficiency in both themes — if you
  change those two hues, re-run the validator rather than eyeballing it.
- **Workbook** (`.xlsx`) — **built on request only**, not part of the weekly delivery. Data /
  formula-driven summary / methodology, with a live days-remaining formula.
  It also carries a **«للمراجعة»** sheet — see below.
- **Review list** — the portal leaves the city field empty on roughly a third of its open
  national records (600 of 1,874 on 2026-08-30); its own opportunity page shows only the
  amanah. Blank-city records within 25 km of an opportunity the portal *does* label with one
  of the four cities are listed separately, with the distance and the posting authority, in
  both the dashboard and the workbook. **They are never added to the city counts.** Proximity
  is not proof — one record 7 km from a labelled "Riyadh" point is in محافظة حريملاء — so the
  call is left to a human rather than guessed by the agent.
- **Diff** — what is new, what disappeared, what changed, what closes within 14 days.

## Skills

| Skill | Use |
|---|---|
| `furas-scan` | Run the weekly scan and publish |
| `furas-deep-dive` | Open one opportunity's كراسة, extract the commercial terms **and the surveyed location**, and hand over the actual files |

## Weekly delivery

**The dashboard link, and nothing else.** The workbook, `data.json` and the run snapshot are
build artifacts — sending them every week buries the one link that matters. Ask for the
workbook and it gets built.

Two operational facts that cost a week when they were not known:

- **The diff baseline does not live on disk.** Every scheduled run is a fresh container, so
  `runs/` is always empty. The baseline is the project doc
  `claude/furas_run_snapshot_latest.json` — read at the start of a run, written back after a
  successful publish.
- **A failed artifact *read* does not mean a failed *publish*.** Verified: with the artifact
  host blocked, `read` errors and the publish to the same URL still succeeds. The
  publish-nothing rule applies only to the portal host during discovery.

## Requirements

Network access to two hostnames. **The allowlist matches exact hostnames — a parent domain
does not cover a subdomain.**

```
gisapps.balady.gov.sa      required — opportunity discovery and coordinates
furas.momah.gov.sa         required — detail pages, documents, contract terms
```

**Only those two.** `gisOppertunities.momra.gov.sa` appears inside the request URL and in proxy
logs, but balady's proxy fetches it server-side — this environment never dials it, so it does
not need allowlisting. Asking for it makes the request broader than necessary.

Without the first, the scan cannot discover what is live and will stop with a diagnosis
rather than publish a partial result.

Python 3 with `openpyxl` for the workbook. No credentials, no API keys — the portal is a
public disclosure platform and is read anonymously.

## Verification gates

The scan refuses to publish unless every record has a reference number, there are no
duplicates, no excluded types leaked through, every city returned a non-zero count, dates are
ISO, coordinates are present, and `DURATION` still agrees with the portal's own detail card. A
failing gate prints which one and exits non-zero. There is **no count floor**: the total is
reported as found (decided 5 Oct 2026, after ordinary turnover dropped it to 109).

## City scope

A city counts every record the portal labels with that city, **plus** every record its main
amanah offers itself or through one of its city sectors (e.g. أمانة محافظة جدة's ثول listings),
even when the portal writes another town or leaves the city blank. Records from separate town
municipalities (الخرج، رابغ، الجموم …) stay out. `scripts/furas_amanah_scope.py` applies this.

## Booklet formats differ by amanah — the skill is written for that

Verified against two issuers with materially different documents (أمانة محافظة جدة and
أمانة منطقة الرياض). Four things vary and each one breaks a naive reader:

1. **Arabic extraction.** Some booklets extract with the definite article bound to the next
   letter (`المواصفات` → `املواصفات`), so every Arabic keyword search returns zero and the
   document looks empty. `scripts/ar_text.py` normalises it — 0 → 102 hits on one Riyadh file.
2. **Section headings.** `البند الرابع: وصف العقار` (Jeddah) vs `المادة الثالثة: وصف العقار`
   (Riyadh). Search the phrase, never the section number.
3. **Survey-sheet format.** Jeddah: an NGN table in Arabic-Indic digits, hand-annotated.
   Riyadh: a GIS sheet with `احداثيات حدود الموقع`, an English `LIST OF CONTROL POINTS`,
   elevations, a boundary/length table and `WGS84` printed on it.
4. **UTM zone.** Jeddah/Mecca/Medina are zone **37N**, Riyadh is **38N**. Hardcoding 37N puts a
   Riyadh site ~600 km away. `ar_text.utm_epsg_for(lon)` picks it.

Both cross-checked against the portal's GIS point: **44 m** (Jeddah) and **50 m** (Riyadh).

## Reading a كراسة

The booklet's `وصف العقار` table is a blank contract template — street, plan number, boundaries
and the X/Y coordinate rows all read «حسب القرار المساحي المرفق». That is a cross-reference, not
a missing value. The survey decision itself is usually bound into the same PDF near the end as
**scanned images**, one sheet per plot, carrying a corner-coordinate table on the NGN grid.
Text extraction cannot see them — find them with `pdfimages -list`, render with `pdftoppm`, and
read them. Converted from UTM zone 37N, those corners agreed with the portal's GIS point to
**44 m** on a 159,701 m² parcel, confirming both sources.

## Things that look like bugs but are not

- `DURATION` is **months**, and it is the real contract term. 300 = 25 years.
- Mecca is stored `مكه المكرمه` and Medina `المدينه المنوره` — with ه, not ة. The standard
  spelling returns zero results.
- 57 of 175 opportunities have no Amanah; they are الجهات الشريكة (partner entities). All of
  Mecca's are in that group. Filter on city, never Amanah alone.
- `RFPPRICE` is the booklet fee, not rent. Annual rent is not published anywhere at list level.
- Attachment download links are unreliable on the portal's side: some open the PDF, some
  redirect to the list page, and the two cases are **indistinguishable from the server** —
  every attachment URL returns the same 302 to a non-browser client, including ones that work
  in a real browser. Reconstructing the static file path does not classify them either
  (it 404s for a booklet that downloads fine and succeeds for one that bounces). The dashboard
  therefore ships the document links *and* the opportunity-page button, which always works.

## First run

`scripts/runs/2026-08-30/` holds a verified baseline of 175 opportunities so the first
scheduled run has something to diff against.
