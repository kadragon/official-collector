import time
import re
import logging
from typing import List, Tuple, Optional, Dict, Any

from src.collector import OfficialCollector
from src.json_handler import load_json, update_sort_data
from src.dialog_handler import DialogHandler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Main:
    def __init__(self):
        self.sort_data: Dict[str, List] = load_json("./data/sort_data.json")
        self.sorted_data: List[Dict] = []
        self.docu_data: Dict[str, Any] = load_json("./data/docu_data.json")
        self.docued_data: Dict = {}
        self.approval_name_list: List[str] = load_json('./data/base_data.json')['approval_names']
        self.share_name_list: List[str] = load_json('./data/base_data.json')['share_names']

        self.collector = OfficialCollector()
        self.dialog = DialogHandler()

    def _check_sort(self, title: str) -> Optional[Tuple[str, int]]:
        """접수된 공문에 대해서 담당자 매칭 확인"""
        for item in self.sort_data['items']:
            if re.match(item['title'], title) or item['title'] in title:
                logger.info(
                    '%s으로 %s가 매칭 되었습니다.',
                    item['title'],
                    title
                )
                return item['approval'], item['share']

        return None

    def _check_docu(self, title: str) -> str:
        """결재 완료된 공문에 대해서 과제 카드 매칭 확인"""
        for card_name, docu_titles in self.docu_data.items():
            for docu_title in docu_titles:
                if docu_title in title or re.match(docu_title, title):
                    return card_name

        return None

    def run(self) -> None:
        """ 메인 로직 """
        while True:
            if self.collector.check_end_collecting():
                break

            approval = shared = None

            title = self.collector.get_official_title()

            if title.startswith('접수'):
                checked = self._check_sort(title.replace("접수: ", ''))

                if checked is not None:
                    approval, shared = checked

                if approval is None:
                    approval, shared = self.dialog.select_approval_and_share(
                        self.approval_name_list, self.share_name_list
                    )

                    self.sorted_data.append({
                        "title": title.replace("접수: ", ''),
                        "approval": approval,
                        "shared": shared
                    })

                self.collector.approval(approval)
                if shared != '공람없음':
                    self.collector.add_share(shared)

                print(
                    f"{title} -> {approval} / {shared}")

                self.collector.reception()

                if shared != '공람없음':
                    self.collector.dlg['확인2'].click()

                time.sleep(0.5)
            else:
                card_name = self._check_docu(title)

                if card_name is None:
                    card_name = self.dialog.choose_task_card(self.docu_data)

                    self.docued_data[title] = {
                        "title": title,
                        "card_name": card_name
                    }

                self.collector.document_sort(card_name)


        if len(self.sorted_data) > 0:
            print("분류 기준을 갱신합니다.")
            update_sort_data(self.sort_data, self.sorted_data)

        print("완료되었습니다.")


if __name__ == '__main__':
    main = Main()
    main.run()
    # main.update_sort_data()
    # print()
