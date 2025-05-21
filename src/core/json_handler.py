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
# from ai.ai_openai import sorter # Removed old import
from pathlib import Path

from src.config.config import PREFERRED_LLM_MODEL # Added import
from src.ai.llm_handler import LLMHandler # Added import

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# src/core/json_handler.py 파일의 상단에서
# PROJECT_ROOT는 프로젝트 루트 경로를 지정
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# 백업 폴더 경로를 프로젝트 루트 하위로 지정
BACKUP_DIR = PROJECT_ROOT / "data" / "backup"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)  # 폴더가 없는 경우 자동 생성

# 백업 파일 경로 지정


def save_backup(timestamp):
    backup_path = BACKUP_DIR / f"sort_data_{timestamp}.json"
    print(f"Backup will be saved to: {backup_path}")


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
    backup_pattern = "./data/sort_data_*.json" # This path might need adjustment if src_path is not default
    # Adjust backup_pattern if src_path is different from default
    if src_path != './data/sort_data.json':
        src_p = Path(src_path)
        backup_pattern = str(src_p.parent / f"{src_p.stem}_*.json")

    for old_backup in glob.glob(backup_pattern):
        try:
            os.remove(old_backup)
        except OSError as e:
            logger.warning(f"Could not remove old backup {old_backup}: {e}")


    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    # Ensure backup_path uses the same directory and base name as src_path
    src_path_obj = Path(src_path)
    dynamic_backup_dir = src_path_obj.parent / "backup" # Store backups in a subfolder of data source
    dynamic_backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = dynamic_backup_dir / f"{src_path_obj.stem}_{timestamp}.json"


    if os.path.exists(src_path):
        try:
            shutil.copy(src_path, backup_path)
            logger.info(f"Backup of {src_path} created at {backup_path}")
        except Exception as e:
            logger.error(f"Failed to create backup for {src_path}: {e}")


    handler = LLMHandler() # Instantiated LLMHandler
    response = None # Initialize response to None for robust error handling
    try:
        print(f"Updating sort data using {PREFERRED_LLM_MODEL} model...")
        response = handler.resort_langchain(
            model_type=PREFERRED_LLM_MODEL,
            sort_data=sort_data,
            sorted_data=sorted_data,
            mode="sort"
        )

        if response is None:
            logger.error("LLMHandler returned None. No updates will be applied to sort_data.")
            # Optionally, restore from backup or skip writing file if response is critical
            return # Exit if no response

        if 'deletions' in response:
            for deletion in response['deletions']:
                title = deletion.get('title')
                approval = deletion.get('approval')

                if not title or not approval:
                    logger.warning(f"Skipping deletion with missing title or approval: {deletion}")
                    continue

                if approval in sort_data:
                    original_len = len(sort_data[approval])
                    sort_data[approval] = [
                        item for item in sort_data[approval] if item.get('title') != title]
                    if len(sort_data[approval]) < original_len:
                        print(f'삭제 (sort): {deletion}')
                    else:
                        logger.info(f"Deletion for title '{title}' in approval '{approval}' not found or already removed.")
                else:
                    logger.warning(
                        f"경고: 삭제하려는 approval 키 '{approval}'가 sort_data에 존재하지 않습니다. Deletion: {deletion}")

        if 'additions' in response:
            for addition in response['additions']:
                title = addition.get('title')
                share = addition.get('share')
                approval = addition.get('approval')

                if not title or not share or not approval:
                    logger.warning(f"Skipping addition with missing title, share, or approval: {addition}")
                    continue

                if approval not in sort_data:
                    sort_data[approval] = []

                if not any(item.get('title') == title for item in sort_data[approval]):
                    sort_data[approval].append({
                        "title": title,
                        "share": share
                    })
                    print(f'추가 (sort): {addition}')
                else:
                    logger.info(f"경고: 이미 존재하는 title '{title}'을(를) approval '{approval}'에 추가하려 했습니다. Addition: {addition}")
    
    except KeyError as e:
        logger.error(f"KeyError 발생 in update_sort_data: {e}. This might indicate unexpected response structure.")
        logger.debug(f"sort_data before error: {sort_data}")
        logger.debug(f"LLM response: {response}")
    except Exception as e:
        logger.error(f"예상치 못한 오류 발생 in update_sort_data: {e}")
        logger.debug(f"LLM response: {response}")

    try:
        with open(src_path, "w", encoding="utf-8") as f:
            json.dump(sort_data, f, indent=4, ensure_ascii=False)
        logger.info(f"Successfully updated {src_path}")
    except Exception as e:
        logger.error(f"Failed to write updated sort_data to {src_path}: {e}")


