"""
Supabase 데이터베이스 서비스 클래스
벡터 유사도 검색, CRUD 연산, 배치 업데이트 기능 제공
"""

import os
import logging
from typing import List, Dict, Any, Optional, Tuple, Union
from uuid import UUID, uuid4
import json
from datetime import datetime

from supabase import create_client, Client
from dotenv import load_dotenv
from .openai_embedding_service import OpenAIEmbeddingService

# 환경변수 로드
load_dotenv()

logger = logging.getLogger(__name__)


class SupabaseService:
    """Supabase 데이터베이스 서비스"""
    
    def __init__(self):
        """Supabase 클라이언트 초기화"""
        self.url = os.getenv('SUPABASE_URL')
        self.key = os.getenv('SUPABASE_KEY')
        
        if not self.url or not self.key:
            raise ValueError("SUPABASE_URL과 SUPABASE_KEY 환경변수가 필요합니다")
        
        self.client: Client = create_client(self.url, self.key)
        
        # OpenAI 임베딩 서비스 초기화
        self.embedding_service = OpenAIEmbeddingService()
        
        logger.info("Supabase 클라이언트 및 OpenAI 임베딩 서비스 초기화 완료")
    
    # Reception Documents 관련 메서드
    def create_reception_document(self, title: str, content: str = None, 
                                 handler: str = None, approval_chain: List[str] = None,
                                 metadata: Dict[str, Any] = None) -> str:
        """접수 문서 생성"""
        try:
            document_id = str(uuid4())
            data = {
                'id': document_id,
                'title': title,
                'content': content,
                'handler': handler,
                'approval_chain': approval_chain or [],
                'status': 'pending',
                'metadata': metadata or {}
            }
            
            result = self.client.table('reception_documents').insert(data).execute()
            logger.info(f"접수 문서 생성 완료: {title}")
            return document_id
        except Exception as e:
            logger.error(f"접수 문서 생성 실패: {e}")
            raise
    
    def get_reception_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """접수 문서 조회"""
        try:
            result = self.client.table('reception_documents').select('*').eq('id', document_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"접수 문서 조회 실패: {e}")
            return None
    
    def update_reception_document(self, document_id: str, **kwargs) -> bool:
        """접수 문서 업데이트"""
        try:
            update_data = {k: v for k, v in kwargs.items() if v is not None}
            update_data['updated_at'] = datetime.utcnow().isoformat()
            
            result = self.client.table('reception_documents').update(update_data).eq('id', document_id).execute()
            logger.info(f"접수 문서 업데이트 완료: {document_id}")
            return True
        except Exception as e:
            logger.error(f"접수 문서 업데이트 실패: {e}")
            return False
    
    def list_reception_documents(self, status: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """접수 문서 목록 조회"""
        try:
            query = self.client.table('reception_documents').select('*')
            
            if status:
                query = query.eq('status', status)
            
            result = query.order('created_at', desc=True).limit(limit).execute()
            return result.data
        except Exception as e:
            logger.error(f"접수 문서 목록 조회 실패: {e}")
            return []
    
    # Task Cards 관련 메서드
    def create_task_card(self, title: str, content: str = None, category: str = None,
                        priority: str = 'medium', assigned_to: str = None,
                        metadata: Dict[str, Any] = None) -> str:
        """업무카드 생성"""
        try:
            task_id = str(uuid4())
            data = {
                'id': task_id,
                'title': title,
                'content': content,
                'category': category,
                'priority': priority,
                'assigned_to': assigned_to,
                'status': 'active',
                'metadata': metadata or {}
            }
            
            result = self.client.table('task_cards').insert(data).execute()
            logger.info(f"업무카드 생성 완료: {title}")
            return task_id
        except Exception as e:
            logger.error(f"업무카드 생성 실패: {e}")
            raise
    
    def get_task_card(self, task_id: str) -> Optional[Dict[str, Any]]:
        """업무카드 조회"""
        try:
            result = self.client.table('task_cards').select('*').eq('id', task_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"업무카드 조회 실패: {e}")
            return None
    
    def list_task_cards(self, category: str = None, status: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """업무카드 목록 조회"""
        try:
            query = self.client.table('task_cards').select('*')
            
            if category:
                query = query.eq('category', category)
            if status:
                query = query.eq('status', status)
            
            result = query.order('created_at', desc=True).limit(limit).execute()
            return result.data
        except Exception as e:
            logger.error(f"업무카드 목록 조회 실패: {e}")
            return []
    
    # Document Embeddings 관련 메서드
    def store_embedding(self, document_id: str, document_type: str, title: str,
                       embedding: List[float], content_summary: str = None,
                       metadata: Dict[str, Any] = None) -> str:
        """임베딩 저장"""
        try:
            embedding_id = str(uuid4())
            data = {
                'id': embedding_id,
                'document_id': document_id,
                'document_type': document_type,
                'title': title,
                'content_summary': content_summary,
                'embedding': embedding,
                'embedding_model': 'text-embedding-3-small',
                'metadata': metadata or {}
            }
            
            result = self.client.table('document_embeddings').insert(data).execute()
            logger.info(f"임베딩 저장 완료: {title}")
            return embedding_id
        except Exception as e:
            logger.error(f"임베딩 저장 실패: {e}")
            raise
    
    def find_similar_documents(self, query_embedding: List[float], 
                              document_type: str = None, limit: int = 5,
                              similarity_threshold: float = 0.7) -> List[Dict[str, Any]]:
        """벡터 유사도 검색"""
        try:
            # pgvector 코사인 유사도 검색 쿼리
            query = """
            SELECT 
                de.*,
                1 - (de.embedding <=> %s::vector) as similarity
            FROM document_embeddings de
            WHERE 1 - (de.embedding <=> %s::vector) > %s
            """
            
            params = [query_embedding, query_embedding, similarity_threshold]
            
            if document_type:
                query += " AND de.document_type = %s"
                params.append(document_type)
            
            query += " ORDER BY de.embedding <=> %s::vector LIMIT %s"
            params.extend([query_embedding, limit])
            
            # Supabase RPC 함수를 사용하여 원시 SQL 실행
            result = self.client.rpc('execute_sql', {
                'query': query,
                'params': params
            }).execute()
            
            return result.data if result.data else []
        except Exception as e:
            logger.error(f"유사도 검색 실패: {e}")
            return []
    
    def delete_embedding(self, document_id: str) -> bool:
        """임베딩 삭제"""
        try:
            result = self.client.table('document_embeddings').delete().eq('document_id', document_id).execute()
            logger.info(f"임베딩 삭제 완료: {document_id}")
            return True
        except Exception as e:
            logger.error(f"임베딩 삭제 실패: {e}")
            return False
    
    # 배치 처리 메서드
    def batch_insert_embeddings(self, embeddings_data: List[Dict[str, Any]]) -> bool:
        """임베딩 배치 삽입"""
        try:
            # UUID 생성 및 기본값 설정
            for data in embeddings_data:
                if 'id' not in data:
                    data['id'] = str(uuid4())
                if 'embedding_model' not in data:
                    data['embedding_model'] = 'text-embedding-3-small'
                if 'metadata' not in data:
                    data['metadata'] = {}
            
            result = self.client.table('document_embeddings').insert(embeddings_data).execute()
            logger.info(f"임베딩 배치 삽입 완료: {len(embeddings_data)}개")
            return True
        except Exception as e:
            logger.error(f"임베딩 배치 삽입 실패: {e}")
            return False
    
    def batch_update_documents(self, document_type: str, updates: List[Dict[str, Any]]) -> bool:
        """문서 배치 업데이트"""
        try:
            table_name = 'reception_documents' if document_type == 'reception_document' else 'task_cards'
            
            for update in updates:
                document_id = update.pop('id')
                update['updated_at'] = datetime.utcnow().isoformat()
                self.client.table(table_name).update(update).eq('id', document_id).execute()
            
            logger.info(f"{document_type} 배치 업데이트 완료: {len(updates)}개")
            return True
        except Exception as e:
            logger.error(f"{document_type} 배치 업데이트 실패: {e}")
            return False
    
    # 새로운 매핑 테이블 메서드 (단순화된 구조)
    def retrieve_reception_by_title(self, title: str) -> Tuple[Optional[str], Optional[str]]:
        """제목으로 접수 문서 매핑 조회"""
        try:
            result = self.client.table('reception_mappings').select('handler', 'share_target').eq('title', title).execute()
            if result.data:
                data = result.data[0]
                return data['handler'], data['share_target']
            return None, None
        except Exception as e:
            logger.error(f"접수 문서 제목 조회 실패: {e}")
            return None, None
    
    def recommend_reception(self, title: str, count: int = 3) -> List[Dict[str, Any]]:
        """벡터 유사도 기반 접수 문서 추천"""
        try:
            # 1. 쿼리 텍스트 임베딩 생성
            embedding_response = self.embedding_service.create_embedding(title, f"query_{title}")
            if not embedding_response:
                logger.warning(f"임베딩 생성 실패: {title}")
                return []
            
            query_embedding = embedding_response.embedding
            
            # 2. pgvector 코사인 유사도 검색 수행
            try:
                result = self.client.rpc('search_reception_mappings', {
                    'query_embedding': query_embedding,
                    'similarity_threshold': 0.3,  # 임계값을 0.5에서 0.3으로 낮춤
                    'match_count': count
                }).execute()
                
                recommendations = []
                if result.data:
                    for item in result.data:
                        recommendations.append({
                            'approval': item['handler'],
                            'share': item['share_target'] or '공람없음',
                            'similarity': item.get('similarity', 0),
                            'title': item['title']
                        })
                
                logger.info(f"접수 문서 추천 완료: {len(recommendations)}개")
                return recommendations
                
            except Exception as e:
                logger.error(f"벡터 검색 실패: {e}")
                return []
                
        except Exception as e:
            logger.error(f"접수 문서 추천 실패: {e}")
            return []
    
    
    def retrieve_card_by_title(self, title: str) -> Optional[str]:
        """제목으로 업무카드 매핑 조회"""
        try:
            result = self.client.table('task_card_mappings').select('task_title').eq('title', title).execute()
            if result.data:
                return result.data[0]['task_title']
            return None
        except Exception as e:
            logger.error(f"업무카드 제목 조회 실패: {e}")
            return None
    
    def recommend_cards(self, title: str, count: int = 5) -> List[str]:
        """벡터 유사도 기반 업무카드 추천"""
        try:
            # 1. 쿼리 텍스트 임베딩 생성
            embedding_response = self.embedding_service.create_embedding(title, f"query_{title}")
            if not embedding_response:
                logger.warning(f"임베딩 생성 실패: {title}")
                return []
            
            query_embedding = embedding_response.embedding
            
            # 2. pgvector 코사인 유사도 검색 수행
            try:
                result = self.client.rpc('search_task_card_mappings', {
                    'query_embedding': query_embedding,
                    'similarity_threshold': 0.3,  # 임계값을 0.5에서 0.3으로 낮춤
                    'match_count': count
                }).execute()
                
                recommendations = []
                if result.data:
                    for item in result.data:
                        recommendations.append(item['task_title'])
                
                logger.info(f"업무카드 추천 완료: {len(recommendations)}개")
                return recommendations
                
            except Exception as e:
                logger.error(f"벡터 검색 실패: {e}")
                return []
                
        except Exception as e:
            logger.error(f"업무카드 추천 실패: {e}")
            return []
    
    
    def upsert_reception_embedding(self, title: str, handler: str, share_target: str):
        """접수 문서 매핑 업서트 (임베딩 포함)"""
        try:
            # 1. 임베딩 생성
            embedding_response = self.embedding_service.create_embedding(title, f"reception_{title}")
            if not embedding_response:
                logger.warning(f"임베딩 생성 실패, 임베딩 없이 저장: {title}")
                embedding = None
            else:
                embedding = embedding_response.embedding
            
            # 2. 기존 데이터 확인
            existing = self.client.table('reception_mappings').select('id').eq('title', title).execute()
            
            data = {
                'title': title,
                'handler': handler,
                'share_target': share_target,
                'embedding': embedding,
                'updated_at': datetime.utcnow().isoformat()
            }
            
            if existing.data:
                # 업데이트
                result = self.client.table('reception_mappings').update(data).eq('title', title).execute()
                logger.info(f"접수 문서 매핑 업데이트: {title} -> {handler}/{share_target}")
            else:
                # 삽입
                result = self.client.table('reception_mappings').insert(data).execute()
                logger.info(f"접수 문서 매핑 생성: {title} -> {handler}/{share_target}")
            
            return True
        except Exception as e:
            logger.error(f"접수 문서 매핑 업서트 실패: {e}")
            return False
    
    def upsert_card_embedding(self, title: str, task_title: str):
        """업무카드 매핑 업서트 (임베딩 포함)"""
        try:
            # 1. 임베딩 생성
            embedding_response = self.embedding_service.create_embedding(title, f"task_card_{title}")
            if not embedding_response:
                logger.warning(f"임베딩 생성 실패, 임베딩 없이 저장: {title}")
                embedding = None
            else:
                embedding = embedding_response.embedding
            
            # 2. 기존 데이터 확인
            existing = self.client.table('task_card_mappings').select('id').eq('title', title).execute()
            
            data = {
                'title': title,
                'task_title': task_title,
                'embedding': embedding,
                'updated_at': datetime.utcnow().isoformat()
            }
            
            if existing.data:
                # 업데이트
                result = self.client.table('task_card_mappings').update(data).eq('title', title).execute()
                logger.info(f"업무카드 매핑 업데이트: {title} -> {task_title}")
            else:
                # 삽입
                result = self.client.table('task_card_mappings').insert(data).execute()
                logger.info(f"업무카드 매핑 생성: {title} -> {task_title}")
            
            return True
        except Exception as e:
            logger.error(f"업무카드 매핑 업서트 실패: {e}")
            return False
    
    def get_document_count(self, table_type: str = 'task_card') -> int:
        """문서 개수 조회"""
        try:
            table_name = 'task_card_mappings' if table_type == 'task_card' else 'reception_mappings'
            result = self.client.table(table_name).select('*', count='exact').limit(0).execute()
            return result.count if result.count is not None else 0
        except Exception as e:
            logger.error(f"문서 개수 조회 실패: {e}")
            return 0

    # 유틸리티 메서드
    def get_connection_status(self) -> Dict[str, Any]:
        """연결 상태 확인"""
        try:
            # 간단한 쿼리로 연결 테스트 (새 테이블 구조 사용)
            result = self.client.table('task_card_mappings').select('count', count='exact').limit(0).execute()
            return {
                'connected': True,
                'url': self.url,
                'tables': ['task_card_mappings', 'reception_mappings']
            }
        except Exception as e:
            return {
                'connected': False,
                'error': str(e)
            }
    
    def clear_all_data(self) -> bool:
        """모든 데이터 삭제 (개발/테스트용)"""
        try:
            self.client.table('task_card_mappings').delete().neq('id', '').execute()
            self.client.table('reception_mappings').delete().neq('id', '').execute()
            logger.warning("모든 데이터 삭제 완료")
            return True
        except Exception as e:
            logger.error(f"데이터 삭제 실패: {e}")
            return False
    
    # 삭제 인터페이스용 메서드들 (기존 ChromaService 호환성)
    def list_all_cards(self) -> List[Tuple[str, str, str]]:
        """모든 업무카드 매핑 목록 조회 (title, task_title, created_at)"""
        try:
            result = self.client.table('task_card_mappings').select('title', 'task_title', 'created_at').execute()
            return [(item['title'], item['task_title'], item['created_at']) for item in result.data]
        except Exception as e:
            logger.error(f"업무카드 목록 조회 실패: {e}")
            return []
    
    def list_all_receptions(self) -> List[Tuple[str, str, str, str]]:
        """모든 접수 문서 매핑 목록 조회 (title, handler, share_target, created_at)"""
        try:
            result = self.client.table('reception_mappings').select('title', 'handler', 'share_target', 'created_at').execute()
            return [(item['title'], item['handler'], item['share_target'], item['created_at']) for item in result.data]
        except Exception as e:
            logger.error(f"접수 문서 목록 조회 실패: {e}")
            return []
    
    def bulk_delete_cards(self, titles: List[str]) -> int:
        """업무카드 일괄 삭제"""
        try:
            deleted_count = 0
            for title in titles:
                result = self.client.table('task_card_mappings').delete().eq('title', title).execute()
                if result.data:
                    deleted_count += len(result.data)
            logger.info(f"업무카드 일괄 삭제 완료: {deleted_count}개")
            return deleted_count
        except Exception as e:
            logger.error(f"업무카드 일괄 삭제 실패: {e}")
            return 0
    
    def bulk_delete_receptions(self, titles: List[str]) -> int:
        """접수 문서 일괄 삭제"""
        try:
            deleted_count = 0
            for title in titles:
                result = self.client.table('reception_mappings').delete().eq('title', title).execute()
                if result.data:
                    deleted_count += len(result.data)
            logger.info(f"접수 문서 일괄 삭제 완료: {deleted_count}개")
            return deleted_count
        except Exception as e:
            logger.error(f"접수 문서 일괄 삭제 실패: {e}")
            return 0
    
    def card_exists(self, title: str) -> bool:
        """업무카드 존재 여부 확인"""
        try:
            result = self.client.table('task_card_mappings').select('id').eq('title', title).execute()
            return len(result.data) > 0
        except Exception as e:
            logger.error(f"업무카드 존재 확인 실패: {e}")
            return False
    
    def reception_exists(self, title: str) -> bool:
        """접수 문서 존재 여부 확인"""
        try:
            result = self.client.table('reception_mappings').select('id').eq('title', title).execute()
            return len(result.data) > 0
        except Exception as e:
            logger.error(f"접수 문서 존재 확인 실패: {e}")
            return False
    
    def delete_card_by_title(self, title: str) -> bool:
        """제목으로 업무카드 삭제"""
        try:
            result = self.client.table('task_card_mappings').delete().eq('title', title).execute()
            success = len(result.data) > 0
            if success:
                logger.info(f"업무카드 삭제 완료: {title}")
            return success
        except Exception as e:
            logger.error(f"업무카드 삭제 실패: {e}")
            return False
    
    def delete_reception_by_title(self, title: str) -> bool:
        """제목으로 접수 문서 삭제"""
        try:
            result = self.client.table('reception_mappings').delete().eq('title', title).execute()
            success = len(result.data) > 0
            if success:
                logger.info(f"접수 문서 삭제 완료: {title}")
            return success
        except Exception as e:
            logger.error(f"접수 문서 삭제 실패: {e}")
            return False
    
    def delete_all_cards(self) -> int:
        """모든 업무카드 삭제"""
        try:
            result = self.client.table('task_card_mappings').delete().neq('id', '').execute()
            deleted_count = len(result.data) if result.data else 0
            logger.warning(f"모든 업무카드 삭제 완료: {deleted_count}개")
            return deleted_count
        except Exception as e:
            logger.error(f"모든 업무카드 삭제 실패: {e}")
            return 0
    
    def delete_all_receptions(self) -> int:
        """모든 접수 문서 삭제"""
        try:
            result = self.client.table('reception_mappings').delete().neq('id', '').execute()
            deleted_count = len(result.data) if result.data else 0
            logger.warning(f"모든 접수 문서 삭제 완료: {deleted_count}개")
            return deleted_count
        except Exception as e:
            logger.error(f"모든 접수 문서 삭제 실패: {e}")
            return 0