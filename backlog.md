# Backlog

## Next

### Stored reception handler resolution — fix/stored-reception-handler-department

- [x] Resolve exact and recommended stored handlers independently of the configured fallback department; constrain only manual org-chart selections.
- Regression: configured IT fallback rejects a stored HR handler before the fix; manual HR selection must not constrain the next stored handler.
- Verification: five regressions fail before the fix; all 382 unit tests pass after it. Main pylint adds no diagnostics; Bandit finds no issues. Live GUI verification not run.
- Existing gate debt: main-only mypy reports the two deletion-list argument errors already recorded above; unchanged by this fix.

### Commit accumulated approval workflow — fix/unknown-document-stage

- [x] Verify accumulated approval decision memory, handler/reviewer/final dispatch, console input and client-dialog changes before commit.
- Verification: 378 unit tests pass; 24 changed Python files pass Black; pylint exits 0; Bandit reports no medium/high issues; whitespace check passes with CRLF handling.
- Existing gate debt remains: full mypy reports 50 errors (48 Supabase, 2 deletion paths in main); whole-repo Black flags 11 unchanged files. No hook bypass requested or used.

### Final handler task-card completion — fix/unknown-document-stage

- [x] Confirm final-handler stage for the verified handler/reception/manager signature without treating newly staged managers as completed approval.
- [x] Present DB card recommendations; capture manual selection from the client's complete unit-card chooser and read back the saved card.
- [x] Complete approval only after card/editor verification; learn confirmed selections and discard failed-document updates.
- [x] Run regressions and static checks; document live verification limits.
- Verification: 378 unit tests pass; pylint exits 0; four touched modules pass mypy with unrelated imported errors silenced; Bandit reports no issues. Live chooser and control IDs verified, final approval/DB persistence not executed.

### Avoid toolbar combo expansion during approval lookup — fix/unknown-document-stage

- [x] Replace best-match indexing in the review path's payment-info button, approval tab and approval button with exact title/control-type selectors.
- Evidence: installed pywinauto `findbestmatch.get_control_names` reads unnamed controls with `texts()`, and UIA `ComboBoxWrapper.texts()` expands/collapses combo boxes to enumerate items.
- Acceptance: the three `toolbar_scan` regression tests reject best-match indexing and pass with exact selectors. Live toolbar behavior verification pending; no approval clicked for verification.
- Verification: 362 unit tests pass; pylint exits 0; all three touched service modules pass mypy; Bandit reports no issues; changed-file whitespace checks pass.

### Submitted approval consent and line-save result — fix/unknown-document-stage

- [x] Route a submitted document with one named drafter and the operator as reviewer/approver to explicit review consent, even without a handler row.
- [x] Retain the original approval-editor wrapper; acknowledge only the exact process-scoped `결재선 변경을 완료했습니다.` result and verify both windows close before success.
- Acceptance: `test_submitted_document_routes_own_reviewer_to_consent` and `test_save_consumes_completion_result_after_original_dialog_disappears` reproduce the former failures.
- Verification: 359 unit tests pass; whole-source pylint exits 0; handler/config mypy passes; touched approval/main Bandit reports no issues; changed-file whitespace checks pass.
- Live read: `근무상황신청` shows `기안` and the configured operator as `검토` (2026-10-08). No live approval clicked. Save-result click still awaits a new manual save session.

### Unknown document stage must stop before completion — fix/unknown-document-stage

- [x] Remove the legacy stage-3 default: no roles or a superior row without completion evidence stops before task-card matching or document completion.
- Acceptance: `test_run_unverified_own_stage_never_completes_document` fails on the old classifier and passes with the guard.
- Verification: 354 unit tests pass; whole-source pylint exits 0; classifier mypy and Bandit pass; changed-file whitespace check passes with CRLF handling.
- Live read (2026-10-08): current assigned document has only handler and receptionist rows; configured operator matches the handler. This is stage 2. Historical completion cause remains unverified.

### Console focus before operator input — fix/console-focus

