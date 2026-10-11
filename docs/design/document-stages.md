# Document Stages: Reception / Assigned-to-Me / Post-Approval Task Processing

Status: stage-2 runtime wiring implemented (2026-10-07); stage-3 completion discriminator remains open.
Source: live-client observations + current code (`src/main.py`, `src/services/official_service.py`,
`src/utils/text_utils.py`, `src/config.py`, `src/services/approval_line_handler.py`).

## The 3 stages

1. **Reception (접수)** — window title starts with `접수:`. Run the reception cycle:
   `approval()` + `add_share()` + `reception()` (`src/main.py:161-170`,
   `src/services/official_service.py:135/118/211`).
2. **Assigned to me (나에게 배정)** — title starts with `전자결재:`, approval line shows the
   receptionist plus the user as handler (업무담당자). Action: insert the user's superior
   (상위 결재권자) into the approval line via `OfficialCollector.set_approval_line()`
   (`src/services/official_service.py:175`), NOT the task-card flow.
3. **Post-approval task processing (결재완료 후 업무처리)** — looks like stage 2 but approval is
   complete. Action: select the task card in 문서정보 via `document_sort()` /
   `_perform_task_card_selection()` (`src/services/official_service.py:275/320`).

## Original code gap (before the stage splitter)

`Main.run()` (`src/main.py:154`) splits only two ways: `is_reception_document(title)`
(`src/utils/text_utils.py:87-91`, prefix `src/utils/text_utils.py:44`, window patterns
`src/config.py:118-121`) → reception flow; otherwise `extract_title_from_approval()` +
`process_task_card_matching()` + `document_sort()` (`src/main.py:178-183`,
`src/utils/text_utils.py:63-84`). Stages 2 and 3 collapse into one electronic-approval path,
so a stage-2 document would wrongly enter task-card selection and never get its superior
added to the approval line.

## Discriminators

| Signal | Stage 1 | Stage 2 | Stage 3 |
|---|---|---|---|
| Window title | `접수:` prefix | `전자결재:` prefix | `전자결재:` prefix (title alone cannot split 2/3) |
| Approval ListView (`List1`, `결재자` column; read via `ApprovalLineHandler.read_approver_names`, `src/services/approval_line_handler.py:205`) | reception line (empty or reception default) | receptionist + user present, no superior above user | completion stamps present, user pending as handler |
| Buttons | `접수` enabled (`src/services/official_service.py:237`) | `결재` enabled, no `접수` | `결재`/process button, no `접수` |
| 문서정보 task-card field | n/a | must stay untouched | empty → selection required (`과제카드 선택` dialog, `src/services/official_service.py:327`) |

## Proposed shape (not yet implemented)

- `classify_stage(title, approver_names, approval_complete, task_card_set)` → `1 | 2 | 3`,
  called in `Main.run()` before the `is_reception_document` branch.
- Stage 2 → `set_approval_line([superiors...])`; stage 3 → existing `_process_approval_document`.
- New RPA readers needed: approval-line names (exists), per-row approval state + 문서정보
  task-card field state (missing — requires live `print_control_identifiers` dump via
  `uv run -m src.debug.debug_manager`, option 1).

## Verified against live client (2026-10-07, stage-2 document, read-only probe)

- Main window: `전자결재: [ 보안등급 : 99 ] [ 붙임 : 2 ](이첩) 국민제안 감사아이디어 공모제 실시 안내`
  — matches `extract_title_from_approval()` (skip two `[...]` pairs).
- Approval `List1` columns: `['직위', '직급', '결재방법', '결재자']` — the existing
  `결재자`-header lookup (`ApprovalLineHandler._name_column_index`) resolves to index 3.
- Approval `List1` rows (example): `[정보화지원팀장, 전산주사, 업무담당자, 강동욱]`,
  `[주무관, 전산서기보, 접수, 박형진]` — i.e. the `결재방법` column doubles as the role
  marker (`접수` vs `업무담당자`), and no superior/`결재` row is staged. This is the
  stage-2 signature: `접수` row + handler row present, superior missing.
- 과제카드 ComboBox lives inside the 결재정보 dialog (win32 `과제카드ComboBox`,
  candidate items `[단위]...`), current value empty (`''`) on this stage-2 document —
  so an empty task-card field alone does NOT split stage 2 from stage 3.
- TabControl tab names are not readable via win32 `texts()` (returned `['']`) — use the
  existing uia `dlg["결재선"]` path for tab switching.

## Runtime wiring update (2026-10-07)

