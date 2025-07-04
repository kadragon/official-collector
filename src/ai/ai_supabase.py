import os
import sys
from pathlib import Path
import uuid

from langchain_community.vectorstores import SupabaseVectorStore
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain.storage import FileSystemStore
from langchain.embeddings import CacheBackedEmbeddings
from supabase.client import Client, create_client

# config.config는 main.py에서 로드되므로 여기서는 직접 임포트하지 않음
# 대신 필요한 환경 변수는 클래스 초기화 시 전달받거나 os.environ에서 직접 접근

class SupabaseManager:
    def __init__(self, openai_api_key: str, supabase_url: str, supabase_key: str, table_name: str = "documents", query_name: str = "match_documents"):
        self.supabase: Client = create_client(supabase_url, supabase_key)
        
        # 캐시 설정
        fs = FileSystemStore(root_path="./.cache/")
        underlying_embeddings = OpenAIEmbeddings(
            openai_api_key=openai_api_key, model="text-embedding-3-small"
        )
        self.embeddings = CacheBackedEmbeddings.from_bytes_store(
            underlying_embeddings, fs, namespace=underlying_embeddings.model
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

    def recommend_cards(self, title: str, count: int = 5):
        """
        입력된 제목과 유사한 과제 카드를 추천하고 taskTitle을 반환합니다.
        """
        similar_cards = self.vector_store.similarity_search(query=title, k=count)
        return [card.metadata.get('taskTitle', card.page_content) for card in similar_cards]