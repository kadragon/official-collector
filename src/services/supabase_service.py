import os
import sys
from pathlib import Path
from typing import Any

from langchain_community.vectorstores import SupabaseVectorStore
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain.storage import LocalFileStore
from langchain.embeddings import CacheBackedEmbeddings
from supabase.client import Client, create_client

from utils.id_generator import generate_document_id, generate_cache_key
from utils.error_handler import setup_logger, safe_execute


class SupabaseService:
    def __init__(self, openai_api_key: str, supabase_url: str, supabase_key: str, table_name: str = "documents", query_name: str = "match_documents"):
        self.logger = setup_logger(__name__)
        self.supabase: Client = create_client(supabase_url, supabase_key)

        # 캐시 설정
        fs = LocalFileStore(root_path="./.cache/")
        underlying_embeddings = OpenAIEmbeddings(
            openai_api_key=openai_api_key, model="text-embedding-3-small"
        )
        self.embeddings = CacheBackedEmbeddings.from_bytes_store(
            underlying_embeddings, fs, key_encoder=generate_cache_key
        )

        self.vector_store = SupabaseVectorStore(
            client=self.supabase,
            embedding=self.embeddings,
            table_name=table_name,
            query_name=query_name,
        )

    def upsert_card_embedding(self, title: str, task_title: str):
        """
        과제 카드 제목을 임베딩으로 변환하여 벡터 데이터베이스에 저장합니다.
        기존에 동일한 title이 존재하면 갱신합니다.
        """
        doc_id = generate_document_id(title)
        document = Document(page_content=title, metadata={
                            'title': title, 'taskTitle': task_title})
        
        def upload_document():
            self.vector_store.add_documents([document], ids=[doc_id])
            return True
        
        success = safe_execute(
            upload_document,
            default_return=False,
            logger=self.logger,
            error_message=f"과제 카드 업로드 실패: {title}"
        )
        
        if success:
            self.logger.info(f"과제 카드 '{title}' (taskTitle: '{task_title}')를 성공적으로 업로드/갱신했습니다.")
        else:
            self.logger.error(f"과제 카드 '{title}' 업로드에 실패했습니다.")

    def retrieve_card_by_title(self, title: str):
        """
        주어진 title과 정확히 일치하는 과제 카드를 Supabase에서 검색합니다.
        임베딩을 생성하지 않고 메타데이터를 직접 쿼리하여 불필요한 임베딩 호출을 방지합니다.
        """
        response = self.supabase.table(self.vector_store.table_name).select(
            "metadata").eq('metadata->>title', title).limit(1).execute()
        if response.data:
            metadata = response.data[0].get('metadata', {})
            return metadata.get('taskTitle')
        return None

    def recommend_cards(self, title: str, count: int = 10):
        """
        임베딩 기반 의미적 유사도를 통해 입력된 제목과 유사한 과제 카드를 추천합니다.
        벡터 유사도 순으로 정렬하여 중복을 제거한 taskTitle을 반환합니다.
        """
        embedding = self.embeddings.embed_query(title)

        # Supabase 벡터 매칭 함수를 통한 의미적 유사도 검색
        response = self.supabase.rpc(
            'match_documents',
            {
                'query_embedding': embedding,
                'match_count': count,
                'filter': {}  # 현재 필터 미적용
            }
        ).execute()

        recommended_task_titles = []
        seen_task_titles = set()

        if response.data:
            for card in response.data:
                metadata = card.get('metadata', {})
                task_title = metadata.get('taskTitle', metadata.get('title'))
                if task_title not in seen_task_titles:
                    recommended_task_titles.append(task_title)
                    seen_task_titles.add(task_title)

        return recommended_task_titles

    def upsert_reception_embedding(self, title: str, approval: str, share: Any):
        """
        접수 문서 정보를 임베딩으로 변환하여 벡터 데이터베이스에 저장합니다.
        향후 유사한 접수 문서에 대한 자동 담당자 배정을 위해 사용됩니다.
        """
        doc_id = generate_document_id(title)
        metadata = {'title': title, 'approval': approval, 'share': share}
        document = Document(page_content=title, metadata=metadata)
        
        def upload_reception():
            self.vector_store.add_documents([document], ids=[doc_id])
            return True
        
        success = safe_execute(
            upload_reception,
            default_return=False,
            logger=self.logger,
            error_message=f"접수 정보 업로드 실패: {title}"
        )
        
        if success:
            self.logger.info(f"접수 정보 '{title}' (담당: '{approval}')를 성공적으로 업로드/갱신했습니다.")
        else:
            self.logger.error(f"접수 정보 '{title}' 업로드에 실패했습니다.")

    def retrieve_reception_by_title(self, title: str):
        """
        주어진 title과 정확히 일치하는 접수 정보를 Supabase에서 검색합니다.
        """
        response = self.supabase.table(self.vector_store.table_name).select(
            "metadata").eq('metadata->>title', title).limit(1).execute()
        if response.data:
            metadata = response.data[0].get('metadata', {})
            return metadata.get('approval'), metadata.get('share')
        return None, None

    def recommend_reception(self, title: str, count: int = 5):
        """
        임베딩 기반 의미적 유사도를 통해 입력된 제목과 유사한 접수 정보를 추천합니다.
        벡터 유사도 기반으로 가장 적절한 담당자와 공람 대상자를 찾습니다.
        """
        embedding = self.embeddings.embed_query(title)

        # Supabase 벡터 매칭 함수를 통한 접수 문서 의미적 유사도 검색
        response = self.supabase.rpc(
            'match_reception_documents',
            {
                'query_embedding': embedding,
                'match_count': count,
                'filter': {}  # 현재 필터 미적용
            }
        ).execute()

        recommendations = []
        seen_approvals = set()

        if response.data:
            for doc in response.data:
                metadata = doc.get('metadata', {})
                approval = metadata.get('approval')
                if approval and approval not in seen_approvals:
                    recommendations.append({
                        'approval': approval,
                        'share': metadata.get('share')
                    })
                    seen_approvals.add(approval)

        return recommendations

    def delete_card_by_title(self, title: str):
        """
        주어진 title과 일치하는 과제 카드를 삭제합니다.
        """
        def delete_operation():
            response = self.supabase.table(self.vector_store.table_name).delete().eq('metadata->>title', title).execute()
            return len(response.data) > 0
        
        success = safe_execute(
            delete_operation,
            default_return=False,
            logger=self.logger,
            error_message=f"과제 카드 삭제 실패: {title}"
        )
        
        if success:
            self.logger.info(f"과제 카드 '{title}'를 성공적으로 삭제했습니다.")
        else:
            self.logger.error(f"과제 카드 '{title}' 삭제에 실패했습니다.")
        
        return success

    def delete_reception_by_title(self, title: str):
        """
        주어진 title과 일치하는 접수 문서를 삭제합니다.
        """
        def delete_operation():
            response = self.supabase.table(self.vector_store.table_name).delete().eq('metadata->>title', title).execute()
            return len(response.data) > 0
        
        success = safe_execute(
            delete_operation,
            default_return=False,
            logger=self.logger,
            error_message=f"접수 문서 삭제 실패: {title}"
        )
        
        if success:
            self.logger.info(f"접수 문서 '{title}'를 성공적으로 삭제했습니다.")
        else:
            self.logger.error(f"접수 문서 '{title}' 삭제에 실패했습니다.")
        
        return success

    def card_exists(self, title: str) -> bool:
        """
        주어진 title의 과제 카드가 존재하는지 확인합니다.
        """
        def check_operation():
            response = self.supabase.table(self.vector_store.table_name).select("id").eq('metadata->>title', title).limit(1).execute()
            return len(response.data) > 0
        
        exists = safe_execute(
            check_operation,
            default_return=False,
            logger=self.logger,
            error_message=f"과제 카드 존재 확인 실패: {title}"
        )
        
        return exists

    def reception_exists(self, title: str) -> bool:
        """
        주어진 title의 접수 문서가 존재하는지 확인합니다.
        """
        def check_operation():
            response = self.supabase.table(self.vector_store.table_name).select("id").eq('metadata->>title', title).limit(1).execute()
            return len(response.data) > 0
        
        exists = safe_execute(
            check_operation,
            default_return=False,
            logger=self.logger,
            error_message=f"접수 문서 존재 확인 실패: {title}"
        )
        
        return exists

    def list_all_cards(self):
        """
        저장된 모든 과제 카드 목록을 조회합니다.
        """
        def list_operation():
            response = self.supabase.table(self.vector_store.table_name).select("metadata").execute()
            return [(item['metadata']['title'], item['metadata'].get('taskTitle', '')) for item in response.data]
        
        cards = safe_execute(
            list_operation,
            default_return=[],
            logger=self.logger,
            error_message="과제 카드 목록 조회 실패"
        )
        
        return cards

    def list_all_receptions(self):
        """
        저장된 모든 접수 문서 목록을 조회합니다.
        """
        def list_operation():
            response = self.supabase.table(self.vector_store.table_name).select("metadata").execute()
            return [(item['metadata']['title'], item['metadata'].get('approval', ''), item['metadata'].get('share', '')) for item in response.data]
        
        receptions = safe_execute(
            list_operation,
            default_return=[],
            logger=self.logger,
            error_message="접수 문서 목록 조회 실패"
        )
        
        return receptions

    def bulk_delete_cards(self, titles: list):
        """
        여러 과제 카드를 일괄 삭제합니다.
        """
        deleted_count = 0
        for title in titles:
            if self.delete_card_by_title(title):
                deleted_count += 1
        
        self.logger.info(f"총 {deleted_count}개의 과제 카드가 삭제되었습니다.")
        return deleted_count

    def bulk_delete_receptions(self, titles: list):
        """
        여러 접수 문서를 일괄 삭제합니다.
        """
        deleted_count = 0
        for title in titles:
            if self.delete_reception_by_title(title):
                deleted_count += 1
        
        self.logger.info(f"총 {deleted_count}개의 접수 문서가 삭제되었습니다.")
        return deleted_count
