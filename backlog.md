# Backlog

## Next

- [ ] Capture a stage-3 live dump (결재방법 completion-marker strings) when a post-approval document is open — finalizes the 2/3 split rule
- [ ] Add RPA readers for per-row approval state + 문서정보 task-card field (after live dump lands the exact control names)
- [ ] PoC win32-hybrid RPA backend for confirm dialogs (baseline ⏱️ logs first, then win32/BM_CLICK on 확인창 only, keep UIA for TreeView/List1)
- [ ] Speed up task-card selection: replace coords mouse.click + fixed sleeps in `_perform_task_card_selection` with control click / keyboard accelerators
- [ ] Unify confirm-dialog text reads to single quick pass (`get_quick_dialog_text` + early pattern match, extend `handle_approval_result` fast-path to reception flow)
- [ ] Split remaining oversized RPA modules on next touch (dialog_handler.py 564 lines)

## Someday

- [ ] Revisit rich.live.Live for real-time batch progress if batch workflow needs it

## Review Backlog

- [ ] [P1] Wire main.py 접수 flow to OfficialCollector.set_approval_line (needs department source for vector-matched approvers; approval() still live)
- [ ] [P2] Match staged ListView rows on (department, name): List1 carries no department column, so cross-department homonyms resolve by name only