- [x] Focus the owning console HWND with the correct Win32 API; activate both bounded input readers before waiting for input.
- Acceptance: `test_focus_uses_native_console_handle`, `test_raw_input_focuses_console_before_reading`, `test_native_input_focuses_console_before_reader` pass.
- Verification: 352 unit tests pass; pylint exits 0; touched modules pass mypy and Black; Bandit reports no medium/high issues. Live client focus verification pending.

### Approval decision memory — feat/approval-line-reuse

- [x] Review prompt state detection: read known body text instead of an exact Static caption; accept an already-visible next/exit result without confirming approval again. Bound confirmation/result waits to 10 seconds and log observed bodies on failure.
- Prompt-state verification: 346 unit tests pass; pylint exits 0; three touched config/dialog/official modules pass mypy; Bandit reports no issues; Black and diff checks pass. Live prompt sequence verification pending.
- [x] Next-document load boundary: after a verified continuation prompt, wait for its disappearance plus a nonempty changed raw window title and an enabled main window before reading the next document. Preserve changed-document review guard; unchanged/partial loads stop within 10 seconds.
- Load-boundary verification: 343 unit tests pass; pylint exits 0; config/official-service mypy passes; Bandit reports no issues; Black and diff checks pass. Actual client load verification pending.
- [ ] Capture a live document identifier for consecutive documents with identical raw window titles; the load boundary currently stops safely rather than guessing identity.
- [x] Follow-up dialog read: UIA child wrappers have no exists(); read their text directly. Screenshot confirms `결재문서를 처리하였습니다. 다음 문서를 처리하겠습니까?` and `예(Y)`; explicit Yes click fallback added. Reproducing tests cover the reader-to-review transition and button lookup.
- Follow-up verification: 335 unit tests pass; pylint exits 0; config/dialog-handler mypy passes; Bandit reports no issues; Black and diff checks pass. Live click verification remains pending.
- [x] Review continuation: confirm only the known approval prompt after consent, require a result/next-document signal before success, continue with separate consent per document; native composed-name input with a bounded child reader.
- Review-continuation verification: 333 unit tests pass; pylint exits 0; four touched modules pass mypy; Bandit reports no medium/high issues; Black and diff checks pass. Actual IME and client-dialog verification pending.
- [x] Handler review gate: pair role/name cells, resolve operator identity, bypass classification for other handlers, click approval only on explicit consent; skip/timeout/title change stop. Empty-memory registration verified.
- Handler-review verification: 323 unit tests pass; pylint exits 0, Bandit reports no issues, Black and diff checks pass. Mypy reports 50 diagnostics in existing Supabase/deletion paths; live verification pending.
- [ ] Live verification of handler review gate: exact operator identity, composed name input, other-handler prompt, skip/consent, known approval confirmation and per-document continuation.
- [x] Approval probe close regression: replace ignored Escape with bounded win32 WM_CLOSE; regression tests cover ignored Escape and refused closure. Live verification pending.
- [x] Approval probe closure verification: retain the original HWND wrapper before closing; regression test reproduces post-close WindowSpecification lookup failure. Live verification pending.
- [x] Approval store: ordered JSON, local KNN reuse, transactional upsert, pagination, Supabase legacy no-ops
- [x] Reception fallback: config department, org-chart member selection, bounded prompts, existing handler reuse
- [x] Assigned reuse: local store in both backends, confirmed recommendations, manual dialog capture, verified application
- [x] Foundation verification: 262 unit tests pass; pylint exits 0 (9.69/10), touched local modules pass mypy, Bandit `--ini` reports no issues, Black and diff checks pass. Live-client verification not run.
- [x] Runtime unit verification: 301 tests pass; pylint exits 0 (9.70/10), six touched service/config/input modules pass mypy, Bandit `--ini` reports no issues, Black passes on all 15 touched Python files.
- [ ] Live-client verification: department/member reads, ordered line application, capture/save/cancel and 60-second timeout; see docs/runbook.md
- [x] Resolve manual approval-line capture timeout: 60 seconds maximum, approved 2026-10-07; cancel without learning on timeout
- Verified foundations: department/member readers expand lazy org nodes; stored-name resolution preserves order and rejects homonyms or incomplete reads. Raw verified role-column probing now routes the known stage-2 signature; after configuring its line, the run ends for operator submission.
- Existing gate debt: whole-project mypy has 50 diagnostics after Black formatting, identical to a same-format HEAD snapshot (41 before formatting; line splits repeat indexing diagnostics). No new type errors; Supabase JSON response types and deletion-list invariance remain.
- Existing gate debt: runbook/pre-commit use `--configfile .bandit`, but `.bandit` is INI; `bandit -r -ll --ini .bandit src/` passes.

