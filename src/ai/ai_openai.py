import os
import json
import logging
from pathlib import Path
from typing import Dict

from openai import OpenAI

# from config.config import OPENAI_API_KEY # Removed


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY')) # Use os.getenv directly


# Removed card_picker and related functions as Supabase is now used for recommendations


def sort_prompt() -> str:
    system_template = """
    role: Advanced classification and pattern rule optimizer  
    objective: Automatically classify document titles by semantic patterns, using regular expressions and similarity rules, and update classification logic iteratively with data-driven improvements.

    instructions:
    - Title Preprocessing:
        - Strip titles of:
        - Date-related text (e.g., "2025년", "2024.05.01").
        - Common postfixes/prefixes (e.g., "알림", "안내", "계획", "요청", "공고").
        - Particles or auxiliary markers (e.g., 조사, 관형사).
        - Tokenize titles into normalized keyword sequences.
        - Detect and abstract repeating patterns (e.g., ".*협조 요청$", ".*계획 알림") using regex.

    - Pattern Classification:
        - Match processed title to regex-based classification patterns in the current system.
        - If no match is found:
        - Apply fuzzy matching (title similarity 
 0.85).
        - Generate regex candidates from token clusters and compare to known patterns.
        - Propose candidate pattern(s) and target classification label.
        - Avoid duplicate or overly similar patterns by:
        - Checking for regex subset/superset relations.
        - Using Levenshtein or Jaccard similarity for de-duplication.

    - Pattern Rule Learning:
        - When a new document fails to match existing rules:
        - Suggest a new regex pattern generalized from the unmatched title.
        - Match against manual_sort_data to determine ideal classification.
        - Add new pattern to **Additions**, and flag redundant/overfitted rules under **Deletions**.
        - If multiple titles share similar structure or tokens:
        - Propose a unified regex covering them.
        - Consolidate into one generalized pattern.

    - Rule Optimization & Feedback:
        - Regularly re-evaluate classification accuracy using sort_data vs manual_sort_data.
        - For titles misclassified or unclassified:
        - Generate regex generalizations from manually labeled clusters.
        - Recommend rule updates for better recall and precision.
        - Maintain versioned logs of all rule changes for traceability.

    constraints:
    - Always prioritize reusable, generalized regex patterns over title-specific ones.
    - Avoid hardcoded literal matches unless uniquely necessary.
    - Maintain minimal overlap between regex rules for clarity.
    - New regex proposals must improve coverage **without introducing misclassification**.
    """

    return system_template


def select_format(type):
    if type == 'docu':
        return {
            "type": "json_schema",
            "name": "response_schema",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "additions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["title", "document_name"],
                            "properties": {
                                "document_name": {
                                    "type": "string",
                                    "description": "업무 분류 카드명"
                                },
                                "title": {
                                    "type": "string",
                                    "description": "업무명 (정규 표현식 사용 가능, 숫자 및 불필요한 조사 제거)"
                                }
                            },
                            "additionalProperties": False
                        }
                    },
                    "deletions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["document_name", "title"],
                            "properties": {
                                "document_name": {
                                    "type": "string",
                                    "description": "업무 분류 카드명"
                                },
                                "title": {
                                    "type": "string",
                                    "description": "기존 업무명"
                                }
                            },
                            "additionalProperties": False
                        }
                    }
                },
                "required": ["additions", "deletions"],
                "additionalProperties": False
            }
        }
    elif type == 'sort':
        return {
            "type": "json_schema",
            "name": "response_schema",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "additions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["title", "share", "approval"],
                            "properties": {
                                "title": {
                                    "type": "string",
                                    "description": "업무명 (정규 표현식 사용 가능, 숫자 및 불필요한 조사 제거)"
                                },
                                "share": {
                                    "type": "string",
                                    "description": "공람대상자(원장님제외, 원장님포함, 공람없음, 일반직, 조교, 팀장님, 원장님만)"
                                },
                                "approval": {
                                    "type": "string",
                                    "description": "업무 담당자 구분(기존에 존재하는 담당자 구분만 사용)"
                                }
                            },
                            "additionalProperties": False
                        }
                    },
                    "deletions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["title", "approval"],
                            "properties": {
                                "title": {
                                    "type": "string",
                                    "description": "업무명 (기존 분류체계에 존재하는 업무명)"
                                },
                                "approval": {
                                    "type": "string",
                                    "description": "업무 담당자 구분(기존에 존재하는 담당자 구분만 사용)"
                                }
                            },
                            "additionalProperties": False
                        }
                    }
                },
                "required": ["additions", "deletions"],
                "additionalProperties": False
            }
        }


def sorter(sort_data: Dict, sorted_data: Dict, type: str) -> Dict:
    system_prompt = sort_prompt()

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

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[
            {
                "role": "system",
                "content": [{
                    "type": "input_text", "text": system_prompt
                }]
            },
            {
                "role": "user",
                "content": [{
                        "type": "input_text", "text": user_prompt
                }]
            }
        ],
        text={
            "format": select_format(type)
        },
        reasoning={},
        tools=[],
        temperature=0.1,
        max_output_tokens=2048,
        top_p=1,
        store=True
    )

    usage_token(response=response)

    return json.loads(response.output_text)


def usage_token(response):
    # Pydantic 모델의 .usage 속성으로 사용량 가져오기
    usage = response.usage or {}

    # Pydantic 모델 → dict 변환 (nested Pydantic 모델인 경우)
    if not isinstance(usage, dict):
        usage = usage.dict()

    input_tokens = usage.get('input_tokens', 0)
    output_tokens = usage.get('output_tokens', 0)
    total_tokens = usage.get('total_tokens', 0)
    cached_tokens = usage.get('input_tokens_details',
                              {}).get('cached_tokens', 0)

    # 한 줄 로깅
    logger.info(
        f"Prompt Tokens: {input_tokens}, "
        f"Completion Tokens: {output_tokens}, "
        f"Total Tokens: {total_tokens}, "
        f"Cached Tokens: {cached_tokens}"
    )
