# First-time setup (one user, one library)

Run this only when `claude/re_reg_monitor_config.json` does not exist, and only with the user present. It creates the user's own decisions library, fills it with a baseline, and saves the config. **It never sends an alert.**

Run inside a Claude Project — the config, backups and run logs are project docs. If no Project is attached, say so and stop.

## 1. Ask (one AskUserQuestion)
- **Alert recipient(s):** who receives one email per new decision. Default: the user themself (`get_me`). Several addresses are allowed.
- Confirm that alerts are sent from **their own** Outlook account through the Microsoft 365 connector. If that connector isn't connected, the library still works; alerts can't be sent until it is.

## 2. Publish the library page
Publish `${CLAUDE_PLUGIN_ROOT}/skills/re-reg-scan/assets/library.html` with the Artifact tool (new artifact, no `url`):
- `icon`: `law`
- `capabilities`: `{"db": {"rules": [{"path": "", "read": "view", "write": "admin"}]}}` — viewers read, only the owner writes. Load the `artifact-capabilities` skill first if the Artifact tool asks for it.
- Record the returned URL as `library_url`.

## 3. Build the baseline
Do steps 2 and 4 of the weekly run (collect + classify) over the **full** history of all three sources, not just recent pages. Write every row with `baseline: true`, `alert_status: "baseline"`, `first_seen` = today. Use `batch` writes. Then `set` `meta/run` with `library_url`, `last_updated`, `last_run_date` (today), `run_count: 1`, `last_run_summary` («خط الأساس: N قرار — X فعّالة، Y سابقة، Z غير مؤكدة»).

This takes a while (~50–60 decisions at the last check). Opus is recommended for this step.

## 4. Save the config
`project_write` `claude/re_reg_monitor_config.json`:
```json
{"library_url": "<url>", "alert_to": ["..."], "sender_name": "<display name from get_me>", "created": "<YYYY-MM-DD>"}
```
Also write the backup `claude/re_reg_monitor_state.json`.

## 5. Hand over
- The library link and the counts per tab.
- Remind them the page is private until they share it (Share menu on the artifact) with the alert recipients.
- Offer to create the weekly scheduled task (suggested: Sundays ~07:55 Asia/Riyadh) with the prompt «run the regulatory scan».