- Post-click review state detection reads the dialog body rather than requiring an exact `Static` caption. A known next/exit prompt already visible during the confirmation phase counts as a result; it is not clicked as another approval. The existing continuation loop then handles the next-document prompt. Confirmation/result observation has a 10-second bound and records observed text on failure.
- After a known continuation prompt, `handle_document_flow_dialog()` waits at most `TimeoutConfig.NEXT_DOCUMENT_WAIT` (10 seconds) for prompt disappearance, a nonempty changed raw window title and an enabled main window before returning to the loop. This prevents a previous title from being paired with the next document's role rows while loading. Unknown/approval prompts are not treated as continuation consent. Identical raw-title queue entries stop safely until a live document identifier is verified; review-time title guards remain active.
- User screenshot verifies the post-submit prompt `결재문서를 처리하였습니다. 다음 문서를 처리하겠습니까?` with `예(Y)` / `아니오(N)`. This is a next-document confirmation, not another approval request or a stage-3 row marker. UIA child wrappers are read directly without `exists()`; the review transition detector and existing next/exit loop consume the body text. Actual click verification remains pending.
- `Main._classify_document()` reads paired `결재방법` / `결재자` cells from the verified `List1` through a read-only approval-dialog probe. A failed read or failed dialog close stops processing.
- Before the 2/3 split, a unique nonempty `업무담당자` name is compared with the operator's exact name (`MY_NAME`, then `base_data.json.my_name`, otherwise bounded runtime input). Missing or multiple handlers and unavailable identity stop processing.
- A different handler enters review dispatch (runtime branch 4), bypassing task-card matching and approval-line registration. Only the explicit `검토 완료, 결재` choice clicks the approval button and confirms the exact `결재를 진행하시겠습니까?` prompt. Skip, timeout, changed title, unexpected/missing confirmation or unverified transition stops processing. Success requires a known next/exit result or a changed document without a pending prompt. The loop then handles the next/exit dialog and asks for fresh review consent on each next review document.
- The known receptionist-plus-handler signature enters approval-line reuse/manual capture. After stage-2 configuration, the run ends; document approval remains an operator action. This prevents task-card processing merely because a superior was added.
- Completion-marker strings remain unverified. This update does not finalize the stage-3 discriminator or add a task-card-field reader.

## Unknown-stage guard (2026-10-08)

- Read-only live inspection of the currently open assigned document again found only `업무담당자` and `접수` rows. The configured operator matched the handler; the classifier returns stage 2.
- Regression replay through `Main.run()` reproduced task-card/completion dispatch for own-handler documents with missing receptionist rows or an added superior, despite absent completion evidence.
- `classify_stage()` now returns `None` for unverified signatures. Only an explicit completion flag or supplied verified completion markers selects stage 3. Runtime completion readers remain pending, so unverified own-handler signatures stop.
- This confirms an unsafe fallback; it does not establish which historical run completed the user's document. The live inspection changed only the visible information tab.

## Submitted approval and line-save completion (2026-10-08)

- User-defined submitted signature: a `기안` row plus the operator's `검토` or `결재` row. Live read of `근무상황신청` confirmed the drafter and own-reviewer signature, alongside another approver and an absent approver.
- Runtime checks this signature before requiring an `업무담당자` row. A single named drafter and a single own reviewer/approver role dispatch to existing explicit review consent. Missing/ambiguous roles stop. Consent, title checks, known approval confirmation and result verification remain required.
- Line saving retains the original editor HWND wrapper before its Confirm click, waits for the process-scoped exact `결재선 변경을 완료했습니다.` body, clicks its unique enabled Confirm once and verifies result/editor closure. Unknown result bodies are not confirmed. Only then can the captured line be learned.
- Regression tests reproduce both prior failures. Live approval was not performed; live line-save acknowledgment awaits the next manual save session.

## Final-handler task-card flow (2026-10-08)

- User verified the live `업무담당자` + `업무관리자` + `접수` document had completed its superior approval and returned for final handler processing. Those roles also exist immediately after line registration, so runtime asks a bounded completion-stage confirmation rather than inferring completion from roles alone.
- Final-handler dispatch presents exact/similar DB card recommendations for confirmation and uses the client's complete unit-card chooser for the actual selection. Live controls: document-info task-card selector Button ID 6451, selected-card ComboBox ID 1994. The chooser is embedded web content with no readable card rows in the available UIA tree; manual selection remains required.
- The operator selects and confirms inside `과제카드 선택`, leaves document-info Confirm untouched, then enters Enter in the console within 60 seconds. `TaskCardHandler` reads the actual card field and saves document info; a nonempty card, closed chooser/editor, unchanged document and enabled main window are required before approval.
- Final approval uses the existing known-confirmation/result verifier. Failed completion discards that document's pending card update; successful completion allows the actual title/card mapping to flush to the active vector backend. Exact recommendations may be corrected by the operator.
- Raw titles retain digits for title-change checks and title/card matching. Live end-to-end final completion and DB persistence remain pending; no document was completed during inspection.

## Still open (do not guess — read from live client)

1. Stage-3 `결재방법` marker strings (e.g. what a completed approver row shows) — capture a
   stage-3 dump when such a document is open.
2. Handler identity at runtime — never hardcode names; resolve "me" via config/base data.
3. Whether any stage-2 document ever carries a pre-filled task card (decides if
   task-card-emptiness can stay out of the splitter entirely).
