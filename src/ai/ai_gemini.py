"""
Google's Gemini AI model (via LLMHandler) to process document classification and sorting.
"""

import logging
from pathlib import Path
from typing import List, Dict, Optional

from src.ai.llm_handler import LLMHandler
# Removed: import json, google.generativeai as genai, content types, prompt constants, config constants

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define PROJECT_ROOT for path resolution, similar to ai_openai.py
# Assuming this file is in src/ai/, so parents[2] should be the project root.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOCU_DATA_PATH = PROJECT_ROOT / "data" / "card_list.txt"

class AIManager:
    """
    Manages document classification and sorting tasks by delegating to LLMHandler.
    """

    def __init__(self) -> None:
        """
        Initializes the AIManager.
        Previously configured Google API key and models, now handled by LLMHandler.
        """
        # LLMHandler will be instantiated on-demand in methods.
        pass

    def resort(self, sort_data: dict, sorted_data: dict, mode: str) -> Optional[dict]:
        """
        Uses LLMHandler to perform document classification and sorting.

        Args:
            sort_data (dict): Original data for classification.
            sorted_data (dict): Manually sorted data.
            mode (str): 'sort' or 'docu'.

        Returns:
            Optional[dict]: The LLM's JSON response as a dictionary, or None on error.
        """
        try:
            handler = LLMHandler()
            # LLMHandler.resort_langchain is expected to return a dict or None
            result = handler.resort_langchain(
                model_type='gemini',
                sort_data=sort_data,
                sorted_data=sorted_data,
                mode=mode
            )
            if result is None:
                logger.error("AIManager.resort: LLMHandler returned None.")
                return {} # Return empty dict as per original error handling
            return result
        except Exception as e:
            logger.error(f"An unexpected error occurred in AIManager.resort: {e}", exc_info=True)
            return {} # Return empty dict on unexpected errors

    def card_picker(self, docu_data: dict, title: str) -> List[str]:
        """
        Uses LLMHandler to get task card recommendations for a document title.
        The 'docu_data' argument from the original method is no longer used to pass
        card list content, as it's now read from file. It's kept for signature
        compatibility if external calls expect it, but it's ignored.

        Args:
            docu_data (dict): This argument is now ignored. Card data is read from file.
            title (str): The document title for which to recommend cards.

        Returns:
            List[str]: A list of recommended card names. Returns empty list on error.
        """
        try:
            handler = LLMHandler()
            
            # Read card_list.txt content
            if not DOCU_DATA_PATH.is_file():
                logger.error(f"Card list file not found at {DOCU_DATA_PATH}")
                return []
            
            with open(DOCU_DATA_PATH, "r", encoding="utf-8") as f:
                card_list_content = "".join(
                    f"- {line.strip()}\n" for line in f if line.strip()
                )

            # LLMHandler.card_picker_langchain is expected to return a list of strings or None
            recommendations = handler.card_picker_langchain(
                model_type='gemini_flash', # As per llm_handler setup for card picking with Gemini
                title=title,
                docu_data_content=card_list_content
            )
            if recommendations is None:
                logger.error("AIManager.card_picker: LLMHandler returned None.")
                return []
            return recommendations
        except FileNotFoundError:
            logger.error(f"Card list file not found at {DOCU_DATA_PATH}. Please ensure it exists.")
            return []
        except Exception as e:
            logger.error(f"An unexpected error occurred in AIManager.card_picker: {e}", exc_info=True)
            return []

# Example usage (for testing, if needed)
if __name__ == '__main__':
    logger.info("Starting AIManager example usage (Gemini through LLMHandler)...")
    ai_manager = AIManager()

    # Note: LLMHandler relies on API keys being available via src.config.config
    # which loads them from .env

    # Example for card_picker
    # The 'docu_data' parameter is ignored by the refactored card_picker
    # Create a dummy card_list.txt if it doesn't exist for testing
    if not DOCU_DATA_PATH.exists():
        DOCU_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(DOCU_DATA_PATH, "w", encoding="utf-8") as f:
            f.write("Sample Card 1\n")
            f.write("Another Card Example\n")
            f.write("Project Alpha Task\n")
        logger.info(f"Created dummy {DOCU_DATA_PATH} for example.")

    # print("\n--- Testing card_picker ---")
    # test_title_card_picker = "기획처 2024년도 주요업무계획 알림"
    # recommended_cards = ai_manager.card_picker(docu_data={}, title=test_title_card_picker)
    # if recommended_cards:
    #     print(f"Recommended cards for '{test_title_card_picker}': {recommended_cards}")
    # else:
    #     print(f"No cards recommended or error for '{test_title_card_picker}'.")

    # Example for resort
    # print("\n--- Testing resort (mode='docu') ---")
    # test_sort_data_docu = {
    #     "unclassified_docs": [
    #         {"title": "2024년 하계 워크숍 준비 계획"},
    #         {"title": "정보 보안 강화 방안 보고"}
    #     ]
    # }
    # test_sorted_data_docu = {
    #     "행사 준비": [{"title": "2023년 동계 워크숍 결과 보고", "document_name": "행사 준비"}],
    #     "정보 보안": []
    # }
    # resort_result_docu = ai_manager.resort(test_sort_data_docu, test_sorted_data_docu, "docu")
    # if resort_result_docu:
    #     print(f"Resort result (docu): {json.dumps(resort_result_docu, ensure_ascii=False, indent=2)}")
    # else:
    #     print("Resort (docu) failed or returned empty.")
    
    logger.info("AIManager example usage finished.")