def update_docu_data(docu_data, docued_data, src_path='./data/docu_data.json') -> None:
    """
    문서 분류 데이터를 업데이트하고 백업을 생성합니다.

    Args:
        src_path (str): 정렬 데이터 파일 경로. 기본값은 './data/docu_data.json'
    """
    # Adjust backup_path logic similar to update_sort_data
    src_path_obj = Path(src_path)
    dynamic_backup_dir = src_path_obj.parent / "backup" # Store backups in a subfolder of data source
    dynamic_backup_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    backup_path = dynamic_backup_dir / f"{src_path_obj.stem}_{timestamp}.json"

    if os.path.exists(src_path):
        try:
            shutil.copy(src_path, backup_path)
            logger.info(f"Backup of {src_path} created at {backup_path}")
        except Exception as e:
            logger.error(f"Failed to create backup for {src_path}: {e}")

    handler = LLMHandler() # Instantiated LLMHandler
    response = None # Initialize for robust error handling

    try:
        print(f"Updating document data using {PREFERRED_LLM_MODEL} model...")
        response = handler.resort_langchain(
            model_type=PREFERRED_LLM_MODEL,
            sort_data=docu_data, # Mapped docu_data to sort_data parameter
            sorted_data=docued_data, # Mapped docued_data to sorted_data parameter
            mode="docu"
        )

        if response is None:
            logger.error("LLMHandler returned None. No updates will be applied to docu_data.")
            return # Exit if no response

        if 'deletions' in response:
            for deletion in response['deletions']:
                document_name = deletion.get('document_name')
                title = deletion.get('title')

                if not document_name or not title:
                    logger.warning(f"Skipping deletion with missing document_name or title: {deletion}")
                    continue
                
                if document_name in docu_data:
                    original_len = len(docu_data[document_name])
                    docu_data[document_name] = [
                        item for item in docu_data[document_name] if item != title] # Assuming items are strings
                    if len(docu_data[document_name]) < original_len:
                        print(f'삭제 (docu): {deletion}')
                    else:
                        logger.info(f"Deletion for title '{title}' in document_name '{document_name}' not found or already removed.")
                else:
                    logger.warning(f"Document category '{document_name}' not found in docu_data for deletion: {deletion}")


        if 'additions' in response:
            for addition in response['additions']:
                document_name = addition.get('document_name')
                title = addition.get('title')

                if not document_name or not title:
                    logger.warning(f"Skipping addition with missing document_name or title: {addition}")
                    continue

                if document_name not in docu_data:
                    logger.warning(f"Document category '{document_name}' not found in docu_data for addition. Creating it. Addition: {addition}")
                    docu_data[document_name] = []
                
                if title not in docu_data[document_name]: # Check for duplicates
                    docu_data[document_name].append(title)
                    print(f'추가 (docu): {addition}')
                else:
                    logger.info(f"Title '{title}' already exists in document_name '{document_name}'. Addition: {addition}")
    
    except KeyError as e:
        logger.error(f"KeyError 발생 in update_docu_data: {e}. This might indicate unexpected response structure.")
        logger.debug(f"docu_data before error: {docu_data}")
        logger.debug(f"LLM response: {response}")
    except Exception as e:
        logger.error(f"예상치 못한 오류 발생 in update_docu_data: {e}")
        logger.debug(f"LLM response: {response}")

    try:
        with open(src_path, "w", encoding="utf-8") as f:
            json.dump(docu_data, f, indent=4, ensure_ascii=False)
        logger.info(f"Successfully updated {src_path}")
    except Exception as e:
        logger.error(f"Failed to write updated docu_data to {src_path}: {e}")
