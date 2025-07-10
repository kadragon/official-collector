"""
데이터 저장용으로 사용하고 있는 json 파일을 제어합니다.
"""

import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

def load_json(file_path: str) -> Dict[str, Any]:
    """
    JSON 파일을 읽어서 딕셔너리로 반환합니다.

    Args:
        file_path (str): 읽을 JSON 파일의 경로

    Returns:
        Dict[str, Any]: JSON 데이터를 담은 딕셔너리. 파일이 없거나 유효하지 않은 경우 빈 딕셔너리 반환
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"File {file_path} not found. Creating an empty dictionary.")
        return {}
    except json.JSONDecodeError:
        print(
            f"File {file_path} is not valid JSON. Creating an empty dictionary.")
        return {}


def save_json(file_path: str, data: Dict[str, Any]):
    """
    지정된 경로에 데이터를 JSON 형식으로 저장합니다.
    """
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except IOError as e:
        logger.error(f"Error saving JSON to {file_path}: {e}")
