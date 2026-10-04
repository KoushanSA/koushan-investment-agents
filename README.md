# Koushan Investment Agents

Private Claude plugin marketplace for Koushan's investment and real-estate agents (Claude AI 2.0).
Access is controlled by the **KoushanSA** GitHub org — you must be a member of the team that has read access to this repo.

## Agents

| Plugin | What it does |
|---|---|
| `furas-opportunity-scout` | Weekly scan of the Furas (فرص) portal for long-term investment opportunities in Riyadh, Jeddah, Mecca and Medina → Arabic dashboard; deep-dive on a single opportunity's كراسة; map pins. |

## Install

### Claude Code
```
/plugin marketplace add KoushanSA/koushan-investment-agents
/plugin install furas-opportunity-scout@koushan-investment-agents
```
Private repo: you need to be signed in to GitHub with an account that has access (e.g. `gh auth login`, or Git credentials that can clone the repo).

### Claude desktop app (Cowork)
Customize → Plugins → add a marketplace → enter `KoushanSA/koushan-investment-agents`, then install **furas-opportunity-scout**.

## Network requirements (Furas)
The agent needs network access to `gisapps.balady.gov.sa` and `furas.momah.gov.sa` (exact hostnames). See the plugin README.

## Updating
Bump `version` in both `plugins/<name>/.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`, then push. Users get the update via `/plugin marketplace update`.
