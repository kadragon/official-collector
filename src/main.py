"""공문 자동 분류 및 처리를 위한 메인 모듈."""

# Trace: backlog.md - Task-card selection and confirmation fast pass

import itertools
import sys
from typing import List, Union, Optional, cast
from rich import traceback

# Enable rich tracebacks globally for better error display
traceback.install(show_locals=True, width=120, theme="monokai")

from config import config, TimeoutConfig
from services.official_service import OfficialCollector, DocumentFlowState
from services.supabase_service import SupabaseService
from services.openai_embedding_service import OpenAIEmbeddingService
from services.local_embedding_service import LocalEmbeddingService
from services.local_vector_service import LocalVectorService
from services.document_processor import DocumentProcessor
from services.task_card_handler import TaskCardHandler
from utils.text_utils import classify_stage, extract_title_from_approval
from utils.wait_helpers import wait_for_document_turnaround
from utils.timed_input import choose_timed_option, get_timed_text_input
from utils.error_handler import setup_logger, handle_pywinauto_error
from utils.audit_logger import init_audit_logger
from utils.monitoring_hooks import init_monitoring_hooks
from utils.quota_manager import init_quota_manager
from ui.console_interface import (
    ConsoleInterface,
    draw_header,
    print_document_info,
    print_success,
    print_warning,
    print_info,
    print_error,
    print_final_result,
    activate_cmd_window,
    clear_screen,
)

logger = setup_logger(__name__)

# Initialize deployment readiness systems (TASK-002)
audit_logger = init_audit_logger(log_to_file=True)
monitoring_hooks = init_monitoring_hooks(
    performance_threshold_ms=5000.0,
    error_rate_threshold=0.1,
    consecutive_failure_threshold=3,
)
quota_manager = init_quota_manager(enable_enforcement=True)

logger.info("Deployment readiness systems initialized")
logger.info("- Audit logging: enabled (./logs/audit/)")
logger.info("- Monitoring hooks: enabled")
logger.info("- Quota management: enabled")


