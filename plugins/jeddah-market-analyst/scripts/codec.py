# -*- coding: utf-8 -*-
"""Compact id→listing-date cache stored in the snapshot (base-36, days since 2015-01-01)."""
import datetime


def b36(n):
    s, n = "", int(n)
    while True:
        n, r = divmod(n, 36)
        s = "0123456789abcdefghijklmnopqrstuvwxyz"[r] + s
        if n == 0:
            return s


EPOCH = datetime.date(2015, 1, 1)


def pack_dates(rows):
    parts = []
    for r in rows:
        d = r.get("create_iso")
        if d:
            days = (datetime.date.fromisoformat(d) - EPOCH).days
            parts.append(f"{b36(r['id'])}:{b36(days)}")
        else:
            parts.append(b36(r["id"]))
    return ",".join(parts)


def unpack_dates(s):
    out = {}
    for p in (s or "").split(","):
        if not p:
            continue
        i, _, d = p.partition(":")
        lid = str(int(i, 36))
        out[lid] = (EPOCH + datetime.timedelta(days=int(d, 36))).isoformat() if d else None
    return out


