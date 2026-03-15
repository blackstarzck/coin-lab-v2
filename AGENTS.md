# AGENTS.md

## Working Rules

- Before starting a task, identify the primary files or folders that will be touched.
- If a task touches user-visible Korean text, preserve UTF-8 exactly and avoid bulk replacement of Korean strings without re-reading the saved file.
- If editing a file that was changed earlier in the session, first verify that previously approved requirements are still present and preserve them unless the user explicitly changes them.
- Do not silently overwrite approved UI or behavior. If a new request conflicts with an earlier approved state, explain the conflict before editing.
- When the user confirms a result is good, propose leaving a checkpoint commit before starting the next substantial change.
- Never report a change as complete unless the saved file contents have been re-checked.
- Before saying a change is done, verify all three when relevant: file contents, `git diff`, and a build/test/runtime check. If any verification is skipped, say so explicitly.
- When reading or verifying files that contain Korean text, use UTF-8-safe commands or settings and confirm the rendered text is still valid Korean rather than mojibake.
- Before completing a task that touched Korean UI text, search the changed files for corruption signals such as `�`, broken compatibility glyphs, or stray `?` inside labels and fix them.
- For large UI files, prefer extracting or editing smaller scoped sections instead of rewriting the whole page at once.
- In tables or lists, only use `hover` styling when the row or item has an explicit click action. If there is no click action, do not use `hover` or any hover-only affordance.
- In completion reports, include the files changed and what was verified so the current state is easy to audit.

## Network Flow Guardrail

- If a task touches dashboard or monitoring data flow, page landing sequence, websocket lifecycle, React Query cache invalidation, session selection, symbol selection, or the UI impact of REST/WebSocket data, read [docs/NETWORK_FLOW_PLAYBOOK.md](./docs/NETWORK_FLOW_PLAYBOOK.md) before making changes.
- Treat [docs/NETWORK_FLOW_PLAYBOOK.md](./docs/NETWORK_FLOW_PLAYBOOK.md) as the maintenance reference for how connections start, which page owns them, and which widgets they affect.
- If implementation changes any documented flow, sequence, ownership, endpoint, cache dependency, or page impact, update [docs/NETWORK_FLOW_PLAYBOOK.md](./docs/NETWORK_FLOW_PLAYBOOK.md) in the same task.
- In the completion report for related work, state whether [docs/NETWORK_FLOW_PLAYBOOK.md](./docs/NETWORK_FLOW_PLAYBOOK.md) was reviewed and whether it was updated.
