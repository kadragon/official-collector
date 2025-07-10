import os
import sys
from pathlib import Path
import uuid
import hashlib
from typing import Any

from langchain_community.vectorstores import SupabaseVectorStore
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain.storage import LocalFileStore
from langchain.embeddings import CacheBackedEmbeddings
from supabase.client import Client, create_client

class SupabaseService:
    def __init__(self, openai_api_key: str, supabase_url: str, supabase_key: str, table_name: str = "documents", query_name: str = "match_documents"):
        self.supabase: Client = create_client(supabase_url, supabase_key)
        
        # 캐시 설정
        fs = LocalFileStore(root_path="./.cache/")
        underlying_embeddings = OpenAIEmbeddings(
            openai_api_key=openai_api_key, model="text-embedding-3-small"
        )
        self.embeddings = CacheBackedEmbeddings.from_bytes_store(
            underlying_embeddings, fs, key_encoder=lambda x: hashlib.sha256(x.encode('utf-8')).hexdigest()
        )

        self.vector_store = SupabaseVectorStore(
            client=self.supabase,
            embedding=self.embeddings,
            table_name=table_name,
            query_name=query_name,
        )

    def upsert_card_embedding(self, title: str, task_title: str):
        """
        과제 카드를 벡터로 변환하여 Supabase에 업로드하거나 갱신합니다.
        동일한 title이 존재하면 갱신합니다.
        """
        doc_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, title)) # Consistent UUID from title
        document = Document(page_content=title, metadata={'title': title, 'taskTitle': task_title})
        self.vector_store.add_documents([document], ids=[doc_id])
        print(f"과제 카드 '{title}' (taskTitle: '{task_title}')를 성공적으로 업로드/갱신했습니다.")

    def retrieve_card_by_title(self, title: str):
        """
        주어진 title과 정확히 일치하는 과제 카드를 Supabase에서 검색합니다.
        임베딩을 생성하지 않고 메타데이터를 직접 쿼리하여 불필요한 임베딩 호출을 방지합니다.
        """
        response = self.supabase.table(self.vector_store.table_name).select("metadata").eq('metadata->>title', title).limit(1).execute()
        if response.data:
            metadata = response.data[0].get('metadata', {})
            return metadata.get('taskTitle')
        return None

    def recommend_cards(self, title: str, count: int = 10):
        """
        입력된 제목과 유사한 과제 카드를 추천하고, 연관도 순으로 중복을 제거한 taskTitle을 반환합니다.
        """
        embedding = self.embeddings.embed_query(title)

        # Directly call the Supabase RPC function for card recommendations
        response = self.supabase.rpc(
            'match_documents',
            {
                'query_embedding': embedding,
                'match_count': count,
                'filter': {} # No filter applied currently
            }
        ).execute()

        recommended_task_titles = []
        seen_task_titles = set()

        if response.data:
            for card in response.data:
                task_title = card.get('taskTitle', card.get('title'))
                if task_title not in seen_task_titles:
                    recommended_task_titles.append(task_title)
                    seen_task_titles.add(task_title)

        return recommended_task_titles

    def upsert_reception_embedding(self, title: str, approval: str, share: Any):
        """
        '접수' 정보를 벡터로 변환하여 Supabase에 업로드하거나 갱신합니다.
        """
        doc_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, title))
        metadata = {'title': title, 'approval': approval, 'share': share}
        document = Document(page_content=title, metadata=metadata)
        self.vector_store.add_documents([document], ids=[doc_id])
        print(f"접수 정보 '{title}' (담당: '{approval}')를 성공적으로 업로드/갱신했습니다.")

    def retrieve_reception_by_title(self, title: str):
        """
        주어진 title과 정확히 일치하는 접수 정보를 Supabase에서 검색합니다.
        """
        response = self.supabase.table(self.vector_store.table_name).select("metadata").eq('metadata->>title', title).limit(1).execute()
        if response.data:
            metadata = response.data[0].get('metadata', {})
            return metadata.get('approval'), metadata.get('share')
        return None, None

    def recommend_reception(self, title: str, count: int = 5):
        """
        입력된 제목과 유사한 접수 정보를 추천합니다.
        """
        embedding = self.embeddings.embed_query(title)
        
        # Directly call the Supabase RPC function
        response = self.supabase.rpc(
            'match_reception_documents',
            {
                'query_embedding': embedding,
                'match_count': count,
                'filter': {} # No filter applied currently
            }
        ).execute()

        recommendations = []
        seen_approvals = set()

        if response.data:
            for doc in response.data:
                approval = doc.get('approval')
                if approval and approval not in seen_approvals:
                    recommendations.append({
                        'approval': approval,
                        'share': doc.get('share')
                    })
                    seen_approvals.add(approval)
        
        return recommendations