class Main:
    """공문 자동 분류 및 처리를 위한 메인 클래스."""

    def __init__(self, auto_continue: bool = True):
        self.auto_continue = auto_continue
        # 통합된 설정에서 데이터 로드
        self.approval_name_list: List[str] = config.reception_list
        self.share_name_list: List[str] = config.share_list

        self.task_card_handler = TaskCardHandler()
        self.collector = OfficialCollector(
            task_card_capture=self.task_card_handler.capture_requested
        )
        self.reception_department = ""

        # 서비스 생성 (의존성 주입 패턴, VECTOR_BACKEND에 따라 백엔드 선택)
        # supabase_service에는 SupabaseService 또는 LocalVectorService가 담긴다
        if config.get_vector_backend() == "local":
            approval_store: LocalVectorService = LocalVectorService(
                LocalEmbeddingService()
            )
            supabase_service: Union[SupabaseService, LocalVectorService] = (
                approval_store
            )
        else:
            supabase_service = SupabaseService(OpenAIEmbeddingService())
            # Keep approval vectors in the local model's space, never cloud dimensions.
            approval_store = LocalVectorService(LocalEmbeddingService())

        # 통합된 문서 처리기
        self.document_processor = DocumentProcessor(
            supabase_service=supabase_service,
            approval_name_list=self.approval_name_list,
            share_name_list=self.share_name_list,
            predefined_card_list=config.card_list,
            approval_store=approval_store,
            reception_member_provider=self._get_reception_members,
        )

    def run(self) -> None:
        """메인 로직"""
        clear_screen()
        draw_header("공문 자동 분류 시스템")
        print_info("문서 처리를 시작합니다...")

        processed_count = 0
        success_count = 0

        while True:
            flow_state = self.collector.check_document_flow_state()

            if flow_state == DocumentFlowState.EXIT:
                print_info("문서 처리를 종료합니다.")
                self.collector.handle_document_flow_dialog(flow_state)
                # 종료 전 대기 중인 업데이트 모두 처리
                self._flush_all_pending_updates()
                break
            elif flow_state == DocumentFlowState.CONTINUE:
                if not self.auto_continue:
                    activate_cmd_window()
                    user_choice = (
                        input("\n다음 문서를 처리하시겠습니까? (y/n): ").lower().strip()
                    )
                    if user_choice in ["n", "no", "아니오"]:
                        print_info("사용자 요청으로 문서 처리를 종료합니다.")
                        # 대화상자에서 취소 버튼 클릭
                        self.collector.handle_cancel_dialog()
                        # 종료 전 대기 중인 업데이트 모두 처리
                        self._flush_all_pending_updates()
                        break

                if not self.collector.handle_document_flow_dialog(
                    flow_state, self.auto_continue
                ):
                    # 종료 전 대기 중인 업데이트 모두 처리
                    self._flush_all_pending_updates()
                    break
            elif flow_state == DocumentFlowState.UNKNOWN:
                print_warning("알 수 없는 대화상자가 나타났습니다.")

                if not self.auto_continue:
                    # 사용자에게 선택권 제공
                    activate_cmd_window()
                    user_choice = (
                        input("계속 처리하시겠습니까? (y: 계속, n: 종료): ")
                        .lower()
                        .strip()
                    )
                    if user_choice in ["y", "yes", "예"]:
                        print_info("사용자 선택: 다음 문서 처리 계속")
                        self.collector.handle_confirm_dialog()
                        continue
                    else:
                        print_info("사용자 선택: 처리 종료")
                        self.collector.handle_cancel_dialog()
                        # 종료 전 대기 중인 업데이트 모두 처리
                        self._flush_all_pending_updates()
                        break
                else:
                    # 자동 모드에서는 안전하게 종료
                    print_warning(
                        "자동 모드에서 알 수 없는 대화상자 - 안전하게 처리를 중단합니다."
                    )
                    self.collector.handle_document_flow_dialog(flow_state)
                    # 종료 전 대기 중인 업데이트 모두 처리
                    self._flush_all_pending_updates()
                    break

            title = self.collector.get_official_title()
            processed_count += 1

            stage = self._classify_document(title)
            if stage is None:
                print_warning("문서 단계를 읽지 못해 처리를 중단합니다")
                self._flush_all_pending_updates()
                break

            if not self._is_current_document(title):
                self._flush_all_pending_updates()
                break

            if stage == 1:
                if self._handle_reception_document(title):
                    success_count += 1
                    wait_for_document_turnaround()
                    clear_screen()
                else:
                    print_warning("접수 완료를 확인하지 못해 처리를 중단합니다")
                    self._flush_all_pending_updates()
                    break
            elif stage == 2:
                if self._handle_assigned_document(title):
                    success_count += 1
                # Stage-3 completion markers remain unverified. Do not reclassify
                # the same document after merely adding a superior's row.
                self._flush_all_pending_updates()
                break
            elif stage == 4:
                if self._handle_review_document(title):
                    success_count += 1
                    wait_for_document_turnaround()
                    clear_screen()
                else:
                    self._flush_all_pending_updates()
                    break
            else:
                # 전자결재 문서 처리
                processed_title = extract_title_from_approval(title)
                print_document_info(processed_title, "전자결재 문서")
                logger.info("전자결재 문서 처리 시작: %s", processed_title)

                success = self._process_approval_document(processed_title, title)
                if success:
                    success_count += 1
                    print_info("문서 분류가 완료되었습니다. 다음 문서를 준비합니다...")
                else:
                    print_warning("완결을 확인하지 못해 처리를 중단합니다")
                    self._flush_all_pending_updates()
                    break

                # 문서 처리 완료 후 잠시 대기하고 화면 정리
                wait_for_document_turnaround()
                clear_screen()

        print_final_result(success_count, processed_count)

    @handle_pywinauto_error(
        "Reception document application", logger, default_return=False
    )
    def _handle_reception_document(self, title: str) -> bool:
        """Apply the chosen handler and retain memory only after reception succeeds."""
        # Stored names resolve organization-wide; only manual picks constrain department.
        self.reception_department = ""
        print_document_info(title, "접수 문서")
        approval, shared = self.document_processor.process_reception_document(title)
        if not approval:
            return False
        completed = False
        try:
            if not self.collector.apply_approval_names(
                [approval], self.reception_department
            ):
                logger.warning("Reception approval-line application failed: %s", title)
                return False
            if shared is not None and shared != "공람없음":
                self.collector.add_share(str(shared))
            if not self.collector.reception(shared):
                return False
            completed = True
            print_success(f"접수 처리 완료: {approval} / {shared}")
            logger.info("Reception completed: %s -> %s / %s", title, approval, shared)
            return True
        finally:
            if not completed:
                self.document_processor.discard_reception_update(title)

    def _is_current_document(self, title: str) -> bool:
        """Keep mutations bound to the title captured before classification."""
        current = self.collector.get_official_title()
        if current != title:
            logger.warning("Document changed: expected=%s, current=%s", title, current)
            print_warning("문서가 바뀌어 처리를 중단합니다")
            return False
        return True

    def _classify_document(self, title: str) -> Optional[int]:
        """Check handler identity before routing any electronic document to task cards."""
        if classify_stage(title) == 1:
            return 1
        members = self.collector.read_approval_role_members()
        if members is None:
            logger.warning("Document stage probe failed: %s", title)
            return None
        identity = getattr(self, "operator_name", "") or config.my_name
        if not identity:
            activate_cmd_window()
            identity = get_timed_text_input(
                "본인 이름 입력 (결재선에 표시된 이름, 빈 입력: 중단)",
                timeout=TimeoutConfig.USER_SELECTION_WAIT,
            )
        if not identity or not identity.strip():
            logger.warning("Operator identity unavailable; document processing stopped")
            return None
        self.operator_name = identity.strip()
        drafters = [name for role, name in members if role == "기안"]
        if drafters:
            own_roles = [role for role, name in members if name == self.operator_name]
            if (
                len(drafters) != 1
                or not drafters[0]
                or own_roles not in (["검토"], ["결재"])
            ):
                logger.warning(
                    "Submitted document reviewer unavailable or ambiguous: %s", title
                )
                return None
            self.review_handler_name = drafters[0]
            self.review_role_label = "기안자"
            return 4
        handlers = [name for role, name in members if role == "업무담당자"]
        if len(handlers) != 1 or not handlers[0]:
            logger.warning("Document handler unavailable or ambiguous: %s", title)
            return None
        if handlers[0] != self.operator_name:
            self.review_handler_name = handlers[0]
            self.review_role_label = "업무담당자"
            return 4
        roles = [role for role, _ in members]
        if (
            "업무관리자" in roles
            and "접수" in roles
            and all(role in ("접수", "업무담당자", "업무관리자") for role in roles)
        ):
            answer = choose_timed_option(
                "상위 결재 완료 여부 확인",
                ["결재 대기 또는 불명확: 중단", "결재 완료 후 최종 업무처리"],
            )
            return 3 if answer == "결재 완료 후 최종 업무처리" else None
        return classify_stage(title, role_markers=[role for role, _ in members])

    def _handle_review_document(self, title: str) -> bool:
        """Require an explicit review decision; never classify or change this line."""
        print_document_info(extract_title_from_approval(title), "검토 후 결재")
        print_info(
            f"{getattr(self, 'review_role_label', '업무담당자')}: {self.review_handler_name}. "
            "문서를 검토한 후 결재하시겠습니까?"
        )
        answer = choose_timed_option("검토 후 결재", ["건너뛰기", "검토 완료, 결재"])
        if answer != "검토 완료, 결재":
            print_info("결재 없이 처리를 마칩니다")
            return False
        current_title = self.collector.get_official_title()
        if current_title != title:
            logger.warning(
                "Reviewed document changed before approval button click: expected=%s, current=%s",
                title,
                current_title,
            )
            print_warning("문서가 바뀌어 결재하지 않습니다")
            return False
        completed = self.collector.approve_reviewed_document(title)
        if completed:
            print_success("검토한 문서 결재 처리 완료. 다음 문서를 준비합니다")
        else:
            print_warning("결재 완료를 확인하지 못해 처리를 중단합니다")
        return bool(completed)

    def _get_reception_members(self) -> List[str]:
        """Provide org-chart members and retain the selected department for application."""
        department, members = self.collector.get_reception_members(config.my_department)
        self.reception_department = department
        return cast(List[str], members)

    def _handle_assigned_document(self, title: str) -> bool:
        """Reuse or capture a line for stage 2, leaving document approval to the operator."""
        processed_title = extract_title_from_approval(title)
        print_document_info(processed_title, "배정 문서")
        result = self.document_processor.process_assigned_document(
            processed_title,
            self.collector.apply_approval_names,
            self.collector.capture_approval_line,
        )
        if result:
            print_success("결재선 지정 완료. 문서 결재는 화면에서 진행하세요")
        else:
            print_warning("결재선 지정 없이 배정 문서 처리를 마칩니다")
        return bool(result)

    def _flush_all_pending_updates(self) -> None:
        """대기 중인 모든 업데이트를 Supabase에 일괄 업로드"""
        reception_count, card_count = (
            self.document_processor.get_pending_updates_count()
        )

        if reception_count > 0 or card_count > 0:
            print_info(
                f"대기 중인 업데이트를 처리합니다... (접수: {reception_count}개, 카드: {card_count}개)"
            )
            self.document_processor.flush_pending_updates()
            remaining_receptions, remaining_cards = (
                self.document_processor.get_pending_updates_count()
            )
            if remaining_receptions or remaining_cards:
                print_warning("저장 실패 항목을 유지합니다. 재시도가 필요합니다.")
            else:
                print_success("모든 업데이트가 완료되었습니다.")

    def _process_approval_document(
        self, processed_title: str, original_title: str
    ) -> bool:
        """
        전자결재 문서를 처리합니다.

        1순위: 동일한 문서명이 있다면 바로 처리
        2순위: 임베딩을 통해서 유사한 문서명을 추천하여 사용자가 선택
        3순위: 2순위에서 사용자가 목록에 없음을 선택하면 문서카드 목록 전체를 A->Z 순서로 정리해서 보여줌

        Args:
            processed_title: 전자결재에서 추출된 문서 제목

        Returns:
            bool: 처리 성공 여부
        """
        try:
            if not self._is_current_document(original_title):
                return False

            def capture_card(suggestion: Optional[str]) -> Optional[str]:
                if not self._is_current_document(original_title):
                    return None
                return cast(
                    Optional[str],
                    self.task_card_handler.capture(self.collector, suggestion),
                )

            # 문서카드 매칭 (3단계 프로세스)
            card_name = self.document_processor.process_task_card_matching(
                processed_title,
                manual_selection=capture_card,
            )
            logger.info(
                "과제 카드 매칭 결과: %s", card_name if card_name else "매칭 실패"
            )

            if card_name:
                logger.info("과제 카드 매칭 성공 - 문서 분류 시작: %s", card_name)

                # 결재 프로세스 실행 (5단계)
                try:
                    if not self.collector.approve_reviewed_document(original_title):
                        self.document_processor.discard_card_update(processed_title)
                        return False
                    print_success(f"문서 분류 완료: {card_name}")
                    logger.info("문서 분류 완료: %s -> %s", processed_title, card_name)
                    return True

                except Exception as e:
                    self.document_processor.discard_card_update(processed_title)
                    logger.error("문서 분류 실행 중 오류 발생: %s", e)
                    print_warning(f"문서 분류 실행 중 오류 발생: {e}")
                    return False
            else:
                print_warning("과제 카드 매칭 실패로 문서 분류를 건너뜁니다")
                logger.warning(
                    "과제 카드 매칭 실패로 문서 분류를 건너뜁니다: %s", processed_title
                )
                return False

        except Exception as e:
            self.document_processor.discard_card_update(processed_title)
            logger.error("전자결재 문서 처리 중 예상치 못한 오류: %s", e)
            print_warning(f"전자결재 문서 처리 중 오류 발생: {e}")
            return False


