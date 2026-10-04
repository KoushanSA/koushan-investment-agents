#!/usr/bin/env python3
"""Compare scanned candidates against the library state to find genuinely new decisions.

--state       folder of decision docs saved by `ArtifactData list ... out_dir` (<out_dir>/decisions/*.json)
--candidates  JSON array of {id, title, url, status?}

Prints JSON: {"new": [...], "possible_duplicates": [...], "known": [...], "retryable_failed": [...]}.
A candidate is known if its id, its canonical URL, or its normalized title matches an existing doc.
Near-identical titles (similarity >= 0.9) under another id are reported as possible duplicates,
which the run must resolve by reading — default to NOT new.
"""
import argparse, difflib, glob, json, os, re, unicodedata
from urllib.parse import unquote, urlsplit

AR_DIACRITICS = re.compile(r"[ؐ-ًؚ-ٰۖ-ۭـ]")


def norm_title(t):
    t = unicodedata.normalize("NFKC", t or "")
    t = AR_DIACRITICS.sub("", t)
    t = re.sub("[إأآا]", "ا", t).replace("ة", "ه").replace("ى", "ي")
    t = re.sub(r"[^\w\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def norm_url(u):
    if not u:
        return None
    s = urlsplit(unquote(u.strip()))
    host = s.netloc.lower().removeprefix("www.")
    path = s.path.rstrip("/")
    q = "&".join(p for p in s.query.split("&") if p and not p.startswith(("x=", "csrt=")))
    return f"{host}{path}" + (f"?{q}" if q else "")


def load_state(folder):
    docs = []
    for f in glob.glob(os.path.join(folder, "*.json")):
        d = json.load(open(f, encoding="utf-8"))
        body = d.get("data", d)  # tolerate either {id,data,version} or bare body
        docs.append({"id": d.get("id") or os.path.splitext(os.path.basename(f))[0], **body})
    return docs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", required=True)
    ap.add_argument("--candidates", required=True)
    a = ap.parse_args()
    state = load_state(a.state)
    if not state:
        raise SystemExit("STATE EMPTY — stop the run; do not alert.")
    by_id = {d["id"]: d for d in state}
    by_url = {}
    for d in state:
        nu = norm_url(d.get("url"))
        if nu:
            by_url.setdefault(nu, d["id"])
    titles = {d["id"]: norm_title(d.get("title")) for d in state}
    out = {"new": [], "possible_duplicates": [], "known": [], "retryable_failed": []}
    seen = set()
    for c in json.load(open(a.candidates, encoding="utf-8")):
        cid, nt, nu = c["id"], norm_title(c.get("title")), norm_url(c.get("url"))
        if cid in seen:
            continue
        seen.add(cid)
        if cid in by_id:
            out["known"].append({"id": cid, "match": "id", "state_status": by_id[cid].get("status")})
            if by_id[cid].get("alert_status") == "failed":
                out["retryable_failed"].append(cid)
            continue
        if nu and nu in by_url:
            out["known"].append({"id": cid, "match": "url", "existing_id": by_url[nu]})
            continue
        exact = [i for i, t in titles.items() if t and t == nt]
        if exact:
            out["known"].append({"id": cid, "match": "title", "existing_id": exact[0]})
            continue
        close = sorted(((difflib.SequenceMatcher(None, nt, t).ratio(), i) for i, t in titles.items() if t), reverse=True)[:1]
        if close and close[0][0] >= 0.9:
            out["possible_duplicates"].append({"id": cid, "title": c.get("title"), "similar_to": close[0][1], "ratio": round(close[0][0], 3)})
            continue
        out["new"].append(c)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
