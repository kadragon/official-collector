from typing import List, Tuple
import json
import time

from dotenv import load_dotenv

from src.pine import PineconeManager
from src.collector import OfficialCollector
from src.cmdControl import CmdControl
from src.ai import AIManager

load_dotenv()

PINE_API_KEY = "pcsk_6r5C1E_GsC9oZqMebgXTdppVR4CPXYsL2N1FsDS2rsPcFxkaEjiHc1Gb7xszup3JC6tLDz"

# 상수 정의
NO_SHARING_TEXT = "공람없음"

class Main:
    def __init__(self):
        self.command_controller = CmdControl()
        self.collector = OfficialCollector()
        self.pinecone_manager = PineconeManager(api_key=PINE_API_KEY)
        self.ai_manager = AIManager()
        
        self.approval_names: List[str] = self._load_json('approval_names')
        self.share_names: List[str] = self._load_json('share_names')

    @staticmethod
    def _load_json(column: str, filename = './data/base_data.json') -> List[str]:
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data[column]
        except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
            print(f"Error loading {column} from {filename}: {e}")
            return []
    
    def _should_stop_collecting(self) -> bool:
        try:
            if self.collector.dlg.child_window(title='확인', control_type='Window').exists():
                self.collector.dlg['예(Y)'].click()
                return True
            return False
        except:
            return False
    
    def _get_user_input(self) -> Tuple[str, str]:
        self.command_controller.activate()

        print("\n[담당자 선택]")
        for index, name in enumerate(self.approval_names):
            print(f"[{index}] {name}")

        while True:
            try:
                selected_index = int(input("번호를 선택하세요: "))
                if 0 <= selected_index < len(self.approval_names):
                    break
                print("유효하지 않은 번호입니다. 다시 선택해주세요.")
            except ValueError:
                print("숫자를 입력해주세요.")

        approval_name = self.approval_names[selected_index]
        shared_name = NO_SHARING_TEXT

        if selected_index < 2:
            print("\n[공람자 선택]")
            share_options = ' / '.join(f"[{i}] {name}" for i, name in enumerate(self.share_names))
            print(share_options)

            while True:
                try:
                    shared_index = int(input("번호를 선택하세요: "))
                    if 0 <= shared_index < len(self.share_names):
                        shared_name = self.share_names[shared_index]
                        break
                    print("유효하지 않은 번호입니다. 다시 선택해주세요.")
                except ValueError:
                    print("숫자를 입력해주세요.")

        return approval_name, shared_name
    
    def run(self) -> None:
        while True:
            if self._should_stop_collecting():
                break
            
            title = self.collector.get_official_title()
            
            if title.startswith('접수'):
                title = title.replace('접수: ', '')
                
                self.command_controller.activate()
                print(f"find best match: {title}")
                # best_match = self.pinecone_manager.find_best_match_by_scoring(title)
                embedding_title = self.ai_manager.get_embedding(title)
                vector_info = self.pinecone_manager.query(embedding_title)
                result = self.ai_manager.find_match(title, vector_info)
                
                classification = result.classification
                viewing = result.viewing
                reason = result.ReasonForClassification
                
                print(f"\n{reason}\n\n\n{title} -> {classification} / {viewing}\n\n")
                user_confirmation = input("위 정보로 진행하시겠습니까? (Enter / N)")
                
                if user_confirmation.lower() == 'n':
                    classification, viewing = self._get_user_input()

                self.collector.approval(classification)
                if viewing != NO_SHARING_TEXT:
                    self.collector.add_share(viewing)
                    
                print(f"{title} -> {classification} / {viewing}")
                
                self.collector.reception()
                
                if viewing != NO_SHARING_TEXT:
                    self.collector.dlg['확인2'].click()
                
                self.pinecone_manager.upsert_data(title, classification, viewing, embedding_title)
                    
                time.sleep(0.5)
                    

if __name__ == "__main__":
    Main().run()
    
    # main = Main()
    # vector = main.pinecone_manager.query("소프트웨어사업(학생역량통합관리시스템 유지보수) 과업 심의 요청")
    
    # result = main.ai_manager.find_match("인사발령 알림('25.1.15.자, 전입)", vector)
    # print()
    # main.pinecone_manager.upsert_data("인사발령 알림('25.1.15.자, 전입)", "담당_이종선", "원장님+")
