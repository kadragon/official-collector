"""
OpenAI's GPT models (via LLMHandler) to process document classification and sorting.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional

# import json # No longer needed for json.loads if LLMHandler returns dict/list
# from openai import OpenAI # No longer needed
# from config.config import OPENAI_API_KEY # No longer needed here

from src.ai.llm_handler import LLMHandler

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# client = OpenAI(api_key=OPENAI_API_KEY) # Removed, LLMHandler handles client

# Define PROJECT_ROOT for path resolution
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOCU_DATA_PATH = PROJECT_ROOT / "data" / "card_list.txt"

def get_card_list_content() -> Optional[str]:
    """
    Reads the content of data/card_list.txt.
    This replaces the formatting part of the original load_card_prompt.
    """
    if not DOCU_DATA_PATH.is_file():
        logger.error(f"Card list file not found at {DOCU_DATA_PATH}")
        return None
    try:
        with open(DOCU_DATA_PATH, "r", encoding="utf-8") as f:
            # LLMHandler's card_picker_langchain expects a string of card names
            # The original formatting was "- card_name\n".
            # The new llm_handler.py card_picker_langchain's prompt template is:
            # "### Data Cards:\n{data}"
            # So, we should provide the {data} part.
            # Let's stick to the same format as before for consistency.
            docu_data_content = "".join(
                f"- {line.strip()}\n" for line in f if line.strip()
            )
        return docu_data_content
    except Exception as e:
        logger.error(f"Error reading card list file {DOCU_DATA_PATH}: {e}")
        return None

# CARD_PROMPT = load_card_prompt() # Removed, prompt construction is in LLMHandler

def card_picker(title: str) -> List[str]:
    """
    Uses LLMHandler to get task card recommendations for a document title.
    """
    try:
        handler = LLMHandler()
        card_list_content = get_card_list_content()
        if card_list_content is None:
            return [] # Error already logged by get_card_list_content

        recommendations = handler.card_picker_langchain(
            model_type='openai',
            title=title,
            docu_data_content=card_list_content
        )
        
        # usage_token(response=response) # Commented out as usage_token is removed

        if recommendations is None:
            logger.error("card_picker: LLMHandler returned None.")
            return []
        return recommendations # Expected to be List[str]
    except Exception as e:
        logger.error(f"An unexpected error occurred in card_picker: {e}", exc_info=True)
        return []

# def sort_prompt() -> str: # Removed, prompt construction is in LLMHandler
#     ...

# def select_format(type): # Removed, schema construction is in LLMHandler
#     ...

def sorter(sort_data: Dict, sorted_data: Dict, type: str) -> Optional[Dict]:
    """
    Uses LLMHandler to perform document classification and sorting.
    'type' argument is passed as 'mode' to LLMHandler.
    """
    try:
        handler = LLMHandler()
        result = handler.resort_langchain(
            model_type='openai',
            sort_data=sort_data,
            sorted_data=sorted_data,
            mode=type # Original argument name is 'type'
        )
        
        # usage_token(response=response) # Commented out

        if result is None:
            logger.error("sorter: LLMHandler returned None.")
            # Original sorter would attempt json.loads on the response,
            # if LLMHandler returns None, we should probably return an empty dict or None
            # based on how calling code handles it. The original code would error out
            # if response.output_text was None. Returning {} to match ai_gemini's error handling.
            return {} 
        return result # Expected to be Dict
    except Exception as e:
        logger.error(f"An unexpected error occurred in sorter: {e}", exc_info=True)
        return {}


# def usage_token(response): # Commented out as per instructions
#     # Pydantic 모델의 .usage 속성으로 사용량 가져오기
#     usage = response.usage or {}

#     # Pydantic 모델 → dict 변환 (nested Pydantic 모델인 경우)
#     if not isinstance(usage, dict):
#         usage = usage.dict()

#     input_tokens = usage.get('input_tokens', 0)
#     output_tokens = usage.get('output_tokens', 0)
#     total_tokens = usage.get('total_tokens', 0)
#     cached_tokens = usage.get('input_tokens_details',
#                               {}).get('cached_tokens', 0)

#     # 한 줄 로깅
#     logger.info(
#         f"Prompt Tokens: {input_tokens}, "
#         f"Completion Tokens: {output_tokens}, "
#         f"Total Tokens: {total_tokens}, "
#         f"Cached Tokens: {cached_tokens}"
#     )

# Example usage (for testing, if needed)
if __name__ == '__main__':
    logger.info("Starting AI OpenAI (via LLMHandler) example usage...")

    # Note: LLMHandler relies on API keys being available via src.config.config
    # which loads them from .env

    # Ensure dummy card_list.txt exists for card_picker testing
    if not DOCU_DATA_PATH.exists():
        DOCU_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(DOCU_DATA_PATH, "w", encoding="utf-8") as f:
            f.write("Sample Card OpenAI 1\n")
            f.write("Another OpenAI Card Example\n")
            f.write("Project Beta Task (OpenAI)\n")
        logger.info(f"Created dummy {DOCU_DATA_PATH} for example.")

    # print("\n--- Testing card_picker (OpenAI) ---")
    # test_title_openai_card_picker = "기획처 2025년도 예산안 편성 지침 안내"
    # recommended_cards_openai = card_picker(title=test_title_openai_card_picker)
    # if recommended_cards_openai:
    #     print(f"Recommended cards for '{test_title_openai_card_picker}': {recommended_cards_openai}")
    # else:
    #     print(f"No cards recommended or error for '{test_title_openai_card_picker}'.")

    # print("\n--- Testing sorter (OpenAI, mode='sort') ---")
    # test_sort_data_openai = {
    #     "new_tasks": [
    #         {"title": "월간 보고서 제출 요청 (7월)", "assigned_to": "김민지"},
    #         {"title": "신규 직원 교육 프로그램 개발"}
    #     ]
    # }
    # test_sorted_data_openai = {
    #     "보고 업무": [{"title": "주간 업무 현황 보고", "share": "팀장", "approval": "부서장"}],
    #     "인사 업무": []
    # }
    # resort_result_openai_sort = sorter(test_sort_data_openai, test_sorted_data_openai, "sort")
    # if resort_result_openai_sort:
    #     # Ensure json is imported if you uncomment this for direct execution and want to print
    #     # import json
    #     # print(f"Sorter result (OpenAI, sort): {json.dumps(resort_result_openai_sort, ensure_ascii=False, indent=2)}")
    #     print(f"Sorter result (OpenAI, sort): {resort_result_openai_sort}") # Prints dict directly
    # else:
    #     print("Sorter (OpenAI, sort) failed or returned empty.")
    
    logger.info("AI OpenAI (via LLMHandler) example usage finished.")
