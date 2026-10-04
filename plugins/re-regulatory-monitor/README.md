# Real Estate Regulatory Monitor (Koushan)

Weekly monitor of Saudi real estate decisions from **جريدة أم القرى**, **الهيئة العامة للعقار** and
**وزارة البلديات والإسكان**. Keeps an Arabic decisions library with three tabs — فعّالة، سابقة / ملغاة،
غير مؤكدة — each row carrying its official link and the evidence for its status, and emails one alert
per genuinely new decision.

## First run (setup)
Inside a Claude Project, say «set up the regulatory monitor». Claude will:
1. ask who should receive alerts (default: you),
2. publish **your own** library page,
3. build a baseline from the three sources (no emails are sent for the baseline),
4. save your settings in the project doc `claude/re_reg_monitor_config.json`.

Then schedule a weekly task (suggested Sundays ~07:55 Riyadh) with the prompt «run the regulatory scan».

## Requirements
- Microsoft 365 connector (Outlook) for alerts — sent from your own mailbox.
- Optional allowlist: `www.uqn.gov.sa`, `uqn.gov.sa`, `rega.gov.sa`, `momah.gov.sa`, `idlelands.momah.gov.sa`.
  Runs work through WebFetch without it.

## Model
Sonnet for weekly runs; Opus for the first-time baseline.
