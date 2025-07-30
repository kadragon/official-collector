"""공문 자동 분류 및 처리를 위한 메인 모듈."""

import sys
import time
from typing import List, Dict, Any

from config import config
from services.official_collector import OfficialCollector, DocumentFlowState
from services.dialog_service import DialogHandler
from services.supabase_service import SupabaseService
from services.reception_service import ReceptionService
from services.task_card_service import TaskCardService
from utils.data_loader import load_base_data
from utils.string_processor import is_reception_document, extract_title_from_approval
from utils.error_handler import setup_logger
from utils.terminal_ui import (
    clear_screen,
    draw_header,
    print_document_info,
    print_success,
    print_warning,
    print_info,
    print_final_result
)

logger = setup_logger(__name__)


class Main:
    """공문 자동 분류 및 처리를 위한 메인 클래스."""

    def __init__(self, auto_continue: bool = True):
        self.auto_continue = auto_continue
        base_data = load_base_data()
        self.approval_name_list: List[str] = base_data["reception_list"]
        self.share_name_list: List[str] = base_data["share_list"]

        self.collector = OfficialCollector()
        self.dialog = DialogHandler()

        # Reception을 위한 Supabase 서비스
        reception_supabase_service = SupabaseService(
            openai_api_key=config.openai_api_key,
            supabase_url=config.supabase_url,
            supabase_key=config.supabase_key,
            table_name="reception_documents",
            query_name="match_reception_documents"
        )

        # Task Card를 위한 Supabase 서비스
        task_card_supabase_service = SupabaseService(
            openai_api_key=config.openai_api_key,
            supabase_url=config.supabase_url,
            supabase_key=config.supabase_key,
            table_name="documents",
            query_name="match_documents"
        )

        self.predefined_card_list: List[str] = base_data["card_list"]

        self.reception_service = ReceptionService(
            reception_supabase_service, self.dialog, self.approval_name_list, self.share_name_list
        )
        self.task_card_service = TaskCardService(
            task_card_supabase_service, self.dialog, self.predefined_card_list
        )

    def run(self) -> None:
        """ 메인 로직 """
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
                break
            elif flow_state == DocumentFlowState.CONTINUE:
                if not self.auto_continue:
                    user_choice = input(
                        "\n다음 문서를 처리하시겠습니까? (y/n): ").lower().strip()
                    if user_choice in ['n', 'no', '아니오']:
                        print_info("사용자 요청으로 문서 처리를 종료합니다.")
                        # 대화상자에서 취소 버튼 클릭
                        self.collector.handle_cancel_dialog()
                        break

                if not self.collector.handle_document_flow_dialog(flow_state, self.auto_continue):
                    break
            elif flow_state == DocumentFlowState.UNKNOWN:
                print_warning("알 수 없는 대화상자가 나타났습니다.")

                if not self.auto_continue:
                    # 사용자에게 선택권 제공
                    user_choice = input(
                        "계속 처리하시겠습니까? (y: 계속, n: 종료): ").lower().strip()
                    if user_choice in ['y', 'yes', '예']:
                        print_info("사용자 선택: 다음 문서 처리 계속")
                        self.collector.handle_confirm_dialog()
                        continue
                    else:
                        print_info("사용자 선택: 처리 종료")
                        self.collector.handle_cancel_dialog()
                        break
                else:
                    # 자동 모드에서는 안전하게 종료
                    print_warning("자동 모드에서 알 수 없는 대화상자 - 안전하게 처리를 중단합니다.")
                    self.collector.handle_document_flow_dialog(flow_state)
                    break

            title = self.collector.get_official_title()
            processed_count += 1

            if is_reception_document(title):
                print_document_info(title, "접수 문서")

                approval, shared = self.reception_service.handle_reception(
                    title)

                if approval:
                    self.collector.approval(approval)
                    if shared is not None and shared != '공람없음':
                        self.collector.add_share(str(shared))

                    print_success(f"접수 처리 완료: {approval} / {shared}")
                    logger.info("접수 처리 완료: %s -> %s / %s",
                                title, approval, shared)
                    self.collector.reception()
                    success_count += 1
                    time.sleep(1)
            else:
                # 전자결재 문서 처리
                processed_title = extract_title_from_approval(title)
                print_document_info(processed_title, "전자결재 문서")

                card_name = self.task_card_service.match_task_card(
                    processed_title)

                if card_name:
                    self.collector.document_sort(card_name)
                    print_success(f"문서 분류 완료: {card_name}")
                    logger.info("문서 분류 완료: %s -> %s",
                                processed_title, card_name)
                    success_count += 1
                else:
                    print_warning("과제 카드 매칭 실패로 문서 분류를 건너뜁니다")
                    logger.warning(
                        "과제 카드 매칭 실패로 문서 분류를 건너뜁니다: %s", processed_title)

                time.sleep(2)

        print_final_result(success_count, processed_count)


def run_deletion_interface():
    """삭제 인터페이스를 실행합니다."""
    from services.deletion_service import DeletionService
    deletion_service = DeletionService()
    deletion_service.run_deletion_interface()


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--delete':
        run_deletion_interface()
    elif len(sys.argv) > 1 and sys.argv[1] == '--interactive':
        main = Main(auto_continue=False)
        main.run()
    else:
        main = Main(auto_continue=True)
        main.run()
