"""공문 자동 분류 및 처리를 위한 메인 모듈."""

import sys
import time
from typing import List

from config import config
from services.official_service import OfficialCollector, DocumentFlowState
from services.supabase_service import SupabaseService
from services.document_processor import DocumentProcessor
from utils.text_utils import is_reception_document, extract_title_from_approval
from utils.error_handler import setup_logger
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


class Main:
    """공문 자동 분류 및 처리를 위한 메인 클래스."""

    def __init__(self, auto_continue: bool = True):
        self.auto_continue = auto_continue
        # 통합된 설정에서 데이터 로드
        self.approval_name_list: List[str] = config.reception_list
        self.share_name_list: List[str] = config.share_list

        self.collector = OfficialCollector()

        # Supabase 서비스 (통합)
        supabase_service = SupabaseService()

        # 통합된 문서 처리기
        self.document_processor = DocumentProcessor(
            supabase_service=supabase_service,
            approval_name_list=self.approval_name_list,
            share_name_list=self.share_name_list,
            predefined_card_list=config.card_list,
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

            if is_reception_document(title):
                print_document_info(title, "접수 문서")

                approval, shared = self.document_processor.process_reception_document(
                    title
                )

                if approval:
                    self.collector.approval(approval)
                    if shared is not None and shared != "공람없음":
                        self.collector.add_share(str(shared))

                    print_success(f"접수 처리 완료: {approval} / {shared}")
                    logger.info(
                        "접수 처리 완료: %s -> %s / %s", title, approval, shared
                    )
                    self.collector.reception(shared)
                    success_count += 1

                    # 문서 처리 완료 후 잠시 대기하고 화면 정리
                    print_info("문서 처리가 완료되었습니다. 다음 문서를 준비합니다...")
                    time.sleep(2)
                    clear_screen()
            else:
                # 전자결재 문서 처리
                processed_title = extract_title_from_approval(title)
                print_document_info(processed_title, "전자결재 문서")
                logger.info("전자결재 문서 처리 시작: %s", processed_title)

                success = self._process_approval_document(processed_title)
                if success:
                    success_count += 1
                    print_info("문서 분류가 완료되었습니다. 다음 문서를 준비합니다...")
                else:
                    print_info("문서 분류를 건너뛰었습니다. 다음 문서를 준비합니다...")

                # 문서 처리 완료 후 잠시 대기하고 화면 정리
                time.sleep(2)
                clear_screen()

        print_final_result(success_count, processed_count)

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
            print_success("모든 업데이트가 완료되었습니다.")

    def _process_approval_document(self, processed_title: str) -> bool:
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
            # 문서카드 매칭 (3단계 프로세스)
            card_name = self.document_processor.process_task_card_matching(
                processed_title
            )
            logger.info(
                "과제 카드 매칭 결과: %s", card_name if card_name else "매칭 실패"
            )

            if card_name:
                logger.info("과제 카드 매칭 성공 - 문서 분류 시작: %s", card_name)

                # 결재 프로세스 실행 (5단계)
                try:
                    self.collector.document_sort(card_name)
                    print_success(f"문서 분류 완료: {card_name}")
                    logger.info("문서 분류 완료: %s -> %s", processed_title, card_name)
                    return True

                except Exception as e:
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
        # Supabase 서비스 초기화 (통합)
        supabase_service = SupabaseService()
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
    service: SupabaseService, console: ConsoleInterface
) -> None:
    """과제 카드 삭제 처리"""
    try:
        cards = service.list_all_cards()
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
    service: SupabaseService, console: ConsoleInterface
) -> None:
    """접수 문서 삭제 처리"""
    try:
        receptions = service.list_all_receptions()
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
    service: SupabaseService,
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


def _handle_bulk_deletion(service: SupabaseService, console: ConsoleInterface) -> None:
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
