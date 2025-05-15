"""
Google의 Gemini AI 모델을 사용하여 문서 분류 및 정렬을 처리하는 모듈.
"""

import json
import logging
import google.generativeai as genai
from google.ai.generativelanguage_v1beta.types import content
from utils.prompt import RESORTING_PROMPT, CARD_PROMPT
from config.config import GOOGLE_API_KEY, GEMINI_MODELS
from typing import List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AIManager:
    """문서 분류 및 정렬을 담당하는 AIManager 클래스."""

    def __init__(self) -> None:
        """AIManager 초기화: Google API 키를 설정한다."""
        genai.configure(api_key=GOOGLE_API_KEY)
        self.model_flash = None
        self.card_chat = None

    def resort(self, sort_data: dict, sorted_data: dict, mode: str) -> dict:
        """
        Gemini AI 모델을 사용해 문서 분류 및 정렬 결과를 생성한다.

        Args:
            sort_data (dict): 분류할 원본 데이터.
            sorted_data (dict): 수동 정렬 데이터.
            type (str): sort / docu

        Returns:
            dict: Gemini AI 모델의 JSON 응답 결과.
        """
        generation_config = None

        if mode == 'sort':
            generation_config = {
                "temperature": 0.1,
                "response_schema": content.Schema(
                    type=content.Type.OBJECT,
                    enum=[],
                    properties={
                        "additions": content.Schema(
                            type=content.Type.ARRAY,
                            items=content.Schema(
                                type=content.Type.OBJECT,
                                enum=[],
                                required=["title", "share", "approval"],
                                properties={
                                    "title": content.Schema(
                                        type=content.Type.STRING,
                                        description="업무명 (정규 표현식 사용 가능, 숫자 및 불필요한 조사 제거)"
                                    ),
                                    "share": content.Schema(
                                        type=content.Type.STRING,
                                        description="공람대상자(원장님제외, 원장님포함, 공람없음, 일반직, 조교, 팀장님, 원장님만)"
                                    ),
                                    "approval": content.Schema(
                                        type=content.Type.STRING,
                                        description=(
                                            "업무 담당자 구분(기존에 존재하는 담당자 구분만 사용)"
                                        )
                                    )
                                },
                            ),
                        ),
                        "deletions": content.Schema(
                            type=content.Type.ARRAY,
                            items=content.Schema(
                                type=content.Type.OBJECT,
                                enum=[],
                                required=["title", "approval"],
                                properties={
                                    "title": content.Schema(
                                        type=content.Type.STRING,
                                        description="업무명 (기존 분류체계에 존재하는 업무명)"
                                    ),
                                    "approval": content.Schema(
                                        type=content.Type.STRING,
                                        description=(
                                            "업무 담당자 구분(기존에 존재하는 담당자 구분만 사용)"
                                        )
                                    )
                                },
                            ),
                        ),
                    }
                ),
                "response_mime_type": "application/json",
            }
        elif mode == 'docu':
            generation_config = {
                "temperature": 0.1,
                "response_schema": content.Schema(
                    type=content.Type.OBJECT,
                    enum=[],
                    properties={
                        "additions": content.Schema(
                            type=content.Type.ARRAY,
                            items=content.Schema(
                                type=content.Type.OBJECT,
                                enum=[],
                                required=["title", "document_name"],
                                properties={
                                    "document_name": content.Schema(
                                        type=content.Type.STRING,
                                        description="업무 분류 카드명"
                                    ),
                                    "title": content.Schema(
                                        type=content.Type.STRING,
                                        description="업무명 (정규 표현식 사용 가능, 숫자 및 불필요한 조사 제거)"
                                    )
                                },
                            ),
                        ),
                        "deletions": content.Schema(
                            type=content.Type.ARRAY,
                            items=content.Schema(
                                type=content.Type.OBJECT,
                                enum=[],
                                required=["title"],
                                properties={
                                    "document_name": content.Schema(
                                        type=content.Type.STRING,
                                        description="업무 분류 카드명"
                                    ),
                                    "title": content.Schema(
                                        type=content.Type.STRING,
                                        description="업무명 (정규 표현식 사용 가능, 숫자 및 불필요한 조사 제거)"
                                    )
                                },
                            ),
                        ),
                    }
                ),
                "response_mime_type": "application/json",
            }

        model = genai.GenerativeModel(
            model_name=GEMINI_MODELS['pro'],
            generation_config=generation_config,
            system_instruction=RESORTING_PROMPT
        )

        user_prompt = (
            "## sort_data\n"
            "```json\n"
            f"{json.dumps(sort_data, ensure_ascii=False, indent=2)}\n"
            "```\n\n"
            "## manual sort data\n"
            "```json\n"
            f"{json.dumps(sorted_data, ensure_ascii=False, indent=2)}\n"
            "```\n\n"
            "Based on the provided data and the system instructions, generate the required JSON object containing additions and deletions."
            "**Output ONLY the raw JSON object, without any markdown formatting (```json) or other text.**"
        )

        response = model.generate_content(user_prompt)

        raw_text = response.text

        # 마크다운 코드 블록 제거 시도
        if raw_text.strip().startswith("```json"):
            # 첫 줄(```json)과 마지막 줄(```) 제거
            lines = raw_text.strip().splitlines()
            if len(lines) > 1 and lines[-1].strip() == "```":
                json_text = "\n".join(lines[1:-1])
            else:  # 혹시 모를 다른 형식 대비
                json_text = raw_text.strip()[7:].rstrip('`')
        else:
            json_text = raw_text  # 마크다운이 없으면 그대로 사용

        try:
            # 후처리된 텍스트를 JSON으로 파싱
            parsed_response = json.loads(json_text)
            return parsed_response
        except json.JSONDecodeError as e:
            logger.error(
                f"Failed to parse JSON after attempting to clean markdown: {e}")
            logger.error(f"Original text: {raw_text}")
            logger.error(f"Cleaned text: {json_text}")
            # 오류 발생 시 빈 딕셔너리나 다른 적절한 값 반환 고려
            return {}
        except Exception as e:  # 예상치 못한 다른 오류 처리
            print(
                f"An unexpected error occurred during response processing: {e}")
            print(f"Original text: {raw_text}")
            return {}

    def card_picker(self, docu_data: dict, title: str) -> List[str]:
        """
        Gemini AI 모델을 사용해 과제 카드 분류를 추천 받는다
        """

        if self.card_chat is None:
            generation_config = {
                "temperature": 0.1,
                "response_schema": content.Schema(
                    type=content.Type.OBJECT,
                    enum=[],
                    properties={
                        "recommendations": content.Schema(
                            type=content.Type.ARRAY,
                            items=content.Schema(
                                type=content.Type.STRING
                            ),
                        ),
                    }
                ),
                "response_mime_type": "application/json",
            }

            self.model_flash = genai.GenerativeModel(
                model_name=GEMINI_MODELS['flash'], generation_config=generation_config)
            self.card_chat = self.model_flash.start_chat(history=[])
            self.card_chat.send_message(CARD_PROMPT)
            self.card_chat.send_message(
                f"## BASE DATA\n\n{json.dumps(docu_data, ensure_ascii=False, indent=2)}\n\n 이 기준을 참고해서 이후 공문 제목을 분석해줘")

        user_prompt = (
            f"## 공문 제목\n\n`{title}`"
        )

        response = self.card_chat.send_message(user_prompt)

        return json.loads(response.text)['recommendations']
