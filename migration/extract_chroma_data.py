"""
ChromaDB 데이터 추출 스크립트
기존 ChromaDB에서 모든 문서와 메타데이터를 추출하여 마이그레이션을 위해 준비
"""

import os
import sys
import json
import logging
from datetime import datetime
from typing import List, Dict, Any

# 프로젝트 루트를 Python path에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# ChromaService import를 위한 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from services.chroma_service import ChromaService
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def extract_chroma_data():
    """ChromaDB에서 모든 데이터를 추출"""
    logger.info("=== ChromaDB 데이터 추출 시작 ===")
    
    try:
        # ChromaService 초기화
        ollama_base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
        ollama_model = os.getenv('OLLAMA_MODEL', 'snowflake-arctic-embed')
        chroma_persist_dir = os.getenv('CHROMA_PERSIST_DIR', './chroma_db')
        
        chroma_service = ChromaService(
            ollama_base_url=ollama_base_url,
            ollama_model=ollama_model,
            chroma_persist_dir=chroma_persist_dir
        )
        
        # 모든 데이터 추출
        extracted_data = {
            'extraction_info': {
                'timestamp': datetime.now().isoformat(),
                'source_model': ollama_model,
                'source_dimensions': None,  # 실제 차원수는 나중에 계산
                'chroma_persist_dir': chroma_persist_dir
            },
            'reception_documents': [],
            'task_cards': [],
            'all_documents': []  # 원시 벡터 데이터 포함
        }
        
        logger.info("접수 문서 추출 중...")
        
        # 접수 문서 데이터 추출
        reception_data = chroma_service.list_all_receptions()
        logger.info(f"접수 문서 {len(reception_data)}개 발견")
        
        for title, approval, share, registered_at in reception_data:
            extracted_data['reception_documents'].append({
                'title': title,
                'approval': approval,
                'share': share,
                'registered_at': registered_at,
                'type': 'reception'
            })
        
        logger.info("업무 카드 추출 중...")
        
        # 업무 카드 데이터 추출
        card_data = chroma_service.list_all_cards()
        logger.info(f"업무 카드 {len(card_data)}개 발견")
        
        for title, task_title, registered_at in card_data:
            extracted_data['task_cards'].append({
                'title': title,
                'task_title': task_title,
                'registered_at': registered_at,
                'type': 'card'
            })
        
        logger.info("원시 벡터 데이터 추출 중...")
        
        # 직접 ChromaDB에서 모든 문서 추출 (벡터 포함)
        try:
            # 모든 문서 가져오기
            all_docs = chroma_service.vector_store.get(include=['embeddings', 'metadatas', 'documents'])
            
            logger.info(f"총 {len(all_docs['ids'])}개 문서 발견")
            
            # 차원 수 계산
            if all_docs['embeddings'] and len(all_docs['embeddings']) > 0:
                extracted_data['extraction_info']['source_dimensions'] = len(all_docs['embeddings'][0])
                logger.info(f"소스 임베딩 차원: {extracted_data['extraction_info']['source_dimensions']}")
            
            # 각 문서 처리
            for i, doc_id in enumerate(all_docs['ids']):
                document_data = {
                    'id': doc_id,
                    'content': all_docs['documents'][i] if i < len(all_docs['documents']) else '',
                    'metadata': all_docs['metadatas'][i] if i < len(all_docs['metadatas']) else {},
                    'embedding': all_docs['embeddings'][i] if i < len(all_docs['embeddings']) else [],
                    'embedding_length': len(all_docs['embeddings'][i]) if i < len(all_docs['embeddings']) and all_docs['embeddings'][i] else 0
                }
                
                extracted_data['all_documents'].append(document_data)
        
        except Exception as e:
            logger.error(f"원시 데이터 추출 중 오류: {e}")
        
        # 데이터 저장
        backup_dir = "./data/backup"
        os.makedirs(backup_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"{backup_dir}/chroma_backup_{timestamp}.json"
        
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(extracted_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"데이터 백업 완료: {backup_file}")
        
        # 요약 정보 출력
        summary = {
            'total_documents': len(extracted_data['all_documents']),
            'reception_documents': len(extracted_data['reception_documents']),
            'task_cards': len(extracted_data['task_cards']),
            'source_dimensions': extracted_data['extraction_info']['source_dimensions'],
            'backup_file': backup_file
        }
        
        logger.info("=== 추출 완료 요약 ===")
        for key, value in summary.items():
            logger.info(f"{key}: {value}")
        
        return extracted_data, backup_file
        
    except Exception as e:
        logger.error(f"데이터 추출 중 오류 발생: {e}")
        raise


def analyze_chroma_collection():
    """ChromaDB 컬렉션 분석"""
    logger.info("=== ChromaDB 컬렉션 분석 ===")
    
    try:
        import chromadb
        
        chroma_persist_dir = os.getenv('CHROMA_PERSIST_DIR', './chroma_db')
        client = chromadb.PersistentClient(path=chroma_persist_dir)
        
        # 컬렉션 목록
        collections = client.list_collections()
        logger.info(f"컬렉션 수: {len(collections)}")
        
        for collection in collections:
            logger.info(f"컬렉션 이름: {collection.name}")
            count = collection.count()
            logger.info(f"문서 수: {count}")
            
            if count > 0:
                # 샘플 데이터 가져오기
                sample = collection.get(limit=1, include=['embeddings', 'metadatas'])
                if sample['embeddings']:
                    dim = len(sample['embeddings'][0])
                    logger.info(f"임베딩 차원: {dim}")
                if sample['metadatas']:
                    logger.info(f"샘플 메타데이터: {sample['metadatas'][0]}")
        
    except Exception as e:
        logger.error(f"컬렉션 분석 중 오류: {e}")


def main():
    """메인 함수"""
    try:
        # 1. 컬렉션 분석
        analyze_chroma_collection()
        
        # 2. 데이터 추출
        extracted_data, backup_file = extract_chroma_data()
        
        print(f"\n✅ ChromaDB 데이터 추출 완료!")
        print(f"📁 백업 파일: {backup_file}")
        print(f"📊 총 문서 수: {len(extracted_data['all_documents'])}")
        print(f"📄 접수 문서: {len(extracted_data['reception_documents'])}")
        print(f"📝 업무 카드: {len(extracted_data['task_cards'])}")
        print(f"📐 소스 차원: {extracted_data['extraction_info']['source_dimensions']}")
        
        return True
        
    except Exception as e:
        logger.error(f"추출 실패: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)