# -*- coding: utf-8 -*-
"""Compare two runs on رقم الفرصة. Prints an Arabic change summary."""
import json, argparse, datetime

ap = argparse.ArgumentParser()
ap.add_argument("--current", default="data.json")
ap.add_argument("--previous", required=True)
ap.add_argument("--json-out", default=None)
args = ap.parse_args()

DATE_FIELDS = {"LASTRFPSELLDATE", "ENDDATE", "ENVELOPESOPENDATE", "STARTDATE", "LASTBIDATE"}

def as_day(v):
    """Runs may store dates as ArcGIS epoch-ms or as YYYY-MM-DD strings depending on how the
    snapshot was produced. Compare them on the same footing or every row looks changed."""
    if v is None or v == "":
        return ""
    if isinstance(v, (int, float)):
        try: return datetime.datetime.utcfromtimestamp(v / 1000).strftime("%Y-%m-%d")
        except Exception: return str(v)
    s = str(v).strip()
    if s.isdigit() and len(s) >= 12:
        try: return datetime.datetime.utcfromtimestamp(int(s) / 1000).strftime("%Y-%m-%d")
        except Exception: return s
    return s[:10]

def cmp_val(field, v):
    return as_day(v) if field in DATE_FIELDS else ("" if v is None else str(v).strip())

def load(p):
    d = json.load(open(p, encoding="utf-8"))
    return d, {r["OPPORTUNITYID"]: r for r in d["records"]}

cur, C = load(args.current)
prv, P = load(args.previous)
LABEL = {"الرياض":"الرياض","جدة":"جدة","مكه المكرمه":"مكة المكرمة","المدينه المنوره":"المدينة المنورة"}

new     = [C[k] for k in C if k not in P]
gone    = [P[k] for k in P if k not in C]
common  = [k for k in C if k in P]
changed = []
for k in common:
    diffs = []
    for f, lab in (("LASTRFPSELLDATE","الموعد النهائي"),("RFPPRICE","سعر الكراسة"),
                   ("DURATION","مدة العقد"),("TOTALSPACEINMETERS","المساحة")):
        old, cur_v = cmp_val(f, P[k].get(f)), cmp_val(f, C[k].get(f))
        if old != cur_v:
            diffs.append(f"{lab}: {old} ← {cur_v}")
    if diffs: changed.append((k, C[k], diffs))

today = datetime.date.fromisoformat(cur["asOf"])
def days(r):
    try: return (datetime.date.fromisoformat(as_day(r["LASTRFPSELLDATE"])) - today).days
    except Exception: return 999
closing = sorted([r for r in C.values() if 0 <= days(r) <= 14], key=days)

def ar_days(n):
    if n == 0: return "اليوم"
    if n == 1: return "غداً"
    if n == 2: return "بعد يومين"
    if n <= 10: return f"بعد {n} أيام"
    return f"بعد {n} يوماً"

def line(r):
    return (f"  {r['OPPORTUNITYID']}  {LABEL.get(r.get('CITYNAME'),r.get('CITYNAME'))}  "
            f"{(r.get('OPPORTUNITYDESCRIPTION') or '')[:64]}")

print(f"مقارنة {prv['asOf']} ← {cur['asOf']}")
print(f"الإجمالي: {prv['total']} ← {cur['total']}\n")
print(f"■ فرص جديدة: {len(new)}");        [print(line(r)) for r in new[:25]]
print(f"\n■ فرص لم تعد مدرجة: {len(gone)}"); [print(line(r)) for r in gone[:25]]
print(f"\n■ فرص تغيّرت بياناتها: {len(changed)}")
for k, r, d in changed[:25]: print(line(r) + "\n      " + " · ".join(d))
print(f"\n■ تُغلق خلال 14 يوماً: {len(closing)}")
for r in closing[:25]: print(line(r) + f"   ({ar_days(days(r))})")

if args.json_out:
    json.dump({"from": prv["asOf"], "to": cur["asOf"],
               "new": [r["OPPORTUNITYID"] for r in new],
               "removed": [r["OPPORTUNITYID"] for r in gone],
               "changed": [{"ref": k, "diffs": d} for k, _, d in changed],
               "closingSoon": [r["OPPORTUNITYID"] for r in closing]},
              open(args.json_out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\nWrote {args.json_out}")
