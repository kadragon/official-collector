"""
데이터 로딩 및 검증을 위한 유틸리티 모듈.
"""

import json
from typing import Dict, Any, List, Optional, Union
from pathlib import Path

from .error_handler import setup_logger, safe_execute

logger = setup_logger(__name__)


def load_json(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    JSON 파일을 읽어서 딕셔너리로 반환합니다.

    Args:
        file_path (Union[str, Path]): 읽을 JSON 파일의 경로.

    Returns:
        Dict[str, Any]: JSON 데이터를 담은 딕셔너리. 파일이 없거나 유효하지 않은 경우 빈 딕셔너리 반환.
    """
    file_path = Path(file_path)

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            logger.info(f"JSON 파일 로드 성공: {file_path}")
            return data
    except FileNotFoundError:
        logger.warning(f"파일을 찾을 수 없습니다: {file_path}. 빈 딕셔너리를 반환합니다.")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"JSON 형식이 올바르지 않습니다: {file_path}. 오류: {e}")
        return {}
    except Exception as e:
        logger.error(f"파일 로드 중 예상치 못한 오류 발생: {file_path}. 오류: {e}")
        return {}


def save_json(file_path: Union[str, Path], data: Dict[str, Any]) -> bool:
    """
    지정된 경로에 데이터를 JSON 형식으로 저장합니다.

    Args:
        file_path (Union[str, Path]): 저장할 JSON 파일의 경로.
        data (Dict[str, Any]): 저장할 데이터.

    Returns:
        bool: 저장 성공 시 True, 실패 시 False.
    """
    file_path = Path(file_path)

    try:
        # 디렉토리가 없으면 생성
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

        logger.info(f"JSON 파일 저장 성공: {file_path}")
        return True

    except IOError as e:
        logger.error(f"파일 저장 중 IO 오류 발생: {file_path}. 오류: {e}")
        return False
    except Exception as e:
        logger.error(f"파일 저장 중 예상치 못한 오류 발생: {file_path}. 오류: {e}")
        return False


def load_base_data(base_data_path: Optional[Union[str, Path]] = None) -> Dict[str, List[str]]:
    """
    기본 데이터를 로드합니다.

    Args:
        base_data_path (Optional[Union[str, Path]]): 기본 데이터 파일 경로.

    Returns:
        Dict[str, List[str]]: 기본 데이터.
    """
    if base_data_path is None:
        # 기본 경로 설정
        project_root = Path(__file__).resolve().parents[2]
        base_data_path = project_root / "data" / "base_data.json"

    data = load_json(base_data_path)

    # 기본 구조 검증 및 기본값 설정
    default_structure = {
        "card_list": [],
        "reception_list": [],
        "share_list": []
    }

    for key, default_value in default_structure.items():
        if key not in data:
            logger.warning(f"기본 데이터에서 '{key}' 키를 찾을 수 없습니다. 기본값으로 설정합니다.")
            data[key] = default_value

    return data


def validate_data_structure(data: Dict[str, Any], required_keys: List[str]) -> bool:
    """
    데이터 구조가 유효한지 검증합니다.

    Args:
        data (Dict[str, Any]): 검증할 데이터.
        required_keys (List[str]): 필수 키 목록.

    Returns:
        bool: 구조가 유효하면 True, 아니면 False.
    """
    missing_keys = [key for key in required_keys if key not in data]

    if missing_keys:
        logger.error(f"필수 키가 누락되었습니다: {missing_keys}")
        return False

    return True




def load_with_fallback(primary_path: Union[str, Path], fallback_path: Union[str, Path]) -> Dict[str, Any]:
    """
    기본 파일을 로드하고, 실패 시 대체 파일을 로드합니다.

    Args:
        primary_path (Union[str, Path]): 기본 파일 경로.
        fallback_path (Union[str, Path]): 대체 파일 경로.

    Returns:
        Dict[str, Any]: 로드된 데이터.
    """
    data = load_json(primary_path)

    if not data:  # 기본 파일 로드 실패
        logger.info(f"기본 파일 로드 실패, 대체 파일을 시도합니다: {fallback_path}")
        data = load_json(fallback_path)

        if data:
            logger.info(f"대체 파일 로드 성공: {fallback_path}")
        else:
            logger.error("기본 파일과 대체 파일 모두 로드에 실패했습니다.")

    return data


def merge_data_lists(base_data: Dict[str, List[str]], additional_data: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """
    두 데이터 구조를 병합합니다 (리스트 중복 제거).

    Args:
        base_data (Dict[str, List[str]]): 기본 데이터.
        additional_data (Dict[str, List[str]]): 추가 데이터.

    Returns:
        Dict[str, List[str]]: 병합된 데이터.
    """
    merged = base_data.copy()

    for key, values in additional_data.items():
        if key in merged:
            # 중복 제거하면서 병합
            combined_list = merged[key] + values
            merged[key] = list(dict.fromkeys(combined_list))  # 순서 유지하면서 중복 제거
        else:
            merged[key] = values.copy()

    return merged




def get_data_statistics(data: Dict[str, List[str]]) -> Dict[str, int]:
    """
    데이터 통계를 반환합니다.

    Args:
        data (Dict[str, List[str]]): 분석할 데이터.

    Returns:
        Dict[str, int]: 각 키별 항목 개수.
    """
    return {key: len(values) for key, values in data.items()}
