import time
import json
import re
from typing import List, Tuple, Optional, Dict, Any

from src.collector import OfficialCollector
from src.cmdControl import CmdControl


class Main:
    def __init__(self):
        self.sort_data: Dict[str, Any] = self._load_data(
            "./data/sort_data.json")
        self.sorted_data: Dict[str, Any] = self._load_data(
            "./data/sorted_data.json")
        self.docu_data: Dict[str, Any] = self._load_data(
            "./data/docu_data.json")
        self.docued_data: Dict[str, Any] = self._load_data(
            "./data/docued_data.json")
        self.approval_name_list: List[str] = self._load_json('approval_names')
        self.share_name_list: List[str] = self._load_json('share_names')

        self.collector = OfficialCollector()
        self.cmd = CmdControl()

    @staticmethod
    def _load_json(column: str) -> List[str]:
        try:
            with open('./data/base_data.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data[column]
        except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
            print(f"Error loading {column} from base_data.json: {e}")
            return []

    def _load_data(self, file_path: str) -> Dict[str, Any]:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"File {file_path} not found. Creating an empty dictionary.")
            return {}
        except json.JSONDecodeError:
            print(
                f"File {file_path} is not valid JSON. Creating an empty dictionary.")
            return {}

    def _save_data(self) -> None:
        with open("./data/sorted_data.json", "w", encoding="utf-8") as f:
            json.dump(self.sorted_data, f, indent=4, ensure_ascii=False)
        with open("./data/docued_data.json", "w", encoding="utf-8") as f:
            json.dump(self.docued_data, f, indent=4, ensure_ascii=False)

    def _check_sort(self, title: str) -> Optional[Tuple[str, int]]:
        for user, data in self.sort_data.items():
            for task in data['tasks']:
                if isinstance(task, list):
                    check_str, shared = task
                else:
                    check_str, shared = task, 2

                if check_str in title or re.match(check_str, title):
                    return user, shared
        return None

    def _check_docu(self, title: str) -> str:
        for card_name, docu_titles in self.docu_data.items():
            for docu_title in docu_titles:
                if docu_title in title or re.match(docu_title, title):
                    return card_name

        return None

    def _select_card_name(self) -> str:
        self.cmd.activate()

        i = 0
        card_list = list(self.docu_data.keys())
        for card_name in card_list:
            print(f'[{i:02d}] {card_name}')
            i += 1

        while True:
            try:
                idx = int(input("과제카드를 선택해주세요: "))
                if 0 <= idx < len(card_list):
                    break
                print("유효하지 않은 번호입니다. 다시 선택해주세요.")
            except ValueError:
                print("숫자를 입력해주세요.")

        return card_list[idx]

    def _check_end_collecting(self) -> bool:
        if self.collector.dlg.child_window(title='확인', control_type='Window').exists():
            self.collector.dlg['예(Y)'].click()
            return True
        return False

    def _get_user_input(self) -> Tuple[str, int]:
        self.cmd.activate()

        print("\n[담당자 선택]")
        for i, approval_name in enumerate(self.approval_name_list):
            print(f"[{i}] {approval_name}")

        while True:
            try:
                tmp = int(input("번호를 선택하세요: "))
                if 0 <= tmp < len(self.approval_name_list):
                    break
                print("유효하지 않은 번호입니다. 다시 선택해주세요.")
            except ValueError:
                print("숫자를 입력해주세요.")

        approval = self.approval_name_list[tmp]
        shared = 2

        if tmp < 2:
            print("\n[공람자 선택]")
            share_text = ' / '.join(f"[{i}] {name}" for i,
                                    name in enumerate(self.share_name_list))
            print(share_text)

            while True:
                try:
                    shared = int(input("번호를 선택하세요: "))
                    if 0 <= shared < len(self.share_name_list):
                        break
                    print("유효하지 않은 번호입니다. 다시 선택해주세요.")
                except ValueError:
                    print("숫자를 입력해주세요.")

        return approval, shared

    def run(self) -> None:
        while True:
            if self._check_end_collecting():
                break

            title = self.collector.get_official_title()

            if title.startswith('접수'):
                checked = self._check_sort(title)

                if checked is not None:
                    approval, shared = checked
                else:
                    approval, shared = self._get_user_input()

                    self.sorted_data[title] = {
                        "title": title,
                        "approval": approval,
                        "shared": shared
                    }

                self.collector.approval(approval)
                if shared != 2:
                    self.collector.add_share(self.share_name_list[shared])

                print(
                    f"{title} -> {approval} / {self.share_name_list[shared]}")

                # if approval.split('_')[0] != '담당':
                #     self.collector.save_pc()

                self.collector.reception()

                if shared != 2:
                    self.collector.dlg['확인2'].click()

                time.sleep(0.5)
            else:
                """결재 완료된 공문에 대해서 과제 카드 부여"""
                print(title)
                card_name = self._check_docu(title)

                if card_name is None:
                    card_name = self._select_card_name()

                    self.docued_data[title] = {
                        "title": title,
                        "card_name": card_name
                    }

                self.collector.document_sort(card_name)

        self._save_data()
        print("완료되었습니다.")


if __name__ == '__main__':
    main = Main()
    main.run()
