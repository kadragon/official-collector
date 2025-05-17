
import json
import logging
from openai import OpenAI

from config.config import OPENAI_API_KEY


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

client = OpenAI(api_key=OPENAI_API_KEY)


def card_prompt() -> str:
    system_template = """
   You are a highly skilled classification assistant specializing in document processing.
   Your task is to analyze the provided **official document title** and return the **top 5 most relevant task cards** from the predefined list below.

   ### ⚡️ Instructions:
   - Semantic Analysis: Assess semantic similarity.
   - Selection Limit: Exactly 5 task cards.
   - Ranking: Most relevant first.
   - Strict Selection: Do not invent new cards.
   - Output: Strict JSON schema.

   ### Data Cards:
   {data}
   """
    file_path = './data/docu_data.json'
    with open(file_path, "r", encoding="utf-8") as f:
        docu_data = json.load(f)
    return system_template.format(data=docu_data)


def card_picker(title):
    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[
            {
                "role": "system",
                "content": [{
                    "type": "input_text", "text": card_prompt()
                }]
            },
            {
                "role": "user",
                "content": [{
                        "type": "input_text", "text": title
                }]
            }
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "recommendations",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "recommendations": {
                            "type": "array",
                            "description": "A list of 5 recommendation items.",
                            "items": {
                                "type": "string"
                            }
                        }
                    },
                    "required": [
                        "recommendations"
                    ],
                    "additionalProperties": False
                }
            }
        },
        reasoning={},
        tools=[],
        temperature=0.1,
        max_output_tokens=2048,
        top_p=1,
        store=True
    )

    usage_token(response=response)
    response = json.loads(response.output_text)

    return response['recommendations']


def sort_prompt() -> str:
    system_template = """
    role: Expert document classification and policy update assistant
    objective: Classify official documents based on their titles and update the existing classification system accordingly.
    instructions:
        - Document Title Processing:
            - Extract the core meaning from the document title.
            - Ignore unnecessary elements, such as:
                - Dates (e.g., "2025년").
                - Grammatical markers (e.g., 조사).
            - Use regular expressions where applicable for improved accuracy.
        - Classification:
            - Classify the document using the existing classification system.
            - If the existing system lacks an appropriate category:
                - Use the user-added classification record to determine a suitable category.
        - Policy Update:
            - If a new classification is required:
                - Add it under **Additions**, maintaining the existing classification framework.
            - If an existing classification needs modification:
                - List the outdated category under **Deletions**.
                - Add the new category under **Additions**.
        - Consolidation of Similar Categories:
            - Identify and merge overlapping or similar categories.
            - Use keyword similarity or pattern matching (e.g., regular expressions).
            - List the old categories under **Deletions**.
            - Add the consolidated category under **Additions**, maintaining the framework.
    output_format:
        - JSON object without any surrounding text, explanations, or markdown formatting.
        - Strictly follow the response schema:
        {
            "Classification": {
            "Existing": ["..."],
            "Additions": ["..."],
            "Deletions": ["..."]
            }
        }
    constraints:
        - Maintain accuracy, consistency, and efficiency in classification.
        - Ensure all classification updates adhere to the existing classification framework.

    """

    return system_template.format()


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


def sorter(sort_data, sorted_data, type):
    system_prompt = """
    role: Expert document classification and policy update assistant
    objective: Classify official documents based on their titles and update the existing classification system accordingly.
    instructions:
        - Document Title Processing:
            - Extract the core meaning from the document title.
            - Ignore unnecessary elements, such as:
                - Dates (e.g., "2025년").
                - Grammatical markers (e.g., 조사).
            - Use regular expressions where applicable for improved accuracy.
        - Classification:
            - Classify the document using the existing classification system.
            - If the existing system lacks an appropriate category:
                - Use the user-added classification record to determine a suitable category.
        - Policy Update:
            - If a new classification is required:
                - Add it under **Additions**, maintaining the existing classification framework.
            - If an existing classification needs modification:
                - List the outdated category under **Deletions**.
                - Add the new category under **Additions**.
        - Consolidation of Similar Categories:
            - Identify and merge overlapping or similar categories.
            - Use keyword similarity or pattern matching (e.g., regular expressions).
            - List the old categories under **Deletions**.
            - Add the consolidated category under **Additions**, maintaining the framework.
    output_format:
        - JSON object without any surrounding text, explanations, or markdown formatting.
        - Strictly follow the response schema:
        {
            "Classification": {
            "Existing": ["..."],
            "Additions": ["..."],
            "Deletions": ["..."]
            }
        }
    constraints:
        - Maintain accuracy, consistency, and efficiency in classification.
        - Ensure all classification updates adhere to the existing classification framework.
    """

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
