# -*- coding: utf-8 -*-
"""Normalise Arabic text extracted from PDFs.

Some booklets (Word-generated, certain embedded fonts) extract with the definite
article's letters bound to the following character, so المواصفات comes out as املواصفات.
Others pad words with tatweel. Neither is visible to an exact-string search.
Normalise BOTH the haystack and the needle before matching."""
import re

_LIG = [("امل", "الم"), ("اإل", "الإ"), ("األ", "الأ"), ("اال", "الا"),
        ("اإلست", "الإست"), ("اآل", "الآ")]

def norm(s: str) -> str:
    if not s: return ""
    for bad, good in _LIG:
        s = s.replace(bad, good)
    s = s.replace("ـ", "")                       # tatweel padding: حـــدود -> حدود
    s = re.sub(r"[​-‏‪-‮]", "", s)   # bidi controls
    for a, b in (("أ","ا"),("إ","ا"),("آ","ا"),("ة","ه"),("ى","ي")):
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s)

def find(haystack: str, needle: str) -> int:
    return norm(haystack).count(norm(needle))

# ---------------------------------------------------------------- UTM helper
def utm_epsg_for(lon: float) -> int:
    """Saudi spans two UTM zones. Picking the wrong one puts the site ~600 km away.
    Zone 37N covers lon < 42°E (Jeddah, Mecca, Medina); 38N covers lon >= 42°E (Riyadh)."""
    return 32637 if lon < 42.0 else 32638

def check_against_gis(corners, gis_lat, gis_lon):
    """corners: [(easting, northing), ...] from the survey sheet.
    Returns (centroid_lat, centroid_lon, metres_from_gis, epsg_used)."""
    import math
    from pyproj import Transformer
    epsg = utm_epsg_for(gis_lon)
    tr = Transformer.from_crs(f"EPSG:{epsg}", "EPSG:4326", always_xy=True)
    pts = [tr.transform(e, n) for e, n in corners]
    cy = sum(p[1] for p in pts) / len(pts)
    cx = sum(p[0] for p in pts) / len(pts)
    dy = (cy - gis_lat) * 111320
    dx = (cx - gis_lon) * 111320 * math.cos(math.radians(cy))
    return cy, cx, math.hypot(dx, dy), epsg

def polygon_area(corners):
    """Shoelace area in m² — cross-check against the stated المساحة."""
    n = len(corners)
    return abs(sum(corners[i][0]*corners[(i+1) % n][1] - corners[(i+1) % n][0]*corners[i][1]
                   for i in range(n)) / 2)
