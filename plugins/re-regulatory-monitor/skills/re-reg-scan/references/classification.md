# Scope, status rules and record schema

## In scope (real estate)
- رسوم الأراضي البيضاء والعقارات الشاغرة: the system, its regulations, city application decisions, zones, rates, violation tables.
- تملك غير السعوديين للعقار: the system, executive regulation, geographic zones, Makkah/Madinah rules, listed-company/fund ownership controls.
- الإيجار والعلاقة الإيجارية: rent freezes, landlord–tenant provisions, Ejar rules, notice periods, violation and correction controls.
- REGA-regulated activity: brokerage, off-plan sales/leasing, strata (units ownership), real estate registration (التسجيل العيني), real estate contributions, auctions, consulting/analytics, marketing and advertising, property/facility management once approved.
- Municipal real estate (العقارات البلدية): disposal, leasing, investment.
- Other instruments whose subject is real estate ownership or use: expropriation, housing support regulation, GCC unified real estate rules, transfer of the real estate exchange.

## Out of scope
- Routine real estate registration area announcements (تحديد مناطق التسجيل العيني) — dozens per year, not decisions for this library.
- Building codes, planning approvals, health/food/vendor rules, general municipal permits.
- AML/CFT, data protection and beneficial-owner circulars even when addressed to brokers.
- Drafts on the public consultation platform (استطلاع) — not issued.
- Real estate transaction tax (ZATCA) unless published by one of the three sources.
- News coverage that is not the instrument itself (use it only as status evidence).

## Status rules (from the source, never inferred)
| Status | Tab | Condition |
|---|---|---|
| `active` | فعّالة | Source shows «ساري» / «نافذ» / entered into force, **or** it is the latest published version with an official effective date and no later amendment or repeal was found in the three sources. |
| `superseded` | سابقة / ملغاة | A source states it was repealed, replaced or superseded. `reason` = what replaced it + date. |
| `uncertain` | غير مؤكدة | Anything else: no status shown, effective date conditional on a future announcement, conflicting signals, text not reachable. `reason` = the specific doubt. |

- An approval news item (e.g. «الموافقة على…») is not a separate instrument when the instrument itself is in the library — attach it as evidence instead of a new row.
- A cabinet decision, royal decree and the law they approve are one row (the law), unless the decision carries its own operative provisions.
- An amended law stays one row (active); the original text becomes a `superseded` row only if the source presents it as replaced.
- Two «ساري» items that overlap stay active; mention the overlap in `note`.

## Record schema (`decisions/<id>`)
```json
{
  "title": "Arabic title as in the source",
  "issuer": "الجهة المُصدرة (+ decision number and Hijri date when shown)",
  "topic": "white_land | foreign_ownership | rental | rega_regulation | municipal_real_estate | other",
  "issued": "1447/01/30هـ / 2025-07-25",
  "effective": "تاريخ السريان as the source states it, or null",
  "summary": "Two short Arabic lines separated by \\n",
  "url": "direct official link you opened, or null",
  "source": "أم القرى | الهيئة العامة للعقار | وزارة البلديات والإسكان",
  "status": "active | superseded | uncertain",
  "evidence": "quoted phrase that proves the status",
  "evidence_url": "link to the evidence page, or null",
  "reason": "repeal reason+date (superseded) or doubt (uncertain), else null",
  "note": "link problems, overlaps, computed dates — else null",
  "first_seen": "YYYY-MM-DD",
  "last_checked": "YYYY-MM-DD",
  "sort_key": "YYYY or YYYY-MM-DD (Gregorian issue date)",
  "baseline": false,
  "alert_status": "baseline | sending | sent | failed",
  "alerted_at": "ISO timestamp or null"
}
```

## Ids
- Umm Al-Qura new-format item: `uqn-<numeric id>` (e.g. `uqn-4001281`); old-format `details?p=N`: `uqn-p<N>` (existing rows may use `uqn-p-<N>` or `uqn-<N>` — match by URL, never create a second row).
- REGA: `rega-<short-english-slug>`.
- MOMAH: `momah-node-<n>` for node pages, otherwise `momah-<short-english-slug>`.
- Allowed characters: letters, digits, `_ - . ~ : @ +`.

## candidates.json (input to diff_state.py)
A JSON array of objects with at least `id`, `title`, `url`, `status` (may be null before classification).
