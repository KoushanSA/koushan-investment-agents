---
name: jeddah-listing-analyze
description: Analyse one Jeddah property listing — an aqar.fm link or pasted listing text — into the Jeddah market schema (نوع العقار، نوع المعاملة، الحي، المساحة، السعر، سعر المتر، التاريخ، المصدر) and place it against its district's latest figures. Use when the user shares a listing URL or ad text and asks "حلل هذا الإعلان", "هل السعر مناسب", "analyse this listing", "how does this compare to the district", or pastes an ad from aqar, Bayut, WhatsApp or Haraj about a Jeddah property.
---

# Single listing analysis

Analyse the one listing given, instead of the full market run.

## Get the listing

- **aqar.fm link** — fetch the page (`scripts/aqar_fetch.py` helpers: `fetch()`, `parse_detail()`;
  JSON-LD on the page gives price/area/district/geo, the RSC payload gives `create_time`,
  `plan_no`, `parcel_no`). If the cloud cannot reach sa.aqar.fm, read the page through Chrome
  with `get_page_text`.
- **Other link** (Bayut, Wasalt, Haraj…) — read the page text. Only Jeddah is in scope; if
  the listing is outside Jeddah, say so and stop.
- **Pasted text** — use the text only. Do not look the ad up elsewhere to fill gaps.

## Extract — exactly these fields

| الحقل | Rule |
|---|---|
| نوع العقار | أرض / شقة / فيلا / عمارة / استراحة / استوديو / أخرى (حدد) |
| نوع المعاملة | بيع / إيجار |
| الحي | as written; if the URL/breadcrumb and the text name different districts, give both |
| المساحة (م²) | as stated; «المساحة حسب الصك» wins over a rounded figure, and say which you used |
| السعر الإجمالي | as stated; rent is annual unless the ad says otherwise — state the period |
| سعر المتر | if stated use it; else السعر ÷ المساحة (say it was calculated) |
| تاريخ الإعلان | «تاريخ الإضافة» / `create_time`. A re-publish date is not the listing date |
| المصدر | site name + link |

Any field the listing does not state → «غير متوفر». Never infer area from room count, never
infer a district from a street name, never convert a monthly figure you had to guess.

## Compare

Read the latest baseline (`project_read` `claude/jeddah_market_snapshot.json`; its `districts`
carry `land_median`, `apt_median`, `active`, `srem_deals`, and `run_at`). Compare the listing's
سعر المتر with the matching district and type median. State the baseline date.

- District missing from the baseline, or its median is null (small sample) → say the comparison
  is not possible, do not substitute the city figure silently (you may show the city figure,
  labelled as city-wide).
- Asking vs asking only. Never call the median an executed price.

## Output

A short Arabic answer: the extracted fields as a compact table, one line placing the price
against the district median (percentage above/below, with the baseline date), and one line on
anything suspicious in the ad (district mismatch, price-per-m² far outside the district range,
missing REGA licence number). No buy/sell advice.
