# -*- coding: utf-8 -*-
"""Fetch the real main-road network for each city and bake it into data.json.

Source: MOMRA's own ArcGIS basemap, layers 14-16 "MOT Roads Level 1-3" (Ministry of
Transport). Same ministry that publishes the opportunities, reached through the same
already-allowlisted balady proxy. This is why the map can show roads at all: OpenStreetMap,
its tile servers and Overpass are ALL blocked by the egress allowlist, and roads drawn from
memory would be invented geography under real coordinates.

The service has Query disabled, so geometry cannot be pulled as lines — but Map export works,
so we take a rendered PNG, recolour it to a neutral ink that reads on both themes, and embed
it as a data URI. The FRAME is computed here and stored, and the dashboard projects its dots
into that stored frame, so the roads and the dots can never drift apart.
"""
import json, math, argparse, base64, io, sys, urllib.request
from config import PROXY, UA

BASE = ("https://gisOppertunities.momra.gov.sa/arcgis/rest/services"
        "/BaseMap/MomraBasemap/MapServer")
ROAD_LAYERS = "14,15,16"          # MOT Roads L1-3. Street centerlines (17+) do not render
PX = 760                          # at a city-wide scale, so asking for them changes nothing.

def city_frame(pts):
    """Square the frame in TRUE ground distance — a degree of longitude is only cos(lat) as
    wide as a degree of latitude, so an unsquared frame stretches the city east-west."""
    la = [p[0] for p in pts]; lo = [p[1] for p in pts]
    minLat, maxLat, minLon, maxLon = min(la), max(la), min(lo), max(lo)
    cosf = math.cos(math.radians((minLat + maxLat) / 2))
    padA = max((maxLat - minLat) * 0.10, 0.012)
    padO = max((maxLon - minLon) * 0.10, 0.012)
    minLat -= padA; maxLat += padA; minLon -= padO; maxLon += padO
    hKm = (maxLat - minLat) * 110.57
    wKm = (maxLon - minLon) * 111.32 * cosf
    if wKm > hKm:
        g = (wKm - hKm) / 110.57 / 2; minLat -= g; maxLat += g
    else:
        g = (hKm - wKm) / (111.32 * cosf) / 2; minLon -= g; maxLon += g
    return {"minLat": minLat, "maxLat": maxLat, "minLon": minLon, "maxLon": maxLon,
            "cos": cosf, "widthKm": round((maxLon - minLon) * 111.32 * cosf, 1)}

def fetch_png(fr, timeout=150, tries=4):
    """This host drops connections mid-transfer often enough that a single attempt loses a
    city at random — Jeddah failed on the first run and fetched cleanly on retry."""
    import time
    bbox = f"{fr['minLon']},{fr['minLat']},{fr['maxLon']},{fr['maxLat']}"
    u = (f"{BASE}/export?bbox={bbox}&bboxSR=4326&imageSR=4326&size={PX},{PX}"
         f"&layers=show:{ROAD_LAYERS}&format=png32&transparent=true&f=image")
    last = None
    for i in range(tries):
        try:
            rq = urllib.request.Request(PROXY + u, headers={"User-Agent": UA})
            with urllib.request.urlopen(rq, timeout=timeout) as r:
                data = r.read()
            if data[:4] == b"\x89PNG":
                return data
            last = RuntimeError("not a PNG (%d bytes)" % len(data))
        except Exception as e:
            last = e
        time.sleep(3 * (i + 1))
    raise last

def restyle(png):
    """The service draws roads red. Repaint to one neutral ink, keeping each line's strength
    so the trunk roads still read heavier than the minor ones, and keep it semi-transparent so
    the opportunity dots stay the subject."""
    from PIL import Image
    im = Image.open(io.BytesIO(png)).convert("RGBA")
    px = im.load()
    w, h = im.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a == 0:
                continue
            lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255.0
            strength = max(0.0, min(1.0, 1.0 - lum))      # a darker source line stays stronger
            px[x, y] = (108, 118, 114, int(a * (0.30 + 0.62 * strength)))
    out = io.BytesIO()
    im.save(out, format="PNG", optimize=True)
    return out.getvalue()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data.json")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    d = json.load(open(a.data, encoding="utf-8"))
    cities = {}
    for r in d["records"]:
        if r.get("_lat") is None: continue
        cities.setdefault(r["CITYNAME"], []).append((r["_lat"], r["_lon"]))
    roads, failed = {}, []
    for city, pts in cities.items():
        fr = city_frame(pts)
        try:
            png = restyle(fetch_png(fr))
            fr["png"] = "data:image/png;base64," + base64.b64encode(png).decode()
            print(f"   {city}: roads {len(png):,}B over {fr['widthKm']} km", flush=True)
        except Exception as e:
            fr["png"] = None; failed.append(f"{city}: {type(e).__name__}")
            print(f"   {city}: NO ROAD LAYER — {e}", flush=True)
        roads[city] = fr
    d["roads"] = roads
    d["roadsSource"] = ("MOMRA/MOT — BaseMap/MomraBasemap layers 14-16 "
                        "(MOT Roads Level 1-3)")
    json.dump(d, open(a.out or a.data, "w", encoding="utf-8"), ensure_ascii=False)
    tot = sum(len(v.get("png") or "") for v in roads.values())
    print(f"wrote {a.out or a.data} · {len(roads)} city frames · "
          f"{tot/1024:.0f} KB of road imagery"
          + (f" · FAILED: {', '.join(failed)}" if failed else ""))

if __name__ == "__main__":
    main()
