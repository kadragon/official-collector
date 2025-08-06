"""
Deletion Menu Handlers

삭제 작업 관련 사용자 인터페이스를 제공합니다.
삭제 메뉴, 항목 선택, 확인 대화상자 등을 담당합니다.
"""

from .terminal_ui import (
    clear_screen,
    print_selection_menu,
    get_styled_input
)
from utils.input_validator import (
    get_valid_selection,
    confirm_choice
)
from typing import List, Tuple, Optional
from services.command_service import CommandExecutor
from utils.error_handler import setup_logger

logger = setup_logger(__name__)


class DeletionMenuHandler:
    """삭제 작업 관련 메뉴를 담당하는 클래스."""

    def __init__(self) -> None:
        """초기화 및 CMD 창 활성화."""
        self.cmd = CommandExecutor()

    def show_deletion_menu(self) -> str:
        """
        삭제 작업 메뉴를 표시하고 사용자 선택을 받습니다.
        """
        self.cmd.activate()
        clear_screen()

        options = [
            "과제 카드 목록 보기 및 삭제",
            "접수 문서 목록 보기 및 삭제",
            "개별 과제 카드 삭제",
            "개별 접수 문서 삭제",
            "일괄 삭제",
            "취소"
        ]

        print_selection_menu("삭제 작업 선택", options)

        while True:
            try:
                user_input = get_styled_input("번호를 선택하세요: ")
                choice = get_valid_selection(user_input, options)
                return choice
            except ValueError as e:
                print(str(e))

    def show_items_for_deletion(self, items: List[Tuple], item_type: str) -> List[int]:
        """
        삭제할 항목들을 표시하고 사용자가 선택하도록 합니다.

        Args:
            items: 삭제 가능한 항목들의 목록 (title, 추가정보...)
            item_type: "과제 카드" 또는 "접수 문서"

        Returns:
            선택된 항목들의 인덱스 목록
        """
        self.cmd.activate()
        clear_screen()

        if not items:
            logger.info(f"삭제 가능한 {item_type}이 없습니다.")
            print(f"삭제 가능한 {item_type}이 없습니다.")
            input("엔터를 눌러 계속...")
            return []

        logger.info(f"저장된 {item_type} 목록 표시 ({len(items)}개)")

        print(f"\n=== 저장된 {item_type} 목록 ===")
        for i, item in enumerate(items, 1):
            if item_type == "과제 카드":
                if len(item) >= 3:
                    title, task_title, registered_at = item[0], item[1], item[2]
                    logger.debug(
                        f"항목 {i}: {title} -> {task_title} [등록: {registered_at}]")
                    print(
                        f"{i}. {title} -> {task_title} [등록: {registered_at}]")
                else:
                    title, task_title = item[0], item[1]
                    logger.debug(f"항목 {i}: {title} -> {task_title}")
                    print(f"{i}. {title} -> {task_title}")
            else:  # 접수 문서
                if len(item) >= 4:
                    title, approval, share, registered_at = item[0], item[1], item[2], item[3]
                    logger.debug(
                        f"항목 {i}: {title} (담당: {approval}, 공람: {share}) [등록: {registered_at}]")
                    print(
                        f"{i}. {title} (담당: {approval}, 공람: {share}) [등록: {registered_at}]")
                else:
                    title, approval, share = item[0], item[1], item[2]
                    logger.debug(
                        f"항목 {i}: {title} (담당: {approval}, 공람: {share})")
                    print(f"{i}. {title} (담당: {approval}, 공람: {share})")

        print("\n삭제할 항목 번호를 입력하세요 (여러 개는 쉼표로 구분, 전체 삭제는 'all', 취소는 'q'):")
        user_input = get_styled_input("선택: ").strip()

        if user_input.lower() == 'q':
            return []
        elif user_input.lower() == 'all':
            if confirm_choice(f"모든 {item_type}을 삭제하시겠습니까?", default_yes=False):
                return list(range(len(items)))
            else:
                return []
        else:
            try:
                indices = []
                for num_str in user_input.split(','):
                    num = int(num_str.strip()) - 1  # 0-based index
                    if 0 <= num < len(items):
                        indices.append(num)
                    else:
                        logger.warning(f"잘못된 번호 입력: {num_str.strip()}")
                        print(f"잘못된 번호: {num_str.strip()}")

                if indices and confirm_choice(f"선택한 {len(indices)}개 항목을 삭제하시겠습니까?", default_yes=False):
                    logger.info(f"{len(indices)}개 항목 삭제 확인됨")
                    return indices
                else:
                    return []
            except ValueError:
                logger.warning("사용자가 올바르지 않은 숫자 입력")
                print("올바른 숫자를 입력해주세요.")
                input("엔터를 눌러 계속...")
                return []

    def get_title_for_deletion(self, item_type: str) -> Optional[str]:
        """
        삭제할 항목의 제목을 직접 입력받습니다.
        """
        self.cmd.activate()
        clear_screen()

        logger.info(f"{item_type} 개별 삭제 시작")

        print(f"\n=== {item_type} 개별 삭제 ===")
        title = get_styled_input(f"삭제할 {item_type}의 제목을 입력하세요: ").strip()

        if title and confirm_choice(f"'{title}' {item_type}을/를 삭제하시겠습니까?", default_yes=False):
            logger.info(f"{item_type} 삭제 확인: {title}")
            return title
        return None