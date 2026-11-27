# Backlog

Historical verification notes. Track active work in [GitHub Issues](https://github.com/kadragon/official-collector/issues).

## Next

### Stored reception handler resolution — fix/stored-reception-handler-department

- Regression: configured IT fallback rejects a stored HR handler before the fix; manual HR selection must not constrain the next stored handler.
- Verification: five regressions fail before the fix; all 382 unit tests pass after it. Main pylint adds no diagnostics; Bandit finds no issues. Live GUI verification not run.
- Existing gate debt: main-only mypy reports the two deletion-list argument errors already recorded above; unchanged by this fix.

### Commit accumulated approval workflow — fix/unknown-document-stage

- Verification: 378 unit tests pass; 24 changed Python files pass Black; pylint exits 0; Bandit reports no medium/high issues; whitespace check passes with CRLF handling.
- Existing gate debt remains: full mypy reports 50 errors (48 Supabase, 2 deletion paths in main); whole-repo Black flags 11 unchanged files. No hook bypass requested or used.

### Final handler task-card completion — fix/unknown-document-stage

- Verification: 378 unit tests pass; pylint exits 0; four touched modules pass mypy with unrelated imported errors silenced; Bandit reports no issues. Live chooser and control IDs verified, final approval/DB persistence not executed.

### Avoid toolbar combo expansion during approval lookup — fix/unknown-document-stage

- Evidence: installed pywinauto `findbestmatch.get_control_names` reads unnamed controls with `texts()`, and UIA `ComboBoxWrapper.texts()` expands/collapses combo boxes to enumerate items.
- Acceptance: the three `toolbar_scan` regression tests reject best-match indexing and pass with exact selectors. Live toolbar behavior verification pending; no approval clicked for verification.
- Verification: 362 unit tests pass; pylint exits 0; all three touched service modules pass mypy; Bandit reports no issues; changed-file whitespace checks pass.

### Submitted approval consent and line-save result — fix/unknown-document-stage

- Acceptance: `test_submitted_document_routes_own_reviewer_to_consent` and `test_save_consumes_completion_result_after_original_dialog_disappears` reproduce the former failures.
- Verification: 359 unit tests pass; whole-source pylint exits 0; handler/config mypy passes; touched approval/main Bandit reports no issues; changed-file whitespace checks pass.
- Live read: `근무상황신청` shows `기안` and the configured operator as `검토` (2026-10-08). No live approval clicked. Save-result click still awaits a new manual save session.

### Unknown document stage must stop before completion — fix/unknown-document-stage

- Acceptance: `test_run_unverified_own_stage_never_completes_document` fails on the old classifier and passes with the guard.
- Verification: 354 unit tests pass; whole-source pylint exits 0; classifier mypy and Bandit pass; changed-file whitespace check passes with CRLF handling.
- Live read (2026-10-08): current assigned document has only handler and receptionist rows; configured operator matches the handler. This is stage 2. Historical completion cause remains unverified.

### Console focus before operator input — fix/console-focus

- Acceptance: `test_focus_uses_native_console_handle`, `test_raw_input_focuses_console_before_reading`, `test_native_input_focuses_console_before_reader` pass.
- Verification: 352 unit tests pass; pylint exits 0; touched modules pass mypy and Black; Bandit reports no medium/high issues. Live client focus verification pending.

### Approval decision memory — feat/approval-line-reuse

- Prompt-state verification: 346 unit tests pass; pylint exits 0; three touched config/dialog/official modules pass mypy; Bandit reports no issues; Black and diff checks pass. Live prompt sequence verification pending.
- Load-boundary verification: 343 unit tests pass; pylint exits 0; config/official-service mypy passes; Bandit reports no issues; Black and diff checks pass. Actual client load verification pending.
- Follow-up verification: 335 unit tests pass; pylint exits 0; config/dialog-handler mypy passes; Bandit reports no issues; Black and diff checks pass. Live click verification remains pending.
- Review-continuation verification: 333 unit tests pass; pylint exits 0; four touched modules pass mypy; Bandit reports no medium/high issues; Black and diff checks pass. Actual IME and client-dialog verification pending.
- Handler-review verification: 323 unit tests pass; pylint exits 0, Bandit reports no issues, Black and diff checks pass. Mypy reports 50 diagnostics in existing Supabase/deletion paths; live verification pending.
- Verified foundations: department/member readers expand lazy org nodes; stored-name resolution preserves order and rejects homonyms or incomplete reads. Raw verified role-column probing now routes the known stage-2 signature; after configuring its line, the run ends for operator submission.
- Existing gate debt: whole-project mypy has 50 diagnostics after Black formatting, identical to a same-format HEAD snapshot (41 before formatting; line splits repeat indexing diagnostics). No new type errors; Supabase JSON response types and deletion-list invariance remain.
- Existing gate debt: runbook/pre-commit use `--configfile .bandit`, but `.bandit` is INI; `bandit -r -ll --ini .bandit src/` passes.
