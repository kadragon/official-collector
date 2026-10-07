# Document Stages: Reception / Assigned-to-Me / Post-Approval Task Processing

Status: analysis (2026-10-07). No production code changed in this doc.
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

## Current code gap

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

## Still open (do not guess — read from live client)

1. Stage-3 `결재방법` marker strings (e.g. what a completed approver row shows) — capture a
   stage-3 dump when such a document is open.
2. Handler identity at runtime — never hardcode names; resolve "me" via config/base data.
3. Whether any stage-2 document ever carries a pre-filled task card (decides if
   task-card-emptiness can stay out of the splitter entirely).
