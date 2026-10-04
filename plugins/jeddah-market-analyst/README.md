# Jeddah Market Analyst (Koushan)

Twice-weekly analyst for the Jeddah real estate market.

**Sources:** البورصة العقارية (MOJ Real Estate Exchange: weekly executed deals, value, SAR/m², by district)
and aqar.fm (every active Jeddah listing, sale and rent).

**Output each run:** one Arabic dashboard, «مرصد جدة العقاري», at a link that stays the same. It carries the
report, KPIs, opportunities, the district table, the trend and the data-quality checks. There's also a CSV
with one row per listing / deal / district aggregate, downloadable from the dashboard and archived per run.

## Skills
- `jeddah-market-scan`: the full run (suggested schedule: Sun + Tue 09:50 Riyadh).
- `jeddah-listing-analyze`: one listing (aqar link or pasted text) placed against its district.

## Network allowlist (cloud runs)
`sa.aqar.fm`, `prod-srem-api-srem.moj.gov.sa`, `prod-inquiryservice-srem.moj.gov.sa`, and
optionally `*.frame.claudeusercontent.com`. The MOJ hosts may refuse non-Saudi traffic. In that case
the البورصة half falls back to Claude in Chrome (see `skills/jeddah-market-scan/references/network.md`).

## Known limits (from the sources, not the agent)
- البورصة publishes no per-deal list and no split by property type, so executed land vs apartment
  totals are not available.
- aqar never marks an ad as sold. Listing dates come from each ad's page and are backfilled
  over the first few runs.

## First run
Say «run the Jeddah market scan». The first run publishes **your own** dashboard and saves its link in the
project doc `claude/jeddah_market_state.md` (run it inside a Claude Project so the link is remembered).
Every later run updates that same link. A full run takes ~15–30 minutes.
