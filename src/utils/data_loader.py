"""기본 데이터 로딩을 위한 유틸리티 모듈."""

import json
import os
from typing import Dict, Any


def load_base_data() -> Dict[str, Any]:
    """
    base_data.json 파일에서 기본 데이터를 로드합니다.
    
    Returns:
        Dict[str, Any]: 카드 목록, 접수 담당자 목록, 공람 목록을 포함한 딕셔너리
    """
    # 프로젝트 루트 디렉토리에서 data/base_data.json 파일 경로 구성
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_dir))
    data_file_path = os.path.join(project_root, 'data', 'base_data.json')
    
    try:
        with open(data_file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        return data
    except FileNotFoundError:
        raise FileNotFoundError(f"기본 데이터 파일을 찾을 수 없습니다: {data_file_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON 파일 형식이 올바르지 않습니다: {e}")
    except Exception as e:
        raise RuntimeError(f"데이터 로딩 중 오류가 발생했습니다: {e}")