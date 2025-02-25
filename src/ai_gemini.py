"""
Google의 Gemini AI 모델을 사용하여 문서 분류 및 정렬을 처리하는 모듈.
"""

import json
import google.generativeai as genai
from google.ai.generativelanguage_v1beta.types import content
from src.prompt import RESORTING_PROMPT
from src.config import GOOGLE_API_KEY, GEMINI_MODELS


class AIManager:
    """문서 분류 및 정렬을 담당하는 AIManager 클래스."""

    def __init__(self) -> None:
        """AIManager 초기화: Google API 키를 설정한다."""
        genai.configure(api_key=GOOGLE_API_KEY)

    def resort(self, sort_data: dict, sorted_data: dict) -> dict:
        """
        Gemini AI 모델을 사용해 문서 분류 및 정렬 결과를 생성한다.

        Args:
            sort_data (dict): 분류할 원본 데이터.
            sorted_data (dict): 수동 정렬 데이터.

        Returns:
            dict: Gemini AI 모델의 JSON 응답 결과.
        """
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
                            required=["title"],
                            properties={
                                "title": content.Schema(
                                    type=content.Type.STRING,
                                    description="업무명 (기존 분류체계에 존재하는 업무명)"
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
            "```"
        )

        response = model.generate_content(user_prompt)
        return json.loads(response.text)
