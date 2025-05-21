import unittest
from unittest.mock import patch, MagicMock, call
import json

from src.ai.llm_handler import LLMHandler
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

# Attempt to import API keys; tests should mock calls so these won't be used for actual API interaction.
# This is to ensure the LLMHandler can be instantiated if it directly tries to read them at __init__
try:
    from src.config.config import GOOGLE_API_KEY, OPENAI_API_KEY, GEMINI_MODELS
except ImportError:
    # Define them as None if not found, so LLMHandler can still be imported and tested with mocks
    GOOGLE_API_KEY = "test_google_api_key" # Mocked, so value doesn't matter too much
    OPENAI_API_KEY = "test_openai_api_key" # Mocked
    GEMINI_MODELS = {'pro': 'gemini-pro-mock', 'flash': 'gemini-flash-mock'}


@patch('src.ai.llm_handler.OPENAI_API_KEY', OPENAI_API_KEY)
@patch('src.ai.llm_handler.GOOGLE_API_KEY', GOOGLE_API_KEY)
@patch('src.ai.llm_handler.GEMINI_MODELS', GEMINI_MODELS)
@patch('langchain_google_genai.ChatGoogleGenerativeAI')
@patch('langchain_openai.ChatOpenAI')
class TestLLMHandler(unittest.TestCase):

    def setUp(self):
        # Sample mock responses
        self.mock_card_picker_response_content = {"recommendations": ["card1", "card2", "card3", "card4", "card5"]}
        self.mock_resort_response_content_sort = {
            "additions": [{"title": "new task", "share": "team", "approval": "manager"}],
            "deletions": [{"title": "old task", "approval": "manager"}]
        }
        self.mock_resort_response_content_docu = {
            "additions": [{"document_name": "doc_cat_A", "title": "new doc title"}],
            "deletions": [{"document_name": "doc_cat_B", "title": "old doc title"}]
        }
        # It's good practice to clear mocks for each test if they are instance attributes
        # For class-level mocks (decorators on the class), they are reset for each method.

    def test_initialization(self, MockChatOpenAI, MockChatGoogleGenerativeAI, MockGoogleAPI, MockOpenAIAPI, MockGeminiModels):
        """Test LLMHandler initialization and LLM client instantiation."""
        handler = LLMHandler()

        MockChatOpenAI.assert_called_once_with(
            model_name="gpt-4.1-mini", # or the default specified in LLMHandler
            openai_api_key=OPENAI_API_KEY,
            temperature=0.1
        )
        # Check calls for both Gemini models (pro and flash)
        self.assertEqual(MockChatGoogleGenerativeAI.call_count, 2)
        MockChatGoogleGenerativeAI.assert_any_call(
            model=GEMINI_MODELS['pro'],
            google_api_key=GOOGLE_API_KEY,
            temperature=0.1
        )
        MockChatGoogleGenerativeAI.assert_any_call(
            model=GEMINI_MODELS['flash'],
            google_api_key=GOOGLE_API_KEY,
            temperature=0.1
        )

        self.assertIsInstance(handler.openai_llm, MockChatOpenAI)
        self.assertIsInstance(handler.gemini_llm, MockChatGoogleGenerativeAI)
        self.assertIsInstance(handler.gemini_flash_llm_for_card_picker, MockChatGoogleGenerativeAI)

    def test_get_llm(self, MockChatOpenAI, MockChatGoogleGenerativeAI, MockGoogleAPI, MockOpenAIAPI, MockGeminiModels):
        """Test retrieval of LLM instances."""
        handler = LLMHandler()
        self.assertIs(handler.get_llm('openai'), handler.openai_llm)
        self.assertIs(handler.get_llm('gemini'), handler.gemini_llm)
        self.assertIs(handler.get_llm('gemini_flash'), handler.gemini_flash_llm_for_card_picker)
        
        # Test invalid model type
        with self.assertLogs(logger='src.ai.llm_handler', level='ERROR') as cm:
            self.assertIsNone(handler.get_llm('invalid_type'))
        self.assertIn("Invalid model type specified: invalid_type", cm.output[0])


    def test_invoke_llm_openai(self, MockChatOpenAI, MockChatGoogleGenerativeAI, MockGoogleAPI, MockOpenAIAPI, MockGeminiModels):
        """Test invoking OpenAI LLM."""
        handler = LLMHandler()
        mock_openai_instance = MockChatOpenAI.return_value
        mock_response = MagicMock()
        mock_response.content = "OpenAI response"
        mock_openai_instance.invoke.return_value = mock_response

        result = handler.invoke_llm('openai', 'test prompt', system_message='system prompt', invoke_kwargs={'temperature': 0.5})

        mock_openai_instance.invoke.assert_called_once()
        args, kwargs = mock_openai_instance.invoke.call_args
        self.assertIsInstance(args[0][0], SystemMessage)
        self.assertEqual(args[0][0].content, 'system prompt')
        self.assertIsInstance(args[0][1], HumanMessage)
        self.assertEqual(args[0][1].content, 'test prompt')
        self.assertEqual(kwargs['temperature'], 0.5)
        self.assertEqual(result, "OpenAI response")

    def test_invoke_llm_gemini(self, MockChatOpenAI, MockChatGoogleGenerativeAI, MockGoogleAPI, MockOpenAIAPI, MockGeminiModels):
        """Test invoking Gemini LLM."""
        handler = LLMHandler()
        # Assuming the first instance created is 'pro', then 'flash'
        # We need to ensure we are mocking the correct Gemini instance
        mock_gemini_pro_instance = handler.gemini_llm # This is already a mock from the class decorator
        mock_response = MagicMock()
        mock_response.content = "Gemini response"
        mock_gemini_pro_instance.invoke.return_value = mock_response

        result = handler.invoke_llm('gemini', 'test prompt gemini', system_message='system prompt gemini', invoke_kwargs={'top_k': 3})
        
        mock_gemini_pro_instance.invoke.assert_called_once()
        args, kwargs = mock_gemini_pro_instance.invoke.call_args
        self.assertIsInstance(args[0][0], SystemMessage)
        self.assertEqual(args[0][0].content, 'system prompt gemini')
        self.assertIsInstance(args[0][1], HumanMessage)
        self.assertEqual(args[0][1].content, 'test prompt gemini')
        self.assertEqual(kwargs['top_k'], 3) # Example specific kwarg for Gemini
        self.assertEqual(result, "Gemini response")

    def test_card_picker_langchain_openai(self, MockChatOpenAI, MockChatGoogleGenerativeAI, MockGoogleAPI, MockOpenAIAPI, MockGeminiModels):
        """Test card_picker_langchain with OpenAI."""
        handler = LLMHandler()
        mock_openai_instance = handler.openai_llm
        mock_response_obj = MagicMock()
        mock_response_obj.content = json.dumps(self.mock_card_picker_response_content)
        mock_openai_instance.invoke.return_value = mock_response_obj

        recommendations = handler.card_picker_langchain('openai', 'test title', 'docu content')
        
        self.assertEqual(recommendations, self.mock_card_picker_response_content['recommendations'])
        mock_openai_instance.invoke.assert_called_once()
        args, kwargs = mock_openai_instance.invoke.call_args
        self.assertIsInstance(args[0][0], SystemMessage) # System prompt for card picker
        self.assertIn("### Data Cards:\ndocu content", args[0][0].content)
        self.assertIsInstance(args[0][1], HumanMessage)
        self.assertEqual(args[0][1].content, 'test title')
        self.assertEqual(kwargs['model_kwargs'], {"response_format": {"type": "json_object"}})


    def test_card_picker_langchain_gemini_flash(self, MockChatOpenAI, MockChatGoogleGenerativeAI, MockGoogleAPI, MockOpenAIAPI, MockGeminiModels):
        """Test card_picker_langchain with Gemini Flash."""
        handler = LLMHandler()
        mock_gemini_flash_instance = handler.gemini_flash_llm_for_card_picker
        mock_response_obj = MagicMock()
        # Gemini might return a dict directly if schema is effective, or string for manual parse.
        # LLMHandler's card_picker tries json.loads if it's a string.
        mock_response_obj.content = json.dumps(self.mock_card_picker_response_content)
        mock_gemini_flash_instance.invoke.return_value = mock_response_obj

        recommendations = handler.card_picker_langchain('gemini', 'test title gemini', 'docu content gemini')
        
        self.assertEqual(recommendations, self.mock_card_picker_response_content['recommendations'])
        mock_gemini_flash_instance.invoke.assert_called_once()
        args, kwargs = mock_gemini_flash_instance.invoke.call_args
        self.assertIsInstance(args[0][0], SystemMessage)
        self.assertIn("### Data Cards:\ndocu content gemini", args[0][0].content)
        self.assertIsInstance(args[0][1], HumanMessage)
        self.assertEqual(args[0][1].content, 'test title gemini')
        
        expected_gemini_invoke_kwargs = {
            'generation_config': {
                "response_mime_type": "application/json",
                "response_schema": {
                    "type": "object",
                    "properties": {"recommendations": {"type": "array", "items": {"type": "string"}}},
                    "required": ["recommendations"],
                }
            }
        }
        self.assertEqual(kwargs, expected_gemini_invoke_kwargs)

    def test_resort_langchain_openai_sort_mode(self, MockChatOpenAI, MockChatGoogleGenerativeAI, MockGoogleAPI, MockOpenAIAPI, MockGeminiModels):
        """Test resort_langchain with OpenAI in 'sort' mode."""
        handler = LLMHandler()
        mock_openai_instance = handler.openai_llm
        mock_response_obj = MagicMock()
        mock_response_obj.content = json.dumps(self.mock_resort_response_content_sort)
        mock_openai_instance.invoke.return_value = mock_response_obj

        sort_data_sample = {"new_tasks": [{"title": "task1"}]}
        sorted_data_sample = {"done_tasks": [{"title": "task0"}]}
        result = handler.resort_langchain('openai', sort_data_sample, sorted_data_sample, 'sort')

        self.assertEqual(result, self.mock_resort_response_content_sort)
        mock_openai_instance.invoke.assert_called_once()
        args, kwargs = mock_openai_instance.invoke.call_args
        self.assertIsInstance(args[0][0], SystemMessage) # System prompt for resort
        self.assertIsInstance(args[0][1], HumanMessage) # User prompt with sort_data and sorted_data
        self.assertIn(json.dumps(sort_data_sample, ensure_ascii=False, indent=2), args[0][1].content)
        self.assertIn(json.dumps(sorted_data_sample, ensure_ascii=False, indent=2), args[0][1].content)
        
        # Check that the complex schema was passed in model_kwargs
        self.assertIn('model_kwargs', kwargs)
        self.assertIn('response_format', kwargs['model_kwargs'])
        self.assertEqual(kwargs['model_kwargs']['response_format']['type'], 'json_schema')
        self.assertIn('json_schema', kwargs['model_kwargs']['response_format'])
        # A basic check for schema structure
        self.assertIn('properties', kwargs['model_kwargs']['response_format']['json_schema'])
        self.assertIn('additions', kwargs['model_kwargs']['response_format']['json_schema']['properties'])


    def test_resort_langchain_gemini_docu_mode(self, MockChatOpenAI, MockChatGoogleGenerativeAI, MockGoogleAPI, MockOpenAIAPI, MockGeminiModels):
        """Test resort_langchain with Gemini in 'docu' mode."""
        handler = LLMHandler()
        mock_gemini_pro_instance = handler.gemini_llm
        mock_response_obj = MagicMock()
        mock_response_obj.content = json.dumps(self.mock_resort_response_content_docu)
        mock_gemini_pro_instance.invoke.return_value = mock_response_obj

        docu_data_sample = {"category1": ["docA"]}
        docued_data_sample = {"category2": ["docB"]}
        result = handler.resort_langchain('gemini', docu_data_sample, docued_data_sample, 'docu')

        self.assertEqual(result, self.mock_resort_response_content_docu)
        mock_gemini_pro_instance.invoke.assert_called_once()
        args, kwargs = mock_gemini_pro_instance.invoke.call_args
        self.assertIsInstance(args[0][0], SystemMessage)
        self.assertIsInstance(args[0][1], HumanMessage)
        self.assertIn(json.dumps(docu_data_sample, ensure_ascii=False, indent=2), args[0][1].content)
        self.assertIn(json.dumps(docued_data_sample, ensure_ascii=False, indent=2), args[0][1].content)

        self.assertIn('generation_config', kwargs)
        self.assertEqual(kwargs['generation_config']['response_mime_type'], 'application/json')
        self.assertIn('response_schema', kwargs['generation_config'])
        # A basic check for schema structure
        self.assertIn('properties', kwargs['generation_config']['response_schema'])
        self.assertIn('deletions', kwargs['generation_config']['response_schema']['properties'])

    def test_card_picker_openai_json_error(self, MockChatOpenAI, MockChatGoogleGenerativeAI, MockGoogleAPI, MockOpenAIAPI, MockGeminiModels):
        """Test card_picker with OpenAI returns empty list on JSON decode error."""
        handler = LLMHandler()
        mock_openai_instance = handler.openai_llm
        mock_response_obj = MagicMock()
        mock_response_obj.content = "this is not json" # Malformed JSON
        mock_openai_instance.invoke.return_value = mock_response_obj

        with self.assertLogs(logger='src.ai.llm_handler', level='ERROR') as cm:
            recommendations = handler.card_picker_langchain('openai', 'test title', 'docu content')
        
        self.assertEqual(recommendations, [])
        self.assertTrue(any("Failed to decode JSON response" in log_msg for log_msg in cm.output))

    def test_resort_gemini_json_error(self, MockChatOpenAI, MockChatGoogleGenerativeAI, MockGoogleAPI, MockOpenAIAPI, MockGeminiModels):
        """Test resort_langchain with Gemini returns None on JSON decode error."""
        handler = LLMHandler()
        mock_gemini_instance = handler.gemini_llm
        mock_response_obj = MagicMock()
        mock_response_obj.content = "{'bad': 'json" # Malformed JSON
        mock_gemini_instance.invoke.return_value = mock_response_obj

        with self.assertLogs(logger='src.ai.llm_handler', level='ERROR') as cm:
            result = handler.resort_langchain('gemini', {}, {}, 'docu')

        self.assertIsNone(result)
        self.assertTrue(any("Failed to decode JSON response" in log_msg for log_msg in cm.output))


if __name__ == '__main__':
    unittest.main()
