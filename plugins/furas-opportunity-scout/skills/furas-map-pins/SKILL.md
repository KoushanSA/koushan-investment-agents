---
name: furas-map-pins
description: Put Furas opportunities on a real Google map as labelled pins — open Google My Maps in the user's Chrome and import the exported pin file, or hand back a one-click multi-pin Maps link. Use when the user says "show these on a map", "open them in Google Maps", "put the pins on a map", "where are these on a map", "اعرضها على الخريطة", "افتحها في خرائط جوجل", or asks to see a district's or city's opportunities plotted.
---

# Put opportunities on a real Google map

Three routes. Pick by how many opportunities, and whether Chrome is connected. Never promise
a route before checking it is available.

## The constraint that decides everything

**No Google Maps URL can place more than about ten pins, and none can draw a district
boundary you supply.** There is no parameter for it. Anyone who says otherwise is guessing.
What exists:

| Route | Pins | Needs | Use when |
|---|---|---|---|
| Maps URLs API (`/maps/dir/?api=1`) | up to **10** | nothing — one click | a district, or any set of ≤10 |
| Named search (`/maps/search/حي <name>، <city>`) | none, but Google shades its **own** boundary | nothing | the user wants the district outline |
| **My Maps import** | unlimited, each labelled | Chrome connected + the user's Google account | a whole city, or >10 |

## Route 1 — ≤ 10 opportunities, no Chrome needed

Build the link yourself and hand it over:

```
https://www.google.com/maps/dir/?api=1
  &origin=<lat>,<lon>            first opportunity
  &destination=<lat>,<lon>       last one
  &waypoints=<lat>,<lon>|...     up to 9 between them
  &travelmode=driving
```

Google drops a lettered pin on each. It also draws a route between them — **say that the
line is an artefact and the pins are the point**, so the user does not read a sequence into
it. The dashboard already renders this button on the district chip.

## Route 2 — more than 10, Chrome connected

This creates a map in the user's own Google account, so **ask first and wait for a clear yes**
— naming the city or district and how many pins. Then:

1. Produce the CSV. Either the dashboard's «تصدير الدبابيس» button, or build it from
   `data.json` with the same columns: `الاسم, رقم الفرصة, المدينة, الحي, خط العرض, خط الطول,
   المساحة م², المدة سنوات, آخر موعد, جهة الطرح, رابط الفرصة`. Write it with a UTF-8 BOM or
   Google mangles the Arabic.
2. `mcp__claude-in-chrome__tabs_context_mcp` first — if the extension does not answer, stop
   and offer Route 1 or the file. Do not keep retrying.
3. New tab → `https://www.google.com/maps/d/u/0/` → **إنشاء خريطة جديدة / Create a new map**.
4. **استيراد / Import** on the layer → upload the CSV with
   `mcp__claude-in-chrome__file_upload`.
5. Google asks which columns hold the position — choose **خط العرض** and **خط الطول** — and
   which column titles the marker — choose **الاسم**.
6. Rename the map to something like `فرص <المدينة> — <التاريخ>` and report back what was
   created. Do not share it or change its visibility; that is the user's call.

If Google's import dialog looks different from the above, read the page and adapt rather than
clicking blind — and if a step cannot be completed, say which one and hand over the CSV.

## Route 3 — Chrome unavailable

Hand over the CSV and the one-line instruction: open <https://www.google.com/maps/d/>, create
a map, import the file, pick the two coordinate columns and `الاسم` as the label. Do not
pretend a URL can do it.

## Never

- Never invent a Maps URL parameter for multiple pins or polygons. There isn't one.
- Never place a pin at a coordinate the portal did not publish — a record with no
  coordinates is left off the map and named as left off.
- Never create, rename or share anything in the user's Google account without asking first.
