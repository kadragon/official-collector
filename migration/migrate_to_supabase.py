"""
ChromaDB → Supabase 마이그레이션 스크립트
Ollama embedding을 OpenAI embedding으로 변환하여 Supabase로 이관
"""

import os
import sys
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
import asyncio
from concurrent.futures import ThreadPoolExecutor
import time

# 프로젝트 루트를 Python path에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.services.supabase_service import SupabaseService
from src.services.openai_embedding_service import OpenAIEmbeddingService, EmbeddingRequest
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class SupabaseMigrator:
    """Supabase 마이그레이션 관리자"""
    
    def __init__(self):
        """초기화"""
        self.supabase = SupabaseService()
        self.openai_service = OpenAIEmbeddingService()
        self.migration_log = []
        
        logger.info("Supabase 마이그레이션 관리자 초기화 완료")
    
    def load_backup_data(self, backup_file: str) -> Dict[str, Any]:
        """백업 파일에서 데이터 로드"""
        logger.info(f"백업 파일 로드 중: {backup_file}")
        
        with open(backup_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        logger.info(f"로드 완료 - 업무카드: {len(data['task_cards'])}, 접수문서: {len(data['reception_documents'])}")
        return data
    
    def migrate_task_cards(self, task_cards: List[Dict[str, Any]], batch_size: int = 20) -> bool:
        """업무 카드 마이그레이션"""
        logger.info(f"=== 업무 카드 마이그레이션 시작 ({len(task_cards)}개) ===")
        
        if not task_cards:
            logger.info("마이그레이션할 업무 카드가 없습니다.")
            return True
        
        try:
            # 1단계: Supabase에 업무 카드 문서 생성
            logger.info("1단계: Supabase 업무 카드 생성 중...")
            created_cards = []
            
            for i, card in enumerate(task_cards, 1):
                try:
                    # 업무 카드 생성
                    task_id = self.supabase.create_task_card(
                        title=card['title'],
                        content=card.get('task_title', ''),
                        category='마이그레이션',
                        assigned_to='시스템',
                        metadata={
                            'migrated_from': 'chroma',
                            'original_registered_at': card.get('registered_at'),
                            'migration_timestamp': datetime.now().isoformat()
                        }
                    )
                    
                    created_cards.append({
                        'supabase_id': task_id,
                        'original_data': card
                    })
                    
                    if i % 10 == 0:
                        logger.info(f"진행률: {i}/{len(task_cards)} 업무카드 생성 완료")
                
                except Exception as e:
                    logger.error(f"업무 카드 생성 실패 ({card['title']}): {e}")
                    continue
            
            logger.info(f"2단계: OpenAI 임베딩 생성 중... ({len(created_cards)}개)")
            
            # 2단계: 배치로 임베딩 생성
            embedding_requests = []
            for card_data in created_cards:
                original = card_data['original_data']
                embedding_text = f"{original['title']} {original.get('task_title', '')}"
                
                embedding_requests.append(EmbeddingRequest(
                    text=embedding_text,
                    identifier=card_data['supabase_id'],
                    metadata={
                        'title': original['title'],
                        'type': 'task_card'
                    }
                ))
            
            # 배치 임베딩 생성
            embedding_results = self.openai_service.create_embeddings_batch(
                embedding_requests, batch_size=batch_size
            )
            
            logger.info(f"3단계: Supabase 임베딩 저장 중... ({len(embedding_results)}개)")
            
            # 3단계: Supabase에 임베딩 저장
            embedding_data_list = []
            for result in embedding_results:
                original_card = next(
                    (c['original_data'] for c in created_cards if c['supabase_id'] == result.identifier),
                    None
                )
                
                if original_card:
                    embedding_data_list.append({
                        'document_id': result.identifier,
                        'document_type': 'task_card',
                        'title': result.metadata.get('title', original_card['title']),
                        'content_summary': original_card.get('task_title', '')[:200],
                        'embedding': result.embedding,
                        'embedding_model': 'text-embedding-3-small',
                        'metadata': {
                            'migrated_from': 'chroma',
                            'original_registered_at': original_card.get('registered_at'),
                            'token_count': result.token_count
                        }
                    })
            
            # 배치 임베딩 삽입
            success = self.supabase.batch_insert_embeddings(embedding_data_list)
            
            if success:
                logger.info(f"✅ 업무 카드 마이그레이션 완료: {len(embedding_results)}개")
                self.migration_log.append({
                    'type': 'task_cards',
                    'success_count': len(embedding_results),
                    'total_count': len(task_cards),
                    'timestamp': datetime.now().isoformat()
                })
                return True
            else:
                logger.error("❌ 임베딩 배치 삽입 실패")
                return False
        
        except Exception as e:
            logger.error(f"업무 카드 마이그레이션 중 오류: {e}")
            return False
    
    def migrate_reception_documents(self, reception_docs: List[Dict[str, Any]], batch_size: int = 20) -> bool:
        """접수 문서 마이그레이션"""
        logger.info(f"=== 접수 문서 마이그레이션 시작 ({len(reception_docs)}개) ===")
        
        if not reception_docs:
            logger.info("마이그레이션할 접수 문서가 없습니다.")
            return True
        
        try:
            # 1단계: Supabase에 접수 문서 생성
            logger.info("1단계: Supabase 접수 문서 생성 중...")
            created_docs = []
            
            for i, doc in enumerate(reception_docs, 1):
                try:
                    # 접수 문서 생성
                    doc_id = self.supabase.create_reception_document(
                        title=doc['title'],
                        content=f"담당: {doc.get('approval', '')}, 공유: {doc.get('share', '')}",
                        handler=doc.get('approval'),
                        approval_chain=[doc.get('approval')] if doc.get('approval') else [],
                        metadata={
                            'migrated_from': 'chroma',
                            'original_registered_at': doc.get('registered_at'),
                            'original_share': doc.get('share'),
                            'migration_timestamp': datetime.now().isoformat()
                        }
                    )
                    
                    created_docs.append({
                        'supabase_id': doc_id,
                        'original_data': doc
                    })
                    
                    if i % 10 == 0:
                        logger.info(f"진행률: {i}/{len(reception_docs)} 접수문서 생성 완료")
                
                except Exception as e:
                    logger.error(f"접수 문서 생성 실패 ({doc['title']}): {e}")
                    continue
            
            # 2단계: 임베딩 생성 및 저장 (업무카드와 동일한 로직)
            logger.info(f"2단계: OpenAI 임베딩 생성 중... ({len(created_docs)}개)")
            
            embedding_requests = []
            for doc_data in created_docs:
                original = doc_data['original_data']
                embedding_text = f"{original['title']} {original.get('approval', '')} {original.get('share', '')}"
                
                embedding_requests.append(EmbeddingRequest(
                    text=embedding_text,
                    identifier=doc_data['supabase_id'],
                    metadata={
                        'title': original['title'],
                        'type': 'reception_document'
                    }
                ))
            
            embedding_results = self.openai_service.create_embeddings_batch(
                embedding_requests, batch_size=batch_size
            )
            
            # 3단계: 임베딩 저장
            logger.info(f"3단계: Supabase 임베딩 저장 중... ({len(embedding_results)}개)")
            
            embedding_data_list = []
            for result in embedding_results:
                original_doc = next(
                    (d['original_data'] for d in created_docs if d['supabase_id'] == result.identifier),
                    None
                )
                
                if original_doc:
                    embedding_data_list.append({
                        'document_id': result.identifier,
                        'document_type': 'reception_document',
                        'title': result.metadata.get('title', original_doc['title']),
                        'content_summary': f"담당: {original_doc.get('approval', '')}"[:200],
                        'embedding': result.embedding,
                        'embedding_model': 'text-embedding-3-small',
                        'metadata': {
                            'migrated_from': 'chroma',
                            'original_registered_at': original_doc.get('registered_at'),
                            'token_count': result.token_count
                        }
                    })
            
            success = self.supabase.batch_insert_embeddings(embedding_data_list)
            
            if success:
                logger.info(f"✅ 접수 문서 마이그레이션 완료: {len(embedding_results)}개")
                self.migration_log.append({
                    'type': 'reception_documents',
                    'success_count': len(embedding_results),
                    'total_count': len(reception_docs),
                    'timestamp': datetime.now().isoformat()
                })
                return True
            else:
                logger.error("❌ 임베딩 배치 삽입 실패")
                return False
        
        except Exception as e:
            logger.error(f"접수 문서 마이그레이션 중 오류: {e}")
            return False
    
    def verify_migration(self) -> Dict[str, Any]:
        """마이그레이션 검증"""
        logger.info("=== 마이그레이션 검증 시작 ===")
        
        try:
            # Supabase 데이터 개수 확인
            task_cards = self.supabase.list_task_cards(limit=1000)
            reception_docs = self.supabase.list_reception_documents(limit=1000)
            
            # 임베딩 개수 확인 (간접적으로)
            status = self.supabase.get_connection_status()
            
            verification = {
                'supabase_connected': status.get('connected', False),
                'task_cards_count': len(task_cards),
                'reception_documents_count': len(reception_docs),
                'migration_log': self.migration_log,
                'cost_summary': self.openai_service.get_cost_summary(),
                'verification_timestamp': datetime.now().isoformat()
            }
            
            logger.info("=== 검증 결과 ===")
            logger.info(f"Supabase 연결: {verification['supabase_connected']}")
            logger.info(f"업무 카드: {verification['task_cards_count']}개")
            logger.info(f"접수 문서: {verification['reception_documents_count']}개")
            logger.info(f"총 비용: ${verification['cost_summary']['total_cost_usd']:.6f}")
            
            return verification
        
        except Exception as e:
            logger.error(f"마이그레이션 검증 중 오류: {e}")
            return {'error': str(e)}
    
    def save_migration_report(self, verification: Dict[str, Any]):
        """마이그레이션 보고서 저장"""
        report_dir = "./data/migration_reports"
        os.makedirs(report_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"{report_dir}/migration_report_{timestamp}.json"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(verification, f, ensure_ascii=False, indent=2)
        
        logger.info(f"마이그레이션 보고서 저장: {report_file}")
        return report_file


def main():
    """메인 마이그레이션 실행"""
    logger.info("=== ChromaDB → Supabase 마이그레이션 시작 ===")
    
    try:
        # 1. 최신 백업 파일 찾기
        backup_dir = "./data/backup"
        backup_files = [f for f in os.listdir(backup_dir) if f.startswith('chroma_backup_') and f.endswith('.json')]
        
        if not backup_files:
            logger.error("백업 파일을 찾을 수 없습니다. extract_chroma_data.py를 먼저 실행하세요.")
            return False
        
        # 가장 최신 백업 파일 선택
        latest_backup = max(backup_files)
        backup_path = os.path.join(backup_dir, latest_backup)
        
        logger.info(f"백업 파일 사용: {backup_path}")
        
        # 2. 마이그레이터 초기화
        migrator = SupabaseMigrator()
        
        # 3. 백업 데이터 로드
        backup_data = migrator.load_backup_data(backup_path)
        
        # 4. 데이터 마이그레이션
        task_success = migrator.migrate_task_cards(backup_data['task_cards'])
        reception_success = migrator.migrate_reception_documents(backup_data['reception_documents'])
        
        # 5. 마이그레이션 검증
        verification = migrator.verify_migration()
        
        # 6. 보고서 저장
        report_file = migrator.save_migration_report(verification)
        
        # 7. 결과 출력
        if task_success and reception_success:
            print(f"\n🎉 마이그레이션 완료!")
            print(f"📊 업무 카드: {verification.get('task_cards_count', 0)}개")
            print(f"📄 접수 문서: {verification.get('reception_documents_count', 0)}개")
            
            cost_info = verification.get('cost_summary', {})
            print(f"💰 총 비용: ${cost_info.get('total_cost_usd', 0):.6f}")
            print(f"🔢 총 토큰: {cost_info.get('total_tokens', 0)}")
            print(f"📁 보고서: {report_file}")
            
            return True
        else:
            logger.error("마이그레이션 중 일부 실패 발생")
            return False
    
    except Exception as e:
        logger.error(f"마이그레이션 실행 중 오류: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)