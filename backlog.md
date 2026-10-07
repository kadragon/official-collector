# Backlog

## Now

- [x] Build 접수 approval line from org chart in predetermined order (TreeView + ▶ 추가 + order buttons)
- [ ] Narrow remaining broad excepts in supabase_service.py and official_service.py polling helpers
- [ ] [constraint] Centralize env-var reads in config.py so `rg "SUPABASE_KEY|OPENAI_API_KEY" src/services/ src/ui/` is empty
- [ ] [constraint] Route remaining time.sleep call sites through named wait helpers so `rg "time\.sleep" src/` is empty
- [ ] Retune local-vector similarity threshold vs 0.3 and document reindex requirement (Supabase 1536-dim vectors do not transfer)

## Next

- [ ] PoC win32-hybrid RPA backend for confirm dialogs (baseline ⏱️ logs first, then win32/BM_CLICK on 확인창 only, keep UIA for TreeView/List1)
- [ ] Speed up task-card selection: replace coords mouse.click + fixed sleeps in `_perform_task_card_selection` with control click / keyboard accelerators
- [ ] Unify confirm-dialog text reads to single quick pass (`get_quick_dialog_text` + early pattern match, extend `handle_approval_result` fast-path to reception flow)
- [ ] Split remaining oversized RPA modules on next touch (dialog_handler.py 564 lines)

## Someday

- [ ] Revisit rich.live.Live for real-time batch progress if batch workflow needs it
