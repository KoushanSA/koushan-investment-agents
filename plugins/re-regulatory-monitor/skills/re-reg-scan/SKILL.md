---
name: re-reg-scan
description: Weekly Saudi real estate regulatory monitor — scan Umm Al-Qura, REGA and MOMAH for new real estate decisions, keep the Arabic decisions library (فعّالة / سابقة-ملغاة / غير مؤكدة) current, and email one alert per genuinely new decision. Use when the user says "run the regulatory scan", "check for new real estate decisions", "update the decisions library", "set up the regulatory monitor", "رصد القرارات العقارية", "مكتبة القرارات العقارية", "هل صدر قرار عقاري جديد", or when the weekly scheduled regulatory run fires.
---

# Real Estate Regulatory Monitor — weekly run

Keep the user's decisions library current and alert on every new real estate decision, with zero duplicate alerts across runs.

## Configuration (per user — nothing user-specific lives in this plugin)

Read the project doc `claude/re_reg_monitor_config.json` (`project_read`):

```json
{
  "library_url": "https://claude.ai/artifact/<id>",
  "alert_to": ["name@company.com"],
  "sender_name": "Display name of the Outlook account that sends the alerts",
  "created": "YYYY-MM-DD"
}
```

- **Doc exists** → use it. The active-tab link used in emails is `<library_url>#active`.
- **Doc missing** → run first-time setup in `references/setup.md`, then stop. Setup builds a baseline and never sends alerts.
- **Scheduled / unattended run with no config** → do not guess recipients. Stop and report that setup is needed.

| Item | Value |
|---|---|
| State | the library artifact's database: `decisions/<id>` (one doc per decision) and `meta/run` |
| Sender | the signed-in Outlook account (Microsoft 365 connector, `outlook_send_mail`) |
| Backup + run log | project docs `claude/re_reg_monitor_state.json` and `claude/RE_Reg_Monitor_Run_<YYYY-MM-DD>.md` |

Approved sources only: جريدة أم القرى، الهيئة العامة للعقار، وزارة البلديات والإسكان. Never add sources unless the user explicitly asks. Do not use laws.boe.gov.sa (it disallows automated access).

## Hard rules

1. **Never invent or construct a URL.** A row's `url` must be a page or file you actually opened and whose content matches. If no direct link can be reached, set `url: null` and say so in `note` («تعذّر الوصول لرابط مباشر…»).
2. **Status comes from the source, never inference.** `active` only if the source says ساري / in force, or it is the latest published version with an official effective date and no later amendment or repeal found in the three sources. Otherwise `uncertain` with a specific `reason`. `superseded` only when a source states the repeal/replacement — record reason and date in `reason`.
3. **Active and superseded never mix.** Moving a decision between tabs means changing its `status` field on its one doc.
4. **One alert per decision, ever.** Alert only for a decision whose id is not already in `decisions`, and whose canonical URL and normalized title don't match an existing doc. Never re-alert a doc with `alert_status` of `sent`, `sending` or `baseline`.
5. **No alerts on a baseline or a failed read.** If a source could not be read this run, say so in the run summary; never treat "couldn't read" as "nothing new" silently.
6. **Only the library owner runs alerts.** If the `ArtifactData` write fails with a permission error, the current user does not own this library — stop, send nothing, and tell them to run setup for their own library or ask the owner.

Full scope, status rules and record schema: `references/classification.md`. Source URLs, pagination and gotchas: `references/sources.md`. Email template: `references/alert-email.md`.

## Steps

### 1. Load state
- `ArtifactData list` on `decisions` (limit 1000) with `out_dir` set to a scratch folder, and `get` `meta/run`. Keep each doc's `version`.
- If the database is empty or unreadable, **stop** and report — do not rebuild from scratch and do not send alerts. The backup in `claude/re_reg_monitor_state.json` can restore it only when the user asks.
- Look for any doc with `alert_status: "sending"` (a previous run crashed mid-send). For each, search Sent Items (`outlook_email_search`, `query` = the decision's short title, `recipient` = the first alert address). Found → update to `sent`. Not found → leave as `sending`, flag it in the run summary for a human; never resend automatically.

### 2. Collect candidates (read-only)
Fetch in this order; prefer a short Python script (curl) for listing pages when the host is reachable, otherwise WebFetch; fall back to the user's Chrome only for a page both fail on.
1. Umm Al-Qura RSS `rssFeed/21`, then listing pages `decisions/rules-and-regulations?pgno=1..N` until an item dated before the previous `meta/run.last_run_date` minus 14 days (overlap window), plus the authorities listing for REGA board decisions.
2. REGA regulations library `?page=1..` until a page repeats; REGA news (first 2 pages) for new rules announced but not yet in the library.
3. MOMAH `ar/regulations?pageNumber=1..3` (newest first) and MOMAH news items mentioning رسوم الأراضي البيضاء / العقارات الشاغرة / تملك.

Keep only real estate items per `references/classification.md` scope. For each candidate open the item page itself before accepting it.

### 3. Diff against state
Write candidates to `candidates.json` (schema in classification.md) and run:
`python3 ${CLAUDE_PLUGIN_ROOT}/skills/re-reg-scan/scripts/diff_state.py --state <out_dir>/decisions --candidates candidates.json`
It prints `new`, `possible_duplicates` (same URL or near-identical title under another id — resolve by reading, default to *not new*), and `known`. For known items, compare status: if a source now shows a repeal/amendment, prepare a status change (no email).

### 4. Classify new items
Open each new item's source. Fill every field. Apply the status rules. When a new instrument repeals or replaces an existing one, also prepare the status change of the old doc to `superseded` with reason and date.

### 5. Write, then alert (per new decision, in this order)
1. `set` `decisions/<id>` with `first_seen` = today, `baseline: false`, `alert_status: "sending"`.
2. Send the email per `references/alert-email.md` with `outlook_send_mail` to every address in `alert_to`.
3. `update` the doc with `alert_status: "sent"`, `alerted_at` (ISO timestamp). If the send failed, set `alert_status: "failed"` and report it; a `failed` doc may be retried on the next run (it was never delivered).

Apply status changes to existing docs with `update` pinned to their `version`. Use `batch` for more than two writes.

### 6. Close the run
- `update` `meta/run`: `last_updated` (ISO, now), `last_run_date` (today, YYYY-MM-DD), `run_count` +1, `library_url`, `last_run_summary` (one Arabic line: counts, new, status changes, sources that failed).
- Write `claude/re_reg_monitor_state.json` to the project: `{generated, library_url, docs: [{id, status, url, alert_status}]}`.
- Write `claude/RE_Reg_Monitor_Run_<date>.md`: new decisions, alerts sent, status changes, sources unreachable, items left uncertain and why.
- Do not republish the artifact page; the page reads the database live.

## Output
End with a short summary: new decisions (title → tab), alerts sent, status changes, anything a human must check. If nothing new: say so, and say which sources were read successfully.

## Model
Weekly runs: Sonnet is sufficient. Use Opus for the first-time baseline and for re-classification.
