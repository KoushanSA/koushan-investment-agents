# -*- coding: utf-8 -*-
"""HTTP helpers. stdlib only. Honours HTTPS_PROXY / SSL_CERT_FILE from the environment."""
import json, time, gzip, zlib, urllib.request, urllib.error, urllib.parse, socket
from config import UA


class Blocked(RuntimeError):
    """Egress proxy refused the host (403 on CONNECT) or DNS/connect failed. Carries the host."""
    def __init__(self, host, detail):
        super().__init__(f"{host}: {detail}")
        self.host = host


def _host(url):
    return urllib.parse.urlsplit(url).hostname or url


def request(url, data=None, headers=None, timeout=45, tries=4, backoff=1.5, accept_404=True):
    # gzip cuts aqar transfer ~6x (a first full run pulled ~8 GB uncompressed on 28 Sep 2026)
    h = {"User-Agent": UA, "Accept-Language": "ar", "Accept-Encoding": "gzip, deflate"}
    if headers:
        h.update(headers)
    last = None
    for i in range(tries):
        try:
            rq = urllib.request.Request(url, data=data, headers=h, method="POST" if data is not None else "GET")
            with urllib.request.urlopen(rq, timeout=timeout) as r:
                raw, enc = r.read(), (r.headers.get("Content-Encoding") or "").lower()
                if enc == "gzip":
                    raw = gzip.decompress(raw)
                elif enc == "deflate":
                    raw = zlib.decompress(raw)
                return r.status, raw.decode("utf-8", "replace"), r.geturl()
        except urllib.error.HTTPError as e:
            if e.code == 404 and accept_404:
                return 404, "", url
            body = ""
            try:
                raw = e.read()
                if (e.headers.get("Content-Encoding") or "").lower() == "gzip":
                    raw = gzip.decompress(raw)
                body = raw.decode("utf-8", "replace")
            except Exception:
                pass
            if e.code >= 500 and body:          # SREM returns JSON bodies on 500
                return e.code, body, url
            last = f"HTTP {e.code}"
        except urllib.error.URLError as e:
            msg = str(e.reason)
            if "403" in msg or "Tunnel" in msg or "CONNECT" in msg:
                raise Blocked(_host(url), msg)
            if "reset" in msg.lower() and i == tries - 1:
                # MOJ hosts accept the tunnel and then reset — they refuse non-Saudi traffic (28 Sep 2026)
                raise Blocked(_host(url), msg)
            last = msg
        except (socket.timeout, TimeoutError) as e:
            last = f"timeout {e}"
        except ConnectionResetError as e:
            last = f"reset {e}"
            if i == tries - 1:
                raise Blocked(_host(url), last)
        except Exception as e:  # noqa
            last = repr(e)
        time.sleep(backoff * (i + 1))
    if last and ("timed out" in last or "timeout" in last or "Name or service" in last
                 or "unreachable" in last.lower()):
        raise Blocked(_host(url), last)
    raise RuntimeError(f"failed after {tries} tries: {url[:120]} :: {last}")


def post_json(url, payload, **kw):
    st, body, _ = request(url, data=json.dumps(payload).encode(),
                          headers={"Content-Type": "application/json", "Accept": "application/json",
                                   "Origin": "https://srem.moj.gov.sa", "Referer": "https://srem.moj.gov.sa/"},
                          **kw)
    try:
        return st, json.loads(body) if body else {}
    except json.JSONDecodeError:
        return st, {"_raw": body[:300]}


def get_json(url, params=None, **kw):
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    st, body, _ = request(url, headers={"Accept": "application/json",
                                        "Origin": "https://srem.moj.gov.sa"}, **kw)
    try:
        return st, json.loads(body) if body else {}
    except json.JSONDecodeError:
        return st, {"_raw": body[:300]}
