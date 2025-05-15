"""
데이터 저장용으로 사용하고 있는 json 파일을 제어합니다.
"""

import logging
import os
import glob
import json
from datetime import datetime
import shutil
from typing import Dict, Any
from ai.ai_gemini import AIManager

logging.basicConfig(level=logging.INFO)
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


def update_sort_data(sort_data, sorted_data, src_path='./data/sort_data.json') -> None:
    """
    정렬 데이터를 업데이트하고 백업을 생성합니다.

    Args:
        src_path (str): 정렬 데이터 파일 경로. 기본값은 './data/sort_data.json'
    """
    ai = AIManager()

    backup_pattern = "./data/sort_data_*.json"
    for old_backup in glob.glob(backup_pattern):
        os.remove(old_backup)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    backup_path = f"./data/backup/sort_data_{timestamp}.json"

    if os.path.exists(src_path):
        shutil.copy(src_path, backup_path)

    try:
        response = ai.resort(sort_data, sorted_data, 'sort')

        if 'deletions' in response:
            for deletion in response['deletions']:
                title = deletion['title']
                approval = deletion['approval']

                if approval in sort_data:
                    sort_data[approval] = [
                        item for item in sort_data[approval] if item['title'] != title]
                    print(f'삭제: {deletion}')
                else:
                    print(
                        f"경고: 삭제하려는 approval 키 '{approval}'가 sort_data에 존재하지 않습니다.")

        if 'additions' in response:
            for addition in response['additions']:
                title = addition['title']
                share = addition['share']
                approval = addition['approval']

                if approval not in sort_data:
                    sort_data[approval] = []  # 새로운 approval 키 생성

                # 중복 title 확인
                if not any(item['title'] == title for item in sort_data[approval]):
                    sort_data[approval].append({
                        "title": title,
                        "share": share
                    })
                    print(f'추가: {addition}')
                else:
                    print(f"경고: 이미 존재하는 title '{title}'을 추가하려 했습니다.")

    except KeyError as e:
        logger.error(f"KeyError 발생: {e}")
        logger.debug(f"sort_data: {sort_data}")
        logger.debug(f"response: {response}")
    except Exception as e:
        logger.error(f"예상치 못한 오류 발생: {e}")
        logger.debug(f"response: {response}")

    with open(src_path, "w", encoding="utf-8") as f:
        json.dump(sort_data, f, indent=4, ensure_ascii=False)


def update_docu_data(docu_data, docued_data, src_path='./data/docu_data.json') -> None:
    """
    문서 분류 데이터를 업데이트하고 백업을 생성합니다.

    Args:
        src_path (str): 정렬 데이터 파일 경로. 기본값은 './data/docu_data.json'
    """
    ai = AIManager()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    backup_path = f"./data/backup/docu_data_{timestamp}.json"

    if os.path.exists(src_path):
        shutil.copy(src_path, backup_path)

    response = ai.resort(docu_data, docued_data, 'docu')

    try:
        if 'deletions' in response:
            for deletion in response['deletions']:
                if deletion['document_name'] in docu_data.keys():
                    document_name = deletion['document_name']
                    title = deletion['title']
                    docu_data[document_name] = [
                        item for item in docu_data[document_name] if item != title]
                    print(f'삭제: {deletion}')

        if 'additions' in response:
            for addition in response['additions']:
                if addition['document_name'] in docu_data.keys():
                    document_name = addition['document_name']
                    title = addition['title']

                    docu_data[document_name].append(title)
                    print(f'추가: {addition}')
    except Exception as e:
        print(f"Error processing document data response: {e}")
        print(response)

    with open(src_path, "w", encoding="utf-8") as f:
        json.dump(docu_data, f, indent=4, ensure_ascii=False)