- [ ] Capture a stage-3 live dump (결재방법 completion-marker strings) when a post-approval document is open — finalizes the 2/3 split rule
- [ ] Add RPA readers for per-row approval state + 문서정보 task-card field (after live dump lands the exact control names)
- [ ] PoC win32-hybrid RPA backend for confirm dialogs (baseline ⏱️ logs first, then win32/BM_CLICK on 확인창 only, keep UIA for TreeView/List1)
- [ ] Speed up task-card selection: replace coords mouse.click + fixed sleeps in `_perform_task_card_selection` with control click / keyboard accelerators
- [ ] Unify confirm-dialog text reads to single quick pass (`get_quick_dialog_text` + early pattern match, extend `handle_approval_result` fast-path to reception flow)

## Someday

- [ ] Revisit rich.live.Live for real-time batch progress if batch workflow needs it

## Review Backlog

- [x] [P1] Wire main.py reception flow to org-chart approval-line application: configured/selected department for manual picks, unique live resolution for stored names
- [ ] [P2] Match staged ListView rows on (department, name): List1 carries no department column, so cross-department homonyms resolve by name only
- [x] [2026-10-08 review] Guarded Desktop import for non-Windows collection; whitespace manual pick rejected; destroyed-window cancel counts as closed; apply-fail logs before manual capture
- [ ] [2026-10-08 review — needs decision] Stale next/exit prompt accepted as approval success without post-click proof; capture pre-click state or require approval prompt first (backlog intent was accept-already-visible; test_review_confirmation_accepts_already_processed_followup covers it)
- [ ] [2026-10-08 review — needs decision] Approval confirm clicks hardcoded 확인 button; 예(Y)/예(&Y) prompts fall through — use pattern list or unified clicker after live button dump
- [ ] [2026-10-08 review] resolve_approvers aborts on any empty department read; skip genuinely empty depts vs load-timeout instead of return None
- [ ] [2026-10-08 review — needs decision] _next_document_ready blocks on any 확인 dialog, so a CONTINUE immediately followed by EXIT times out — accept EXIT/CONTINUE text as ready
- [ ] [2026-10-08 review] Main.run else (task-card) branch unreachable since _classify_document returns only 1/2/4/None; remove or assert, and route future stage 3 explicitly
- [ ] [2026-10-08 review — confirmed behavior] Stage 2 ends the run after one document for operator submission; multi-assigned batches need restart

### PR #107 — fix/now review (2026-10-07)

- [ ] [debt] Extract Main.run() stage branches into handlers; complexity rose 17→20 branches / 72→81 stmts (introduced on fix/now) (source: review) — src/main.py:93
- [ ] [constraint] Narrow remaining broad excepts outside PR #106/#107 scope (approval_line_handler 15, dialog_handler 19, document_processor 5, window_manager 5 incl. bare :123, main.py deletion helpers) (source: review) — src/services/window_manager.py:123
- [ ] [debt] Narrow broad raise in confirm-button fallback (source: review) — src/services/button_controller.py:209
- [x] [plan] Reconcile approval-decision-memory spec with queue: restore Approval store / Reception fallback / Assigned reuse above; spec tracked at docs/design/approval-decision-memory.md

### PR #109 — classification safety review (2026-10-11)

- [ ] [debt] Add a bounded end-of-run learning retry or restart-persistent queue; Main.run ends after its final flush, so retained failures cannot survive process exit (source: code-review) — src/services/document_processor.py:559
- [ ] [constraint] Capture a verified document identifier/load signal before supporting same-title queue entries or distinguishing same-title manual switches; raw-title guards intentionally stop unchanged-title continuation (source: code-review) — src/services/official_service.py:307
