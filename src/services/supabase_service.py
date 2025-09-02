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
        logger.info("Supabase 클라이언트 초기화 완료")
    
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
    
    # 유틸리티 메서드
    def get_connection_status(self) -> Dict[str, Any]:
        """연결 상태 확인"""
        try:
            # 간단한 쿼리로 연결 테스트
            result = self.client.table('reception_documents').select('count', count='exact').limit(0).execute()
            return {
                'connected': True,
                'url': self.url,
                'tables': ['reception_documents', 'task_cards', 'document_embeddings']
            }
        except Exception as e:
            return {
                'connected': False,
                'error': str(e)
            }
    
    def clear_all_data(self) -> bool:
        """모든 데이터 삭제 (개발/테스트용)"""
        try:
            self.client.table('document_embeddings').delete().neq('id', '').execute()
            self.client.table('reception_documents').delete().neq('id', '').execute()
            self.client.table('task_cards').delete().neq('id', '').execute()
            logger.warning("모든 데이터 삭제 완료")
            return True
        except Exception as e:
            logger.error(f"데이터 삭제 실패: {e}")
            return False