# Arabic report — rules

Write `report.md` from `facts.json` only. Arabic, about half a page (180–260 words). Plain
paragraphs and at most one short bullet list. `**bold**` is the only markup the dashboard renders.

## Order (keep it)

1. **التاريخ والفترة** — one line: تاريخ التقرير (run_at) والفترة المغطاة (period.from → period.to,
   آخر 7 أيام تنشرها البورصة العقارية). If `partial` is true, say which gate failed in the same
   paragraph.
2. **المبيعات** — عدد الصفقات المنفذة وقيمتها ومتوسط سعر المتر المنفذ (البورصة العقارية).
   Then the asking side: وسيط سعر متر الأرض والشقة المعروضة (aqar.fm), with sample sizes.
   State once that the البورصة does not split executed deals by property type, so land vs
   apartment executed totals are «غير متوفر» — never apportion.
3. **نسبة المعروض** — the value, and its definition in one clause (from `notes.supply_definition`).
4. **أبرز الفرص** — the computed opportunities (3–5 if present). One line each: the district
   and the reason, using the numbers in `opportunities[].why`. If fewer than 3 qualify, say so;
   do not pad the list with districts that did not qualify.
5. **مقارنة بالتشغيل السابق** — only from `diff`. No `diff` → «لا توجد بيانات سابقة للمقارنة».
   `new_listings` is null → say the listing-level comparison was unavailable this run.
   Mention a change only when it is material (≥ 5% on a price, ≥ 10% on deal count), and give
   both values.
6. **تعارض المصادر** — one line if `conflicts` is non-empty (both figures + gap). Otherwise omit.

## Number style

- Western digits with thousands separators: 4,416 ر.س/م²، 524.3 مليون ر.س.
- Every figure is followed by its source the first time it appears in a paragraph:
  «(البورصة العقارية)» or «(aqar.fm)».
- «متوسط» only for a mean, «وسيط» for a median. Asking prices are «أسعار معروضة», never «أسعار بيع».
- Percentages to the nearest whole number unless below 10%.

## Never

- A number that is not in `facts.json`.
- A forecast, a recommendation to buy or sell, or a price target. Opportunities are
  «مؤشرات تستحق الدراسة», not advice.
- Data from another city in any total.
- Filling a null metric with an estimate. Write «غير متوفر» and why.
