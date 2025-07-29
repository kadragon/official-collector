"""
Supabase에 저장된 문서와 과제카드 데이터를 삭제하는 서비스
"""

import os
from typing import List, Tuple
from services.supabase_service import SupabaseService
from services.dialog_service import DialogHandler
from utils.error_handler import setup_logger
from utils.terminal_ui import print_success, print_error


class DeletionService:
    """Supabase 데이터 삭제를 관리하는 서비스"""
    
    def __init__(self):
        self.logger = setup_logger(__name__)
        self.dialog = DialogHandler()
        
        # Supabase 서비스 초기화
        self.task_service = SupabaseService(
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            supabase_url=os.getenv("SUPABASE_URL"),
            supabase_key=os.getenv("SUPABASE_KEY"),
            table_name="documents",
            query_name="match_documents"
        )
        
        self.reception_service = SupabaseService(
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            supabase_url=os.getenv("SUPABASE_URL"),
            supabase_key=os.getenv("SUPABASE_KEY"),
            table_name="reception_documents",
            query_name="match_reception_documents"
        )

    def run_deletion_interface(self):
        """삭제 인터페이스 메인 루프를 실행합니다."""
        while True:
            choice = self.dialog.show_deletion_menu()
            
            if choice == "취소":
                print_success("삭제 작업을 취소했습니다.")
                break
            elif choice == "과제 카드 목록 보기 및 삭제":
                self._handle_task_card_list_deletion()
            elif choice == "접수 문서 목록 보기 및 삭제":
                self._handle_reception_list_deletion()
            elif choice == "개별 과제 카드 삭제":
                self._handle_individual_task_card_deletion()
            elif choice == "개별 접수 문서 삭제":
                self._handle_individual_reception_deletion()
            elif choice == "일괄 삭제":
                self._handle_bulk_deletion()

    def _handle_task_card_list_deletion(self):
        """과제 카드 목록을 보여주고 선택한 항목들을 삭제합니다."""
        cards = self.task_service.list_all_cards()
        selected_indices = self.dialog.show_items_for_deletion(cards, "과제 카드")
        
        if selected_indices:
            titles_to_delete = [cards[i][0] for i in selected_indices]
            deleted_count = self.task_service.bulk_delete_cards(titles_to_delete)
            print_success(f"{deleted_count}개의 과제 카드가 삭제되었습니다.")
        else:
            print_success("삭제 작업이 취소되었습니다.")
        
        input("엔터를 눌러 계속...")

    def _handle_reception_list_deletion(self):
        """접수 문서 목록을 보여주고 선택한 항목들을 삭제합니다."""
        receptions = self.reception_service.list_all_receptions()
        selected_indices = self.dialog.show_items_for_deletion(receptions, "접수 문서")
        
        if selected_indices:
            titles_to_delete = [receptions[i][0] for i in selected_indices]
            deleted_count = self.reception_service.bulk_delete_receptions(titles_to_delete)
            print_success(f"{deleted_count}개의 접수 문서가 삭제되었습니다.")
        else:
            print_success("삭제 작업이 취소되었습니다.")
        
        input("엔터를 눌러 계속...")

    def _handle_individual_task_card_deletion(self):
        """개별 과제 카드를 제목으로 삭제합니다."""
        title = self.dialog.get_title_for_deletion("과제 카드")
        if title:
            # 존재 여부 확인
            if not self.task_service.card_exists(title):
                print_error(f"'{title}' 과제 카드가 존재하지 않습니다.")
                input("엔터를 눌러 메뉴로 돌아가세요...")
                return
            
            # 삭제 실행
            if self.task_service.delete_card_by_title(title):
                print_success(f"'{title}' 과제 카드가 삭제되었습니다.")
            else:
                print_error(f"'{title}' 과제 카드 삭제에 실패했습니다.")
            
            input("엔터를 눌러 계속...")

    def _handle_individual_reception_deletion(self):
        """개별 접수 문서를 제목으로 삭제합니다."""
        title = self.dialog.get_title_for_deletion("접수 문서")
        if title:
            # 존재 여부 확인
            if not self.reception_service.reception_exists(title):
                print_error(f"'{title}' 접수 문서가 존재하지 않습니다.")
                input("엔터를 눌러 메뉴로 돌아가세요...")
                return
            
            # 삭제 실행
            if self.reception_service.delete_reception_by_title(title):
                print_success(f"'{title}' 접수 문서가 삭제되었습니다.")
            else:
                print_error(f"'{title}' 접수 문서 삭제에 실패했습니다.")
            
            input("엔터를 눌러 계속...")

    def _handle_bulk_deletion(self):
        """모든 데이터를 일괄 삭제합니다."""
        from utils.input_validator import confirm_choice
        from utils.terminal_ui import get_styled_input, clear_screen
        
        clear_screen()
        print("\n=== 일괄 삭제 ===")
        print("경고: 이 작업은 모든 저장된 과제 카드와 접수 문서를 삭제합니다.")
        
        if confirm_choice(get_styled_input("정말로 모든 데이터를 삭제하시겠습니까? (y/N): "), default_yes=False):
            if confirm_choice(get_styled_input("최종 확인: 모든 데이터가 영구적으로 삭제됩니다. 진행하시겠습니까? (y/N): "), default_yes=False):
                
                # 모든 과제 카드 삭제
                cards = self.task_service.list_all_cards()
                card_titles = [card[0] for card in cards]
                deleted_cards = self.task_service.bulk_delete_cards(card_titles)
                
                # 모든 접수 문서 삭제
                receptions = self.reception_service.list_all_receptions()
                reception_titles = [reception[0] for reception in receptions]
                deleted_receptions = self.reception_service.bulk_delete_receptions(reception_titles)
                
                print_success(f"총 {deleted_cards}개의 과제 카드와 {deleted_receptions}개의 접수 문서가 삭제되었습니다.")
            else:
                print_success("삭제 작업이 취소되었습니다.")
        else:
            print_success("삭제 작업이 취소되었습니다.")

    def delete_card_by_title(self, title: str) -> bool:
        """외부에서 호출할 수 있는 과제 카드 삭제 메서드"""
        return self.task_service.delete_card_by_title(title)

    def delete_reception_by_title(self, title: str) -> bool:
        """외부에서 호출할 수 있는 접수 문서 삭제 메서드"""
        return self.reception_service.delete_reception_by_title(title)

    def get_all_cards(self) -> List[Tuple[str, str]]:
        """모든 과제 카드 목록을 반환합니다."""
        return self.task_service.list_all_cards()

    def get_all_receptions(self) -> List[Tuple[str, str, str]]:
        """모든 접수 문서 목록을 반환합니다."""
        return self.reception_service.list_all_receptions()