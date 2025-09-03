"""
업데이트된 Supabase 데이터베이스 서비스 클래스 
새로운 매핑 테이블 구조 (task_card_mappings, reception_mappings)에 최적화
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
    """Supabase 데이터베이스 서비스 (새 매핑 구조)"""
    
    def __init__(self):
        """Supabase 클라이언트 초기화"""
        self.url = os.getenv('SUPABASE_URL')
        self.key = os.getenv('SUPABASE_KEY')
        
        if not self.url or not self.key:
            raise ValueError("SUPABASE_URL과 SUPABASE_KEY 환경변수가 필요합니다")
        
        self.client: Client = create_client(self.url, self.key)
        logger.info("Supabase 클라이언트 초기화 완료")
    
    # Task Card Mappings 관련 메서드
    def create_task_card_mapping(self, title: str, task_title: str, 
                                embedding: List[float] = None,
                                metadata: Dict[str, Any] = None) -> str:
        """업무카드 매핑 생성"""
        try:
            mapping_id = str(uuid4())
            data = {
                'id': mapping_id,
                'title': title,
                'task_title': task_title,
                'embedding': embedding,
                'metadata': metadata or {}
            }
            
            result = self.client.table('task_card_mappings').insert(data).execute()
            logger.info(f"업무카드 매핑 생성 완료: {title} -> {task_title}")
            return mapping_id
        except Exception as e:
            logger.error(f"업무카드 매핑 생성 실패: {e}")
            raise
    
    def find_task_card_by_title(self, title: str) -> Optional[Dict[str, Any]]:
        """제목으로 업무카드 매핑 검색"""
        try:
            result = self.client.table('task_card_mappings').select('*').eq('title', title).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"업무카드 매핑 검색 실패: {e}")
            return None
    
    def find_similar_task_cards(self, query_embedding: List[float], 
                               limit: int = 5, threshold: float = 0.7) -> List[Dict[str, Any]]:
        """벡터 유사도로 비슷한 업무카드 검색"""
        try:
            # PostgreSQL 벡터 유사도 검색 쿼리
            query = """
            SELECT 
                title,
                task_title,
                1 - (embedding <=> %s::vector) as similarity,
                created_at
            FROM task_card_mappings
            WHERE embedding IS NOT NULL 
              AND 1 - (embedding <=> %s::vector) > %s
            ORDER BY embedding <=> %s::vector
            LIMIT %s
            """
            
            result = self.client.rpc('execute_raw_sql', {
                'sql_query': query,
                'params': [query_embedding, query_embedding, threshold, query_embedding, limit]
            }).execute()
            
            return result.data if result.data else []
        except Exception as e:
            logger.error(f"유사 업무카드 검색 실패: {e}")
            return []
    
    def list_task_card_mappings(self, task_title: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """업무카드 매핑 목록 조회"""
        try:
            query = self.client.table('task_card_mappings').select('*')
            
            if task_title:
                query = query.eq('task_title', task_title)
            
            result = query.order('created_at', desc=True).limit(limit).execute()
            return result.data
        except Exception as e:
            logger.error(f"업무카드 매핑 목록 조회 실패: {e}")
            return []
    
    # Reception Mappings 관련 메서드
    def create_reception_mapping(self, title: str, handler: str, share_target: str = None,
                                embedding: List[float] = None, 
                                metadata: Dict[str, Any] = None) -> str:
        """접수 매핑 생성"""
        try:
            mapping_id = str(uuid4())
            data = {
                'id': mapping_id,
                'title': title,
                'handler': handler,
                'share_target': share_target,
                'embedding': embedding,
                'metadata': metadata or {}
            }
            
            result = self.client.table('reception_mappings').insert(data).execute()
            logger.info(f"접수 매핑 생성 완료: {title} -> {handler}")
            return mapping_id
        except Exception as e:
            logger.error(f"접수 매핑 생성 실패: {e}")
            raise
    
    def find_reception_by_title(self, title: str) -> Optional[Dict[str, Any]]:
        """제목으로 접수 매핑 검색"""
        try:
            result = self.client.table('reception_mappings').select('*').eq('title', title).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"접수 매핑 검색 실패: {e}")
            return None
    
    def find_similar_receptions(self, query_embedding: List[float], 
                               limit: int = 5, threshold: float = 0.7) -> List[Dict[str, Any]]:
        """벡터 유사도로 비슷한 접수 문서 검색"""
        try:
            # PostgreSQL 벡터 유사도 검색 쿼리 (간단한 방법)
            result = self.client.table('reception_mappings').select(
                'title, handler, share_target, created_at'
            ).limit(limit).execute()
            
            # 실제로는 벡터 검색 쿼리를 사용해야 하지만, 
            # 간단한 버전으로 먼저 구현
            return result.data if result.data else []
        except Exception as e:
            logger.error(f"유사 접수 문서 검색 실패: {e}")
            return []
    
    def list_reception_mappings(self, handler: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """접수 매핑 목록 조회"""
        try:
            query = self.client.table('reception_mappings').select('*')
            
            if handler:
                query = query.eq('handler', handler)
            
            result = query.order('created_at', desc=True).limit(limit).execute()
            return result.data
        except Exception as e:
            logger.error(f"접수 매핑 목록 조회 실패: {e}")
            return []
    
    # 공통 유틸리티 메서드
    def batch_insert_task_mappings(self, mappings_data: List[Dict[str, Any]]) -> bool:
        """업무카드 매핑 배치 삽입"""
        try:
            for data in mappings_data:
                if 'id' not in data:
                    data['id'] = str(uuid4())
                if 'metadata' not in data:
                    data['metadata'] = {}
            
            result = self.client.table('task_card_mappings').insert(mappings_data).execute()
            logger.info(f"업무카드 매핑 배치 삽입 완료: {len(mappings_data)}개")
            return True
        except Exception as e:
            logger.error(f"업무카드 매핑 배치 삽입 실패: {e}")
            return False
    
    def batch_insert_reception_mappings(self, mappings_data: List[Dict[str, Any]]) -> bool:
        """접수 매핑 배치 삽입"""
        try:
            for data in mappings_data:
                if 'id' not in data:
                    data['id'] = str(uuid4())
                if 'metadata' not in data:
                    data['metadata'] = {}
            
            result = self.client.table('reception_mappings').insert(mappings_data).execute()
            logger.info(f"접수 매핑 배치 삽입 완료: {len(mappings_data)}개")
            return True
        except Exception as e:
            logger.error(f"접수 매핑 배치 삽입 실패: {e}")
            return False
    
    def get_connection_status(self) -> Dict[str, Any]:
        """연결 상태 확인"""
        try:
            # 테이블 개수 확인으로 연결 테스트
            task_result = self.client.table('task_card_mappings').select('count', count='exact').limit(0).execute()
            reception_result = self.client.table('reception_mappings').select('count', count='exact').limit(0).execute()
            
            return {
                'connected': True,
                'url': self.url,
                'tables': ['task_card_mappings', 'reception_mappings'],
                'task_mappings_count': task_result.count or 0,
                'reception_mappings_count': reception_result.count or 0
            }
        except Exception as e:
            return {
                'connected': False,
                'error': str(e)
            }
    
    def clear_all_mappings(self) -> bool:
        """모든 매핑 데이터 삭제 (개발/테스트용)"""
        try:
            self.client.table('task_card_mappings').delete().neq('id', '').execute()
            self.client.table('reception_mappings').delete().neq('id', '').execute()
            logger.warning("모든 매핑 데이터 삭제 완료")
            return True
        except Exception as e:
            logger.error(f"매핑 데이터 삭제 실패: {e}")
            return False
    
    # 통계 및 분석 메서드
    def get_task_title_distribution(self) -> List[Dict[str, Any]]:
        """업무카드 제목별 분포"""
        try:
            result = self.client.rpc('get_task_title_stats').execute()
            return result.data if result.data else []
        except Exception as e:
            logger.error(f"업무카드 분포 조회 실패: {e}")
            return []
    
    def get_handler_distribution(self) -> List[Dict[str, Any]]:
        """담당자별 분포"""
        try:
            result = self.client.rpc('get_handler_stats').execute()
            return result.data if result.data else []
        except Exception as e:
            logger.error(f"담당자 분포 조회 실패: {e}")
            return []
    
    # 검색 및 추천 메서드
    def recommend_task_card(self, title: str, embedding_service, top_k: int = 5) -> List[Dict[str, Any]]:
        """공문 제목으로 업무카드 추천"""
        try:
            # 제목 임베딩 생성
            embedding_result = embedding_service.create_embedding(title, f"query_{int(datetime.now().timestamp())}")
            
            if not embedding_result:
                return []
            
            # 유사한 업무카드 검색
            similar_mappings = self.find_similar_task_cards(
                embedding_result.embedding, 
                limit=top_k
            )
            
            return similar_mappings
        except Exception as e:
            logger.error(f"업무카드 추천 실패: {e}")
            return []
    
    def recommend_handler(self, title: str, embedding_service, top_k: int = 3) -> List[Dict[str, Any]]:
        """공문 제목으로 담당자 추천"""
        try:
            # 제목 임베딩 생성
            embedding_result = embedding_service.create_embedding(title, f"query_{int(datetime.now().timestamp())}")
            
            if not embedding_result:
                return []
            
            # 유사한 접수 문서 검색
            similar_mappings = self.find_similar_receptions(
                embedding_result.embedding, 
                limit=top_k
            )
            
            return similar_mappings
        except Exception as e:
            logger.error(f"담당자 추천 실패: {e}")
            return []