# Network — what to do on exit 3

Hosts the cloud run needs (egress allowlist):

| Host | Used for | If blocked |
|---|---|---|
| `sa.aqar.fm` | listing pages | Stop. Publish nothing. Ask for this one host. |
| `prod-srem-api-srem.moj.gov.sa` | البورصة statistics | Expected: resets from the cloud. Use Chrome (below). |
| `prod-inquiryservice-srem.moj.gov.sa` | البورصة district lookup | Chrome fallback (same run). |
| `*.frame.claudeusercontent.com` | reading the live dashboard + its files | **Not a blocker.** Use the project fallback baseline and publish normally. |

`srem.moj.gov.sa` itself is never called. Do not ask for it.

Check `curl -sS "$HTTPS_PROXY/__agentproxy/status"` → `recentRelayFailures` to see which host
the proxy refused. A 403 at CONNECT is policy (allowlist). A connect **timeout** on an MOJ host
that *is* allowlisted means the ministry is refusing non-Saudi traffic — the allowlist cannot
fix that; go to the fallback.

## Chrome path for البورصة (the normal path since 28 Sep 2026)

Allowlisted on 28 Sep 2026 and still refused: the tunnel opens, the MOJ server resets it
(`ws_closed_mid_exchange`, 39 B received). This is the ministry refusing non-Saudi IPs, not
the allowlist. Keep the entries (they cost nothing, and the cloud attempt is the first thing
tried), but expect Chrome to do this half.

Needs Claude in Chrome on the user's machine (Chrome open, extension connected). aqar still runs in the cloud —
`sa.aqar.fm` answers Python's urllib but blocks curl (Cloudflare fingerprint).

1. Run `aqar_fetch.py` as normal and build `$RUN/seeds.json`.
2. Open a new tab at `https://srem.moj.gov.sa/`.
3. Read `scripts/srem_chrome.js`, replace `__SEEDS__` with the contents of `$RUN/seeds.json`,
   run it with the javascript tool. It returns `started` and works in the background
   (~15–25 min for ~110 districts, three at a time, because the API times out often).
4. Poll `JSON.stringify({done:window.__srem.done,p:window.__srem.progress,n:window.__srem.chunks.length})` (typically 3–5 chunks)
   every few minutes.
5. When done, read `JSON.stringify(window.__srem.sums)` and write it to `$RUN/srem_sums.json`.
   Then for each i read `window.__srem.chunks[i]` and write it **verbatim** with the Write tool to
   `$RUN/srem_parts/000.txt`, `001.txt`, … (no edits, no trailing newline).
6. `python3 srem_assemble.py --parts-dir "$RUN/srem_parts" --sums "$RUN/srem_sums.json" --out "$RUN/srem.json"`.
   It checks every chunk against Chrome's checksum, then runs the same gates as `srem_fetch.py`.
   A checksum failure names the chunk: re-read that one chunk and rewrite it.
7. Continue with Build. Say in the handover that البورصة was read through Chrome.

If Chrome is not reachable either, build and publish without `srem.json`: every البورصة figure
shows «غير متوفر», the run is PARTIAL, and the handover says البورصة could not be read and why.
Never reuse the previous run's البورصة numbers.