# ────────────────────────────────────────────────────────────────────────────
# 삭제 모듈 (기존 deletion_service.py에서 통합)
# ────────────────────────────────────────────────────────────────────────────


def run_deletion_interface() -> None:
    """간소화된 삭제 인터페이스를 실행합니다."""
    from ui.console_interface import (
        ConsoleInterface,
        print_success,
        print_error,
    )

    try:
        # 서비스 초기화 (의존성 주입 패턴, VECTOR_BACKEND에 따라 백엔드 선택)
        if config.get_vector_backend() == "local":
            supabase_service: Union[SupabaseService, LocalVectorService] = (
                LocalVectorService(LocalEmbeddingService())
            )
        else:
            supabase_service = SupabaseService(OpenAIEmbeddingService())
    except Exception as e:
        print_error(f"Supabase 서비스 초기화 실패: {e}")
        print_error("삭제 기능을 사용하려면 Supabase 환경변수가 필요합니다.")
        return

    console = ConsoleInterface()

    while True:
        choice = console.show_deletion_menu()

        if choice == "취소":
            print_success("삭제 작업을 취소했습니다.")
            break
        elif choice == "과제 카드 목록 보기 및 삭제":
            _handle_task_card_deletion(supabase_service, console)
        elif choice == "접수 문서 목록 보기 및 삭제":
            _handle_reception_deletion(supabase_service, console)
        elif choice == "개별 과제 카드 삭제":
            _handle_individual_deletion(supabase_service, console, "과제 카드", "card")
        elif choice == "개별 접수 문서 삭제":
            _handle_individual_deletion(
                supabase_service, console, "접수 문서", "reception"
            )
        elif choice == "일괄 삭제":
            _handle_bulk_deletion(supabase_service, console)


