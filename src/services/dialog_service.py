"""
Dialog Service Compatibility Layer

이 파일은 기존 코드와의 호환성을 위한 래퍼입니다.
새로운 UI 컴포넌트들을 통합하여 기존 DialogHandler 인터페이스를 제공합니다.
"""

from ui.user_interaction import UserInteractionManager
from ui.deletion_menus import DeletionMenuHandler
from typing import Tuple, List, Optional
from utils.input_validator import SelectionResult


class DialogHandler:
    """
    기존 DialogHandler와의 호환성을 위한 래퍼 클래스.
    UserInteractionManager와 DeletionMenuHandler를 통합합니다.
    """

    def __init__(self) -> None:
        """초기화 - 새로운 UI 매니저들을 생성합니다."""
        self.user_interaction = UserInteractionManager()
        self.deletion_menu = DeletionMenuHandler()

    # UserInteractionManager methods
    def select_approval_and_share(self, approval_list: List[str],
                                  share_list: List[str]) -> Tuple[str, str]:
        """담당자와 공람대상자를 선택하도록 요청합니다."""
        return self.user_interaction.select_approval_and_share(approval_list, share_list)

    def confirm_recommendation(self, title: str, recommended_task_title: str) -> bool:
        """추천된 taskTitle을 확인할지 묻습니다."""
        return self.user_interaction.confirm_recommendation(title, recommended_task_title)

    def choose_from_predefined_list(self, title: str, card_list: List[str]) -> Tuple[SelectionResult, Optional[str]]:
        """미리 정의된 목록에서 선택하도록 합니다."""
        return self.user_interaction.choose_from_predefined_list(title, card_list)

    def choose_from_full_list(self, title: str, card_list: List[str]) -> Tuple[SelectionResult, Optional[str]]:
        """전체 목록에서 선택하도록 합니다."""
        return self.user_interaction.choose_from_full_list(title, card_list)

    def choose_from_recommendations(self, title: str, recommendations: List[str]) -> Tuple[SelectionResult, Optional[str]]:
        """추천 목록에서 선택하도록 합니다."""
        return self.user_interaction.choose_from_recommendations(title, recommendations)

    def get_manual_task_card(self, title: str) -> Optional[str]:
        """직접 과제 카드 이름을 입력받습니다."""
        return self.user_interaction.get_manual_task_card(title)

    # DeletionMenuHandler methods
    def show_deletion_menu(self) -> str:
        """삭제 작업 메뉴를 표시합니다."""
        return self.deletion_menu.show_deletion_menu()

    def show_items_for_deletion(self, items: List[Tuple], item_type: str) -> List[int]:
        """삭제할 항목들을 표시하고 선택받습니다."""
        return self.deletion_menu.show_items_for_deletion(items, item_type)

    def get_title_for_deletion(self, item_type: str) -> Optional[str]:
        """삭제할 항목의 제목을 입력받습니다."""
        return self.deletion_menu.get_title_for_deletion(item_type)