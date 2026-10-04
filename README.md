# Koushan Investment Agents

Claude plugin marketplace for Koushan's investment and real-estate agents (Claude AI 2.0). No GitHub account needed to install.

## Agents

| Plugin | What it does |
|---|---|
| `furas-opportunity-scout` | Weekly scan of the Furas (فرص) portal for long-term investment opportunities in Riyadh, Jeddah, Mecca and Medina → Arabic dashboard; deep-dive on a single opportunity's كراسة; map pins. |
| `jeddah-market-analyst` | Twice-weekly Jeddah market analysis (MOJ Real Estate Exchange + aqar.fm) → «مرصد جدة العقاري» dashboard; single-listing analysis. |
| `re-regulatory-monitor` | Weekly Saudi real estate regulatory scan (Umm Al-Qura, REGA, MOMAH) → decisions library + one email alert per new decision. |

## Install

### Claude Code
```
/plugin marketplace add KoushanSA/koushan-investment-agents
/plugin install furas-opportunity-scout@koushan-investment-agents
/plugin install jeddah-market-analyst@koushan-investment-agents
/plugin install re-regulatory-monitor@koushan-investment-agents
```

### Claude desktop app (Cowork)
Customize → Plugins → add a marketplace → enter `KoushanSA/koushan-investment-agents`, then install the agents you need.

Jeddah and Regulatory create **your own** dashboard/library on the first run — run them inside a Claude Project so the link is remembered.

## Network requirements (Furas)
The agent needs network access to `gisapps.balady.gov.sa` and `furas.momah.gov.sa` (exact hostnames). See the plugin README.

## Updating
Bump `version` in both `plugins/<name>/.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`, then push. Users get the update via `/plugin marketplace update`.
