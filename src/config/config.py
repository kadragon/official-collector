"""애플리케이션의 환경 설정 및 상수를 관리하는 모듈."""

import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Gemini 모델 설정
GEMINI_MODELS = {
    'flash': 'gemini-2.0-flash',
    'pro': 'gemini-2.0-pro-exp'
}

# Specifies the default LLM to use: 'openai' or 'gemini'
PREFERRED_LLM_MODEL = "openai"
