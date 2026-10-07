# Backlog

## Now

- [x] Build 접수 approval line from org chart in predetermined order (TreeView + ▶ 추가 + order buttons)
- [x] Capture live window dump (결재선 ListView columns/completion markers + 문서정보 task-card control) via debug manager option 1 — blocks stage 2/3 split (see docs/design/document-stages.md open questions)
  - Verified 2026-10-07 (stage-2 doc): List1 cols [직위, 직급, 결재방법, 결재자]; rows 접수+업무담당자, no superior; 과제카드ComboBox in 결재정보 dialog, value empty
- [ ] Add classify_stage() 1/2/3 splitter in Main.run() before is_reception_document branch: stage 1 = title ^접수; stage 2 = List1 has 접수+업무담당자 rows and no 결재/completion row → set_approval_line([superiors]); stage 3 = completion markers present → document_sort (exact stage-3 markers TBD)
- [ ] Narrow remaining broad excepts in supabase_service.py and official_service.py polling helpers
- [ ] [constraint] Centralize env-var reads in config.py so `rg "SUPABASE_KEY|OPENAI_API_KEY" src/services/ src/ui/` is empty
- [ ] [constraint] Route remaining time.sleep call sites through named wait helpers so `rg "time\.sleep" src/` is empty
- [ ] Retune local-vector similarity threshold vs 0.3 and document reindex requirement (Supabase 1536-dim vectors do not transfer)

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
