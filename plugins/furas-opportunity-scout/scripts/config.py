# -*- coding: utf-8 -*-
"""Furas Opportunity Scout — verified configuration.
Every value here was confirmed against the live portal on 2026-08-30.
Do not change without re-verifying; several are counter-intuitive."""

PROXY = "https://gisapps.balady.gov.sa/opportunities/proxy/proxy.ashx?"
SERVICE = ("https://gisOppertunities.momra.gov.sa/arcgis/rest/services/"
           "GISProjects/InvestmentView/MapServer/0")           # note: 'Oppertunities' (double-p) is correct
DETAIL = "https://furas.momah.gov.sa/opportunity/{ref}?type=Investment"  # ?type= is REQUIRED; without it → 404

# Cities as the portal actually stores them. Mecca/Medina use ه not ة.
CITY_STORED = {
    "الرياض":          "الرياض",
    "جدة":             "جدة",
    "مكة المكرمة":     "مكه المكرمه",
    "المدينة المنورة": "المدينه المنوره",
}
CITY_DISPLAY = {v: k for k, v in CITY_STORED.items()}

# Some records carry a blank/null CITYNAME. Verified on 2026-08-30: three qualifying
# opportunities were being silently dropped this way. Recover them by amanah, and — where the
# record has no attributes at all — by whether the point falls inside the envelope of records
# the portal DOES label for that city. Anything recovered is tagged so it can be audited.
AMANA_TO_CITY = {
    "أمانة منطقة الرياض":       "الرياض",
    "أمانة محافظة جدة":         "جدة",
    "أمانة العاصمة المقدسة":    "مكه المكرمه",
    "أمانة منطقة المدينة المنورة": "المدينه المنوره",
}

INCLUDE_TYPES = ("Investment",)                 # long-term only
EXCLUDE_TYPES = ("TemporaryRental", "DirectRental")

FIELDS = ["OBJECTID","OPPORTUNITYID","OPPORTUNITYDESCRIPTION","CITYNAME","AMANA","BALADYA",
          "ENTITIESNAME","REGIONNAME","DISTRICT","STREET","DURATION","TOTALSPACEINMETERS",
          "RFPPRICE","LASTRFPSELLDATE","ENDDATE","ENVELOPESOPENDATE","STATUS",
          "OPPORTUNITYACTIVESTATUS","OPPORTUNITYTYPE","ACTIVITYTYPE","SUBACTIVITYTYPE"]

# Expected band for the four cities. Outside this → report as suspect, do not publish silently.
SANITY_MIN, SANITY_MAX = 120, 260
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")

def normalize_ar(s: str) -> str:
    """Arabic orthographic normalisation. Without this, Mecca returns zero results."""
    if not s: return ""
    for a, b in (("أ","ا"),("إ","ا"),("آ","ا"),("ة","ه"),("ى","ي")):
        s = s.replace(a, b)
    return s.replace("ـ", "").replace(" ", "")