def _handle_task_card_deletion(
    service: Union[SupabaseService, LocalVectorService],
    console: ConsoleInterface,
) -> None:
    """과제 카드 삭제 처리"""
    try:
        cards = list(itertools.islice(service.iter_all_cards(), 10_000))
        selected_indices = console.show_items_for_deletion(cards, "과제 카드")

        if selected_indices:
            titles_to_delete = [cards[i][0] for i in selected_indices]
            deleted_count = service.bulk_delete_cards(titles_to_delete)
            print_success(f"{deleted_count}개의 과제 카드가 삭제되었습니다.")
        else:
            print_success("삭제 작업이 취소되었습니다.")

    except Exception as e:
        print_error(f"삭제 처리 중 오류 발생: {e}")

    input("엔터를 눌러 계속...")


def _handle_reception_deletion(
    service: Union[SupabaseService, LocalVectorService],
    console: ConsoleInterface,
) -> None:
    """접수 문서 삭제 처리"""
    try:
        receptions = list(itertools.islice(service.iter_all_receptions(), 10_000))
        selected_indices = console.show_items_for_deletion(receptions, "접수 문서")

        if selected_indices:
            titles_to_delete = [receptions[i][0] for i in selected_indices]
            deleted_count = service.bulk_delete_receptions(titles_to_delete)
            print_success(f"{deleted_count}개의 접수 문서가 삭제되었습니다.")
        else:
            print_success("삭제 작업이 취소되었습니다.")

    except Exception as e:
        print_error(f"삭제 처리 중 오류 발생: {e}")

    input("엔터를 눌러 계속...")


