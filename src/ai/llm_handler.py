"""
This module provides a handler for managing and interacting with
Large Language Models (LLMs) using Langchain.

It supports selecting and invoking different models, focusing on
OpenAI's GPT models and Google's Gemini models.
"""

import json
import logging
from typing import Dict, List, Optional, Union

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

from src.config.config import GOOGLE_API_KEY, OPENAI_API_KEY, GEMINI_MODELS

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LLMHandler:
    """
    Manages Langchain LLM instances, allowing for initialization, selection,
    and interaction with different models like OpenAI's GPT and Google's Gemini.
    """

    def __init__(self, openai_model_name="gpt-4.1-mini", gemini_model_name=GEMINI_MODELS['pro']):
        """
        Initializes the LLMHandler with specific OpenAI and Gemini models.

        API keys are loaded from the configuration.
        Initializes Langchain chat model instances for OpenAI and Gemini.

        Args:
            openai_model_name (str): The name of the OpenAI model to use.
            gemini_model_name (str): The name of the Gemini model to use.
        """
        self.openai_api_key = OPENAI_API_KEY
        self.google_api_key = GOOGLE_API_KEY

        if not self.openai_api_key:
            logger.warning("OpenAI API Key is not set. OpenAI models will not be available.")
            self.openai_llm = None
        else:
            self.openai_llm = ChatOpenAI(
                model_name=openai_model_name,
                openai_api_key=self.openai_api_key,
                temperature=0.1 # Default temperature, can be overridden in invoke_llm
            )
            logger.info(f"Initialized OpenAI model: {openai_model_name}")

        if not self.google_api_key:
            logger.warning("Google API Key is not set. Gemini models will not be available.")
            self.gemini_llm = None
        else:
            self.gemini_llm = ChatGoogleGenerativeAI(
                model=gemini_model_name,
                google_api_key=self.google_api_key,
                temperature=0.1 # Default temperature
            )
            logger.info(f"Initialized Gemini model: {gemini_model_name}")
        
        # For card_picker, Gemini often uses a different model (flash)
        # and specific generation_config for JSON output.
        # We can initialize it here or create on-the-fly.
        # For now, let's stick to the main pro model and handle specifics in the method.
        self.gemini_flash_llm_for_card_picker = None
        if self.google_api_key:
             self.gemini_flash_llm_for_card_picker = ChatGoogleGenerativeAI(
                model=GEMINI_MODELS['flash'], # Assuming 'flash' is for card picker
                google_api_key=self.google_api_key,
                temperature=0.1,
                # Gemini's JSON mode is often set in generation_config
                # This will be passed via invoke_kwargs in the card_picker method
            )
             logger.info(f"Initialized Gemini Flash model for card picker: {GEMINI_MODELS['flash']}")


    def get_llm(self, model_type: str) -> Optional[Union[ChatOpenAI, ChatGoogleGenerativeAI]]:
        """
        Retrieves the initialized Langchain LLM instance based on model type.

        Args:
            model_type (str): "openai" or "gemini". 
                               If "gemini_flash" is requested, it returns the flash model.

        Returns:
            Optional[Union[ChatOpenAI, ChatGoogleGenerativeAI]]: The LLM instance or None if not available/invalid type.
        """
        if model_type == "openai":
            if not self.openai_llm:
                logger.error("OpenAI LLM not initialized. Check API key and configuration.")
            return self.openai_llm
        elif model_type == "gemini":
            if not self.gemini_llm:
                logger.error("Gemini LLM not initialized. Check API key and configuration.")
            return self.gemini_llm
        elif model_type == "gemini_flash": # Specific model for card_picker
            if not self.gemini_flash_llm_for_card_picker:
                logger.error("Gemini Flash LLM for card picker not initialized.")
            return self.gemini_flash_llm_for_card_picker
        else:
            logger.error(f"Invalid model type specified: {model_type}. Choose 'openai' or 'gemini'.")
            return None

    def invoke_llm(self, model_type: str, prompt: str, system_message: Optional[str] = None, invoke_kwargs: Optional[Dict] = None) -> Optional[str]:
        """
        Invokes the specified LLM with the given prompt and system message.

        Args:
            model_type (str): "openai" or "gemini".
            prompt (str): The user prompt to send to the LLM.
            system_message (Optional[str]): An optional system message to set context for the LLM.
            invoke_kwargs (Optional[Dict]): Additional keyword arguments for the LLM's invoke method
                                           (e.g., temperature, response_format for OpenAI,
                                           generation_config for Gemini).

        Returns:
            Optional[str]: The content of the LLM's response, or None if an error occurs.
        """
        llm = self.get_llm(model_type)
        if not llm:
            return None

        messages = []
        if system_message:
            messages.append(SystemMessage(content=system_message))
        messages.append(HumanMessage(content=prompt))

        logger.debug(f"Invoking {model_type} LLM with messages: {messages} and invoke_kwargs: {invoke_kwargs}")

        try:
            # Ensure invoke_kwargs is a dict if None
            kwargs_to_pass = invoke_kwargs if invoke_kwargs is not None else {}
            
            response = llm.invoke(messages, **kwargs_to_pass)
            logger.debug(f"LLM Response object: {response}")
            return response.content
        except Exception as e:
            logger.error(f"Error invoking {model_type} LLM: {e}", exc_info=True)
            if hasattr(e, 'response') and e.response: # Log API error response if available
                 logger.error(f"API Error Response: {e.response.text}")
            return None

    def card_picker_langchain(self, model_type: str, title: str, docu_data_content: str) -> List[str]:
        """
        Recommends task cards based on the document title using Langchain.
        Replicates functionality of original card_picker methods.

        Args:
            model_type (str): "openai" or "gemini". Note: For Gemini, this method
                              will use the 'gemini_flash' model specialized for this task.
            title (str): The title of the official document.
            docu_data_content (str): A string containing the list of available task cards,
                                     typically read from 'card_list.txt'.

        Returns:
            List[str]: A list of recommended task card names. Returns empty list on error.
        """
        # System prompt adapted from ai_openai.py's load_card_prompt
        system_prompt_template = """
You are a highly skilled classification assistant specializing in document processing.
Your task is to analyze the provided **official document title** and return the **top 5 most relevant task cards** from the predefined list below.

### ⚡️ Instructions:
- Semantic Analysis: Assess semantic similarity.
- Selection Limit: Exactly 5 task cards.
- Ranking: Most relevant first.
- Strict Selection: Do not invent new cards.
- Output: Strict JSON format with a key "recommendations" containing a list of strings.

### Data Cards:
{data}
"""
        system_message = system_prompt_template.format(data=docu_data_content)
        user_prompt = title
        
        invoke_kwargs = {}
        actual_model_type = model_type

        if model_type == "openai":
            # Langchain's OpenAI integration uses model_kwargs for response_format
            invoke_kwargs['model_kwargs'] = {"response_format": {"type": "json_object"}}
        elif model_type == "gemini":
            actual_model_type = "gemini_flash" # Use the flash model for Gemini card picking
            # For Gemini, JSON output is often controlled by generation_config
            # This schema is simpler: {"recommendations": ["card1", "card2", ...]}
            # Based on ai_gemini.py's card_picker generation_config
            gemini_schema = {
                "type": "object",
                "properties": {
                    "recommendations": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["recommendations"],
            }
            invoke_kwargs['generation_config'] = {
                "response_mime_type": "application/json",
                # Langchain's ChatGoogleGenerativeAI might take 'response_schema' directly here
                # or it might need to be part of a structured output call.
                # Let's try passing it directly as per native client.
                "response_schema": gemini_schema 
            }
        else:
            logger.error(f"Unsupported model_type for card_picker_langchain: {model_type}")
            return []

        raw_response = self.invoke_llm(
            model_type=actual_model_type,
            prompt=user_prompt,
            system_message=system_message,
            invoke_kwargs=invoke_kwargs
        )

        if raw_response:
            try:
                # Gemini might return JSON directly without needing loads if mime_type worked
                if isinstance(raw_response, str): # OpenAI usually returns string
                    data = json.loads(raw_response)
                elif isinstance(raw_response, dict): # Gemini might parse it if schema worked
                    data = raw_response
                else: # Fallback for unexpected response types
                    data = json.loads(str(raw_response))

                recommendations = data.get('recommendations', [])
                if not isinstance(recommendations, list) or not all(isinstance(item, str) for item in recommendations):
                    logger.error(f"Unexpected format for recommendations: {recommendations}. Expected list of strings.")
                    return []
                return recommendations
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode JSON response from LLM for card_picker: {e}")
                logger.error(f"Raw response was: {raw_response}")
                return []
            except Exception as e:
                logger.error(f"An unexpected error occurred during card_picker response processing: {e}")
                logger.error(f"Raw response was: {raw_response}")
                return []
        return []

    def resort_langchain(self, model_type: str, sort_data: dict, sorted_data: dict, mode: str) -> Optional[dict]:
        """
        Reclassifies documents and updates the classification system using Langchain.
        Replicates `resort` from `ai_gemini.py` and `sorter` from `ai_openai.py`.

        Args:
            model_type (str): "openai" or "gemini".
            sort_data (dict): Original data to be classified/sorted.
            sorted_data (dict): Manually sorted/corrected data, providing examples or overrides.
            mode (str): Operation mode, typically "sort" or "docu", which defines the
                        expected JSON output structure.

        Returns:
            Optional[dict]: A dictionary with "additions" and "deletions", or None on error.
        """
        # System prompt adapted from ai_openai.py's sort_prompt
        # This is a generic prompt, specific schema details are handled by model_kwargs/generation_config
        system_message = """
role: Expert document classification and policy update assistant
objective: Classify official documents based on their titles and update the existing classification system accordingly.
instructions:
    - Document Title Processing:
        - Extract the core meaning from the document title.
        - Ignore unnecessary elements, such as dates and grammatical markers.
        - Use regular expressions where applicable for improved accuracy.
    - Classification:
        - Classify the document using the existing classification system.
        - If the existing system lacks an appropriate category, use user-added classification records.
    - Policy Update:
        - If a new classification is required, add it under "Additions".
        - If an existing classification needs modification, list the old under "Deletions" and new under "Additions".
    - Consolidation of Similar Categories:
        - Identify and merge overlapping categories. List old under "Deletions", new under "Additions".
output_format:
    - JSON object without any surrounding text, explanations, or markdown formatting.
    - Strictly follow the response schema provided dynamically for "additions" and "deletions".
constraints:
    - Maintain accuracy, consistency, and efficiency.
    - Ensure updates adhere to the existing classification framework.
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

        invoke_kwargs = {}
        # Schemas adapted from ai_openai.py (select_format) and ai_gemini.py (resort generation_config)
        # These are quite complex, so passing them correctly to Langchain is key.

        common_properties_add_sort = {
            "title": {"type": "string", "description": "업무명 (정규 표현식 사용 가능, 숫자 및 불필요한 조사 제거)"},
            "share": {"type": "string", "description": "공람대상자(원장님제외, 원장님포함, 공람없음, 일반직, 조교, 팀장님, 원장님만)"},
            "approval": {"type": "string", "description": "업무 담당자 구분(기존에 존재하는 담당자 구분만 사용)"}
        }
        common_required_add_sort = ["title", "share", "approval"]

        common_properties_del_sort = {
            "title": {"type": "string", "description": "업무명 (기존 분류체계에 존재하는 업무명)"},
            "approval": {"type": "string", "description": "업무 담당자 구분(기존에 존재하는 담당자 구분만 사용)"}
        }
        common_required_del_sort = ["title", "approval"]
        
        common_properties_add_docu = {
            "document_name": {"type": "string", "description": "업무 분류 카드명"},
            "title": {"type": "string", "description": "업무명 (정규 표현식 사용 가능, 숫자 및 불필요한 조사 제거)"}
        }
        common_required_add_docu = ["title", "document_name"]

        common_properties_del_docu = {
            "document_name": {"type": "string", "description": "업무 분류 카드명"},
            "title": {"type": "string", "description": "업무명 (정규 표현식 사용 가능, 숫자 및 불필요한 조사 제거)"} # ai_gemini had this, openai had "기존 업무명"
        }
        # ai_gemini.py had only "title" as required for deletions in docu mode, ai_openai had "document_name", "title"
        # Taking the more inclusive one from ai_openai for safety
        common_required_del_docu = ["document_name", "title"]


        if mode == 'sort':
            schema = {
                "type": "object",
                "properties": {
                    "additions": {"type": "array", "items": {"type": "object", "required": common_required_add_sort, "properties": common_properties_add_sort, "additionalProperties": False}},
                    "deletions": {"type": "array", "items": {"type": "object", "required": common_required_del_sort, "properties": common_properties_del_sort, "additionalProperties": False}}
                },
                "required": ["additions", "deletions"],
                "additionalProperties": False
            }
        elif mode == 'docu':
            schema = {
                "type": "object",
                "properties": {
                    "additions": {"type": "array", "items": {"type": "object", "required": common_required_add_docu, "properties": common_properties_add_docu, "additionalProperties": False}},
                    "deletions": {"type": "array", "items": {"type": "object", "required": common_required_del_docu, "properties": common_properties_del_docu, "additionalProperties": False}}
                },
                "required": ["additions", "deletions"],
                "additionalProperties": False
            }
        else:
            logger.error(f"Invalid mode '{mode}' for resort_langchain. Must be 'sort' or 'docu'.")
            return None

        if model_type == "openai":
            invoke_kwargs['model_kwargs'] = {
                "response_format": {
                    "type": "json_schema", # Use json_schema for complex objects
                    "json_schema": schema # Pass the schema directly
                }
            }
            # OpenAI's "json_schema" type expects the schema itself under "json_schema" key.
            # The "name" field used in the original ai_openai.py client.responses.create is not standard for ChatCompletion's response_format.
        elif model_type == "gemini":
            invoke_kwargs['generation_config'] = {
                "response_mime_type": "application/json",
                "response_schema": schema # Pass the schema for Gemini
            }
        else:
            logger.error(f"Unsupported model_type for resort_langchain: {model_type}")
            return None

        raw_response = self.invoke_llm(
            model_type=model_type, # Use the main gemini model, not flash
            prompt=user_prompt,
            system_message=system_message,
            invoke_kwargs=invoke_kwargs
        )

        if raw_response:
            try:
                # As with card_picker, attempt to parse based on expected model behavior
                if isinstance(raw_response, str):
                    data = json.loads(raw_response)
                elif isinstance(raw_response, dict): 
                    data = raw_response 
                else:
                    data = json.loads(str(raw_response))
                
                # Basic validation of top-level keys
                if not isinstance(data, dict) or "additions" not in data or "deletions" not in data:
                    logger.error(f"LLM response for resort_langchain does not contain 'additions'/'deletions' keys. Got: {data}")
                    return None
                return data
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode JSON response from LLM for resort_langchain: {e}")
                logger.error(f"Raw response was: {raw_response}")
                return None
            except Exception as e:
                logger.error(f"An unexpected error occurred during resort_langchain response processing: {e}")
                logger.error(f"Raw response was: {raw_response}")
                return None
        return None

if __name__ == '__main__':
    # Example Usage (requires API keys to be set in .env and loaded by config.py)
    # Ensure src.config.config can be imported from this path or adjust PYTHONPATH
    
    # To run this, you'd typically do:
    # 1. Make sure .env has GOOGLE_API_KEY and OPENAI_API_KEY
    # 2. python -m src.ai.llm_handler 
    # (if your project root is added to PYTHONPATH or you are in the root)

    logger.info("LLMHandler module loaded. Example usage below (commented out).")

    # handler = LLMHandler()

    # # Test get_llm
    # # print("Testing get_llm...")
    # # openai_model = handler.get_llm("openai")
    # # gemini_model = handler.get_llm("gemini")
    # # print(f"OpenAI Model: {openai_model}")
    # # print(f"Gemini Model: {gemini_model}")

    # # Test invoke_llm (simple prompt)
    # # print("\nTesting invoke_llm with OpenAI...")
    # # if openai_model:
    # #     response_openai = handler.invoke_llm("openai", "Hello, what is the weather like today?")
    # #     print(f"OpenAI Response: {response_openai}")
    
    # # print("\nTesting invoke_llm with Gemini...")
    # # if gemini_model:
    # #     response_gemini = handler.invoke_llm("gemini", "Hello, tell me a fun fact about space.")
    # #     print(f"Gemini Response: {response_gemini}")

    # # Test card_picker_langchain
    # # print("\nTesting card_picker_langchain with OpenAI...")
    # # dummy_card_list_content = "- Card A\n- Card B\n- Important Project Card\n- Financial Task\n- General Inquiry"
    # # if openai_model:
    # #     recs_openai = handler.card_picker_langchain("openai", "Request for new project budget", dummy_card_list_content)
    # #     print(f"OpenAI Card Recommendations: {recs_openai}")

    # # print("\nTesting card_picker_langchain with Gemini...")
    # # if handler.get_llm("gemini_flash"): # Check if flash model is available for card picking
    # #     recs_gemini = handler.card_picker_langchain("gemini", "Request for new project budget", dummy_card_list_content)
    # #     print(f"Gemini Card Recommendations: {recs_gemini}")
    
    # # Test resort_langchain
    # # print("\nTesting resort_langchain with OpenAI (mode='docu')...")
    # # dummy_sort_data_docu = {"unclassified_docs": [{"title": "Urgent: Security Protocol Update"}, {"title": "Minutes from Q2 Planning Meeting"}]}
    # # dummy_sorted_data_docu = {"Security Documents": ["Old Security Memo"], "Meeting Notes": []}
    # # if openai_model:
    # #     resort_openai_docu = handler.resort_langchain("openai", dummy_sort_data_docu, dummy_sorted_data_docu, "docu")
    # #     print(f"OpenAI Resort (docu) Response: {json.dumps(resort_openai_docu, ensure_ascii=False, indent=2)}")

    # # print("\nTesting resort_langchain with Gemini (mode='sort')...")
    # # dummy_sort_data_sort = {"new_tasks": [{"title": "Submit expense report for July", "assigned_to": "John Doe"}, {"title": "Onboard new intern Sarah"}]}
    # # dummy_sorted_data_sort = {"Finance Tasks": [{"title": "Expense Report Q2", "share": "Team Leads", "approval": "Finance Dept"}], "HR Tasks": []}
    # # if gemini_model:
    # #     resort_gemini_sort = handler.resort_langchain("gemini", dummy_sort_data_sort, dummy_sorted_data_sort, "sort")
    # #     print(f"Gemini Resort (sort) Response: {json.dumps(resort_gemini_sort, ensure_ascii=False, indent=2)}")
    
    # pass # End of example usage block
