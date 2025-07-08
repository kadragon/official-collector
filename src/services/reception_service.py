"""'접수' 공문 처리 관련 모듈."""

import logging
import re
from typing import List, Tuple, Optional, Dict, Any

from services.dialog_service import DialogHandler

logger = logging.getLogger(__name__)

class ReceptionService:
    """
    '접수' 공문을 처리하는 클래스.
    """
    def __init__(self, sort_data: Dict[str, List], dialog_handler: DialogHandler, approval_name_list: List[str], share_name_list: List[str]):
        self.sort_data = sort_data
        self.dialog = dialog_handler
        self.approval_name_list = approval_name_list
        self.share_name_list = share_name_list

    def _check_sort(self, title: str) -> Optional[Tuple[str, int]]:
        """접수된 공문에 대해서 담당자 매칭 확인"""
        for approval in self.sort_data.keys():
            for item in self.sort_data[approval]:
                if re.match(item['title'], title) or item['title'] in title:
                    logger.info('%s으로 %s가 매칭 되었습니다.', item['title'], title)
                    return approval, item['share']
        return None

    def handle_reception(self, title: str) -> Tuple[Optional[str], Optional[Any]]:
        """
        접수 공문을 처리하고, 담당자와 공람자를 반환합니다.
        """
        approval = shared = None
        processed_title = title.replace("접수: ", '')
        checked = self._check_sort(processed_title)

        if checked is not None:
            approval, shared = checked
            if not self.dialog.check_valid_sort(title, checked):
                approval = None

        if approval is None:
            approval, shared = self.dialog.select_approval_and_share(
                self.approval_name_list, self.share_name_list
            )

        return approval, shared
