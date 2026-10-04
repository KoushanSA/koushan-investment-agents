# -*- coding: utf-8 -*-
"""Jeddah Market Analyst — verified configuration.
Every value here was checked against the live sources on 2026-09-27 (via Claude in Chrome).
Several are counter-intuitive; do not change without re-verifying."""
import re

# ── البورصة العقارية (MOJ Real Estate Exchange) ──────────────────────────────
SREM_API = "https://prod-srem-api-srem.moj.gov.sa/api/v1/"
SREM_INQUIRY = "https://prod-inquiryservice-srem.moj.gov.sa/api/v1/AddressInfo/SearchAddress"
SREM_HOSTS = ("prod-srem-api-srem.moj.gov.sa", "prod-inquiryservice-srem.moj.gov.sa")
JEDDAH_CITY_CODE = 37528          # NOT 1 — city code 1 is Riyadh; "طريق جدة السريع" lives there
SREM_REGION_CODE = 2              # منطقة مكة
# Weekly ("W") queries answer. Monthly/yearly city queries hit a 5 s Redis timeout server-side
# and return HTTP 500 most of the time — do not switch the default period to "M".
SREM_PERIOD = "W"
SREM_RETRIES = 8                  # ~4 attempts were needed on 27 Sep; 8 gives headroom

# ── aqar.fm ──────────────────────────────────────────────────────────────────
AQAR = "https://sa.aqar.fm"
AQAR_HOST = "sa.aqar.fm"
AQAR_CITY_SLUG = "جدة"
AQAR_ALL = "عقارات"               # all-categories listing root: /عقارات/جدة
AQAR_SECTORS = ("شمال-جدة", "جنوب-جدة")
# Listing pagination is capped: /أراضي-للبيع/جدة held 3,198 items but page 147+ is empty
# (last non-empty page 146 ≈ 2,920 items). Any slice larger than this must be split further.
AQAR_PAGE_CAP_ITEMS = 2800
AQAR_MAX_PAGES = 160
AQAR_PER_PAGE = 20
AQAR_DELAY = 0.25                 # seconds between page requests per worker
AQAR_WORKERS = 4
DETAIL_CAP_PER_RUN = 8000         # new listings whose detail page (dates, plan/parcel) is fetched per run (~10 min)

# Category slug → (property type, transaction). Anything not listed is parsed generically
# from its "-للبيع" / "-للإيجار" suffix and reported as "أخرى (<name>)".
CATEGORY = {
    "أراضي-للبيع": ("أرض", "بيع"),        "أراضي-للإيجار": ("أرض", "إيجار"),
    "شقق-للبيع": ("شقة", "بيع"),          "شقق-للإيجار": ("شقة", "إيجار"),
    "فلل-للبيع": ("فيلا", "بيع"),         "فلل-للإيجار": ("فيلا", "إيجار"),
    "عمائر-للبيع": ("عمارة", "بيع"),      "عمائر-للإيجار": ("عمارة", "إيجار"),
    "استراحة-للبيع": ("استراحة", "بيع"),  "استراحة-للإيجار": ("استراحة", "إيجار"),
    "استوديوهات-للبيع": ("استوديو", "بيع"), "استوديوهات-للإيجار": ("استوديو", "إيجار"),
    "دور-للبيع": ("أخرى (دور)", "بيع"),   "دور-للإيجار": ("أخرى (دور)", "إيجار"),
    "محلات-للإيجار": ("أخرى (محل)", "إيجار"), "محلات-للبيع": ("أخرى (محل)", "بيع"),
    "مكتب-تجاري-للإيجار": ("أخرى (مكتب تجاري)", "إيجار"),
}
CATEGORY_SLUGS = list(CATEGORY)
# Full category vocabulary seen on aqar.fm (27 Sep 2026). Counts are read per run; empty ones cost one request.
ALL_CATEGORY_SLUGS = CATEGORY_SLUGS + [
    "غرف-للإيجار", "مستودع-للإيجار", "مجمعات-للإيجار", "ورش-للإيجار", "مزارع-للإيجار", "مصانع-للإيجار",
    "محطات-للإيجار", "أبراج-للإيجار", "أكشاك-للإيجار", "فنادق-للإيجار", "صراف-وبنوك-للإيجار", "مدارس-للإيجار",
    "شاليه-للإيجار", "مواقف-سيارات-للإيجار", "مستشفيات-ومراكز-صحية-للإيجار", "مزرعة-للبيع", "مستودعات-للبيع",
    "مجمعات-للبيع", "ورش-للبيع", "محطات-للبيع", "فنادق-للبيع", "مكاتب-للبيع", "أبراج-للبيع", "مصانع-للبيع",
    "مدارس-للبيع", "بيت-للبيع", "غرف-للبيع", "أكشاك-للبيع", "مواقف-سيارات-للبيع", "مستشفيات-ومراكز-صحية-للبيع",
    "بيت-للإيجار", "مخيم-للإيجار", "دور-سينما-للبيع", "دور-سينما-للإيجار", "صراف-وبنوك-للبيع",
    "محطات-كهرباء-للبيع", "محطات-كهرباء-للإيجار", "أبراج-اتصالات-للبيع", "أبراج-اتصالات-للإيجار"]
# A category with at most this many Jeddah listings is crawled city-wide instead of per district.
SMALL_CATEGORY = 400

NA = "غير متوفر"
SRC_SREM = "البورصة العقارية"
SRC_AQAR = "aqar.fm"

# Minimum sample before a district/type average is shown or used for an opportunity.
MIN_SAMPLE = 8
# Coverage gate: unique aqar IDs collected ÷ numberOfItems on /عقارات/جدة. Below this the run
# is marked PARTIAL (published with a banner), never silently presented as the full market.
AQAR_COVERAGE_MIN = 0.90

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")


def classify(cat_slug):
    if cat_slug in CATEGORY:
        return CATEGORY[cat_slug]
    if not cat_slug:
        return (NA, NA)
    for suf, tx in (("-للبيع", "بيع"), ("-للإيجار", "إيجار")):
        if cat_slug.endswith(suf):
            return ("أخرى (%s)" % cat_slug[: -len(suf)].replace("-", " "), tx)
    return ("أخرى (%s)" % cat_slug.replace("-", " "), NA)


_SUB = re.compile(r"\s*/\s*\d+.*$")            # "المروة / 2" → "المروة"
def normalize_ar(s):
    """Orthographic normalisation for matching district names across sources.
    SREM writes الوادى / الربوه / صناعى; aqar writes الوادي / الربوة. Without this they never meet."""
    if not s:
        return ""
    s = str(s).strip()
    s = re.sub(r"^حي[\s\-]+|^حى[\s\-]+", "", s)
    s = s.replace("-", " ")
    for a, b in (("أ", "ا"), ("إ", "ا"), ("آ", "ا"), ("ة", "ه"), ("ى", "ي"), ("ؤ", "و"), ("ئ", "ي")):
        s = s.replace(a, b)
    s = s.replace("ـ", "")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def district_key(s):
    """Base district key: drops SREM sub-plan suffixes ("/ 2", free-text after the name)."""
    s = normalize_ar(_SUB.sub("", s or ""))
    s = re.sub(r"^ال", "", s)                   # الربوه ↔ ربوه, غليل ↔ الغليل
    s = re.sub(r"ء$", "", s)                    # الصفاء ↔ الصفا (2,741 false mismatches on 28 Sep)
    return s.replace(" ", "")
