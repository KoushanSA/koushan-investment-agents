# Run state

Each user has their **own** dashboard. Nothing user-specific is stored in the plugin.

- **Dashboard URL — source of truth:** the project doc `claude/jeddah_market_state.md`
  (`project_read`). Use the dashboard link written there.
- **No such doc, but the user gave a dashboard link** in the conversation or scheduled prompt → use that link.
- **Neither** → this is the user's first run: publish a new dashboard (omit `url`), then
  `project_write` `claude/jeddah_market_state.md` with the new link (when a Project is attached),
  and tell the user to keep the link — later runs must update the same artifact, never create a new one.
  With no Project attached, ask the user to put the link in the scheduled task's prompt.
- Project docs written each run (when a Project is attached): `claude/jeddah_market_snapshot.json`
  (baseline, no listing ids), `claude/Jeddah_Market_Report_<date>.md`.
- Suggested schedule: Sundays and Tuesdays, ~09:50 Asia/Riyadh.