def _handle_individual_deletion(
    service: Union[SupabaseService, LocalVectorService],
    console: ConsoleInterface,
    item_type: str,
    service_type: str,
) -> None:
    """개별 항목 삭제 처리"""
    try:
        title = console.get_title_for_deletion(item_type)
        if not title:
            return

        # 존재 여부 확인 및 삭제
        if service_type == "card":
            exists = service.card_exists(title)
            success = service.delete_card_by_title(title) if exists else False
        else:  # reception
            exists = service.reception_exists(title)
            success = service.delete_reception_by_title(title) if exists else False

        if not exists:
            print_error(f"'{title}' {item_type}가 존재하지 않습니다.")
        elif success:
            print_success(f"'{title}' {item_type}가 삭제되었습니다.")
        else:
            print_error(f"'{title}' {item_type} 삭제에 실패했습니다.")

    except Exception as e:
        print_error(f"개별 삭제 중 오류 발생: {e}")

    input("엔터를 눌러 계속...")


def _handle_bulk_deletion(
    service: Union[SupabaseService, LocalVectorService],
    console: ConsoleInterface,
) -> None:
    """일괄 삭제 처리"""
    try:
        if console.confirm_bulk_deletion():
            task_count = service.delete_all_cards()
            reception_count = service.delete_all_receptions()
            print_success(
                f"모든 데이터가 삭제되었습니다. (과제 카드: {task_count}, 접수 문서: {reception_count})"
            )
        else:
            print_success("일괄 삭제가 취소되었습니다.")
    except Exception as e:
        print_error(f"일괄 삭제 중 오류 발생: {e}")

    input("엔터를 눌러 계속...")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--delete":
        run_deletion_interface()
    elif len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        main = Main(auto_continue=False)
        main.run()
    else:
        main = Main(auto_continue=True)
        main.run()
