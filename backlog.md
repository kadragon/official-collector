# Backlog

## Now

- [ ] Narrow remaining broad excepts in supabase_service.py and official_service.py polling helpers
- [ ] [constraint] Centralize env-var reads in config.py so `rg "SUPABASE_KEY|OPENAI_API_KEY" src/services/ src/ui/` is empty
- [ ] [constraint] Route remaining time.sleep call sites through named wait helpers so `rg "time\.sleep" src/` is empty
- [ ] Retune local-vector similarity threshold vs 0.3 and document reindex requirement (Supabase 1536-dim vectors do not transfer)

## Next

- [ ] Split remaining oversized RPA modules on next touch (dialog_handler.py 564 lines)

## Someday

- [ ] Revisit rich.live.Live for real-time batch progress if batch workflow needs it
