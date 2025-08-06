from typing import Any
from datetime import datetime
import os

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings
from langchain.storage import LocalFileStore
from langchain.embeddings import CacheBackedEmbeddings
import chromadb.errors

from utils.id_generator import generate_document_id, generate_cache_key
from utils.error_handler import setup_logger, safe_execute


class ChromaService:
    def __init__(self, ollama_base_url: str, ollama_model: str, chroma_persist_dir: str = "./chroma_db", collection_name: str = "documents"):
        self.logger = setup_logger(__name__)
        self.collection_name = collection_name
        self.chroma_persist_dir = chroma_persist_dir
        
        # Chroma 데이터베이스 디렉토리 생성
        os.makedirs(chroma_persist_dir, exist_ok=True)
        
        # 캐시 설정
        fs = LocalFileStore(root_path="./.cache/")
        underlying_embeddings = OllamaEmbeddings(
            base_url=ollama_base_url,
            model=ollama_model
        )
        self.embeddings = CacheBackedEmbeddings.from_bytes_store(
            underlying_embeddings, fs, key_encoder=generate_cache_key
        )
        
        # Chroma 벡터 스토어 초기화
        self.vector_store = Chroma(
            collection_name=self.collection_name,
            embedding_function=self.embeddings,
            persist_directory=self.chroma_persist_dir,
        )

    def _add_document_with_dimension_recovery(self, document: Document, doc_id: str) -> bool:
        """
        차원 불일치 복구 기능이 있는 문서 추가 헬퍼 메서드
        """
        try:
            # 기존 문서가 있는지 확인하고 있으면 삭제
            document_type = document.metadata.get('type')
            title = document.metadata.get('title')
            
            existing_docs = self.vector_store.get(
                where={"$and": [{"title": title}, {"type": document_type}]}
            )
            if existing_docs['ids']:
                self.vector_store.delete(ids=existing_docs['ids'])
            
            # 새 문서 추가
            self.vector_store.add_documents([document], ids=[doc_id])
            return True
            
        except (ValueError, chromadb.errors.InvalidArgumentError) as e:
            # 차원 불일치 오류인지 확인
            if "dimension" in str(e).lower():
                self.logger.info("차원 불일치 오류 발생, 컬렉션을 재생성합니다.")
                if self._handle_dimension_mismatch():
                    # 재생성 후 다시 시도
                    self.vector_store.add_documents([document], ids=[doc_id])
                    return True
            # 다른 오류는 다시 발생시킴
            raise e
        except Exception as e:
            # 예상하지 못한 오류 처리
            self.logger.error("문서 업로드 중 예상치 못한 오류: %s", str(e))
            raise e

    def _handle_dimension_mismatch(self):
        """
        차원 불일치 문제가 발생했을 때 컬렉션을 재생성합니다.
        """
        try:
            test_embedding = self.embeddings.embed_query("test")
            current_dimension = len(test_embedding)
            
            self.logger.warning("임베딩 차원 불일치 감지. 새로운 컬렉션을 생성합니다 (%d차원)", current_dimension)
            
            # 기존 컬렉션 삭제
            try:
                import chromadb
                client = chromadb.PersistentClient(path=self.chroma_persist_dir)
                client.delete_collection(name=self.collection_name)
                self.logger.info("기존 컬렉션 '%s' 삭제 완료", self.collection_name)
            except Exception as delete_error:
                self.logger.warning("기존 컬렉션 삭제 실패: %s", delete_error)
            
            # 새 벡터 스토어 생성
            self.vector_store = Chroma(
                collection_name=self.collection_name,
                embedding_function=self.embeddings,
                persist_directory=self.chroma_persist_dir,
            )
            self.logger.info("새로운 벡터 데이터베이스 생성 완료")
            return True
            
        except Exception as e:
            self.logger.error("차원 불일치 처리 실패: %s", e)
            return False

    def upsert_card_embedding(self, title: str, task_title: str):
        """
        과제 카드 제목을 임베딩으로 변환하여 벡터 데이터베이스에 저장합니다.
        기존에 동일한 title이 존재하면 갱신합니다.
        """
        doc_id = generate_document_id(title)
        document = Document(
            page_content=title, 
            metadata={
                'title': title,
                'taskTitle': task_title,
                'type': 'card',
                'registered_at': datetime.now().isoformat()
            }
        )

        success = safe_execute(
            lambda: self._add_document_with_dimension_recovery(document, doc_id),
            default_return=False,
            logger=self.logger,
            error_message=f"과제 카드 업로드 실패: {title}"
        )

        if success:
            self.logger.info("과제 카드 '%s' (taskTitle: '%s')를 성공적으로 업로드/갱신했습니다.", title, task_title)
        else:
            self.logger.error("과제 카드 '%s' 업로드에 실패했습니다.", title)

    def retrieve_card_by_title(self, title: str):
        """
        주어진 title과 정확히 일치하는 과제 카드를 Chroma에서 검색합니다.
        """
        try:
            results = self.vector_store.get(
                where={"$and": [{"title": title}, {"type": "card"}]}
            )
            
            if results['metadatas']:
                return results['metadatas'][0].get('taskTitle')
            
            return None
        except Exception as e:
            self.logger.error("과제 카드 검색 실패: %s", e)
            return None

    def recommend_cards(self, title: str, count: int = 10):
        """
        임베딩 기반 의미적 유사도를 통해 입력된 제목과 유사한 과제 카드를 추천합니다.
        """
        try:
            # 벡터 유사도 검색
            results = self.vector_store.similarity_search_with_score(
                title, 
                k=count,
                filter={"type": "card"}
            )
            
            recommended_task_titles = []
            seen_task_titles = set()
            
            for doc, score in results:
                metadata = doc.metadata
                task_title = metadata.get('taskTitle', metadata.get('title'))
                if task_title and task_title not in seen_task_titles:
                    recommended_task_titles.append(task_title)
                    seen_task_titles.add(task_title)
            
            return recommended_task_titles
        except Exception as e:
            self.logger.error("과제 카드 추천 실패: %s", e)
            return []

    def upsert_reception_embedding(self, title: str, approval: str, share: Any):
        """
        접수 문서 정보를 임베딩으로 변환하여 벡터 데이터베이스에 저장합니다.
        """
        doc_id = generate_document_id(title)
        metadata = {
            'title': title, 
            'approval': approval, 
            'share': share,
            'type': 'reception',
            'registered_at': datetime.now().isoformat()
        }
        document = Document(page_content=title, metadata=metadata)

        success = safe_execute(
            lambda: self._add_document_with_dimension_recovery(document, doc_id),
            default_return=False,
            logger=self.logger,
            error_message=f"접수 정보 업로드 실패: {title}"
        )

        if success:
            self.logger.info("접수 정보 '%s' (담당: '%s')를 성공적으로 업로드/갱신했습니다.", title, approval)
        else:
            self.logger.error("접수 정보 '%s' 업로드에 실패했습니다.", title)

    def retrieve_reception_by_title(self, title: str):
        """
        주어진 title과 정확히 일치하는 접수 정보를 Chroma에서 검색합니다.
        """
        try:
            results = self.vector_store.get(
                where={"$and": [{"title": title}, {"type": "reception"}]}
            )
            
            if results['metadatas']:
                metadata = results['metadatas'][0]
                return metadata.get('approval'), metadata.get('share')
            
            return None, None
        except Exception as e:
            self.logger.error("접수 정보 검색 실패: %s", e)
            return None, None

    def recommend_reception(self, title: str, count: int = 5):
        """
        임베딩 기반 의미적 유사도를 통해 입력된 제목과 유사한 접수 정보를 추천합니다.
        """
        try:
            results = self.vector_store.similarity_search_with_score(
                title, 
                k=count,
                filter={"type": "reception"}
            )
            
            recommendations = []
            seen_approvals = set()
            
            for doc, score in results:
                metadata = doc.metadata
                approval = metadata.get('approval')
                if approval and approval not in seen_approvals:
                    recommendations.append({
                        'approval': approval,
                        'share': metadata.get('share')
                    })
                    seen_approvals.add(approval)
            
            return recommendations
        except Exception as e:
            self.logger.error("접수 정보 추천 실패: %s", e)
            return []

    def delete_card_by_title(self, title: str):
        """
        주어진 title과 일치하는 과제 카드를 삭제합니다.
        """
        def delete_operation():
            try:
                results = self.vector_store.get(
                    where={"$and": [{"title": title}, {"type": "card"}]}
                )
                
                if results['ids']:
                    self.vector_store.delete(ids=results['ids'])
                    return len(results['ids']) > 0
                return False
            except Exception:
                return False

        success = safe_execute(
            delete_operation,
            default_return=False,
            logger=self.logger,
            error_message=f"과제 카드 삭제 실패: {title}"
        )

        if success:
            self.logger.info("과제 카드 '%s'를 성공적으로 삭제했습니다.", title)
        else:
            self.logger.error("과제 카드 '%s' 삭제에 실패했습니다.", title)

        return success

    def delete_reception_by_title(self, title: str):
        """
        주어진 title과 일치하는 접수 문서를 삭제합니다.
        """
        def delete_operation():
            try:
                results = self.vector_store.get(
                    where={"$and": [{"title": title}, {"type": "reception"}]}
                )
                
                if results['ids']:
                    self.vector_store.delete(ids=results['ids'])
                    return len(results['ids']) > 0
                return False
            except Exception:
                return False

        success = safe_execute(
            delete_operation,
            default_return=False,
            logger=self.logger,
            error_message=f"접수 문서 삭제 실패: {title}"
        )

        if success:
            self.logger.info("접수 문서 '%s'를 성공적으로 삭제했습니다.", title)
        else:
            self.logger.error("접수 문서 '%s' 삭제에 실패했습니다.", title)

        return success

    def card_exists(self, title: str) -> bool:
        """
        주어진 title의 과제 카드가 존재하는지 확인합니다.
        """
        def check_operation():
            try:
                results = self.vector_store.get(
                    where={"$and": [{"title": title}, {"type": "card"}]}
                )
                return len(results['ids']) > 0
            except Exception:
                return False

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
            try:
                results = self.vector_store.get(
                    where={"$and": [{"title": title}, {"type": "reception"}]}
                )
                return len(results['ids']) > 0
            except Exception:
                return False

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
            try:
                results = self.vector_store.get(
                    where={"type": "card"}
                )
                
                cards = []
                for metadata in results['metadatas']:
                    cards.append((
                        metadata.get('title', ''),
                        metadata.get('taskTitle', ''),
                        metadata.get('registered_at', 'N/A')
                    ))
                return cards
            except Exception:
                return []

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
            try:
                results = self.vector_store.get(
                    where={"type": "reception"}
                )
                
                receptions = []
                for metadata in results['metadatas']:
                    receptions.append((
                        metadata.get('title', ''),
                        metadata.get('approval', ''),
                        metadata.get('share', ''),
                        metadata.get('registered_at', 'N/A')
                    ))
                return receptions
            except Exception:
                return []

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
        if not titles:
            return 0

        def bulk_delete_operation():
            try:
                deleted_count = 0
                for title in titles:
                    results = self.vector_store.get(
                        where={"$and": [{"title": title}, {"type": "card"}]}
                    )
                    
                    if results['ids']:
                        self.vector_store.delete(ids=results['ids'])
                        deleted_count += len(results['ids'])
                
                return deleted_count
            except Exception:
                return 0

        deleted_count = safe_execute(
            bulk_delete_operation,
            default_return=0,
            logger=self.logger,
            error_message="과제 카드 일괄 삭제 실패"
        )

        self.logger.info("총 %s개의 과제 카드가 삭제되었습니다.", deleted_count)
        return deleted_count

    def bulk_delete_receptions(self, titles: list):
        """
        여러 접수 문서를 일괄 삭제합니다.
        """
        if not titles:
            return 0

        def bulk_delete_operation():
            try:
                deleted_count = 0
                for title in titles:
                    results = self.vector_store.get(
                        where={"$and": [{"title": title}, {"type": "reception"}]}
                    )
                    
                    if results['ids']:
                        self.vector_store.delete(ids=results['ids'])
                        deleted_count += len(results['ids'])
                
                return deleted_count
            except Exception:
                return 0

        deleted_count = safe_execute(
            bulk_delete_operation,
            default_return=0,
            logger=self.logger,
            error_message="접수 문서 일괄 삭제 실패"
        )

        self.logger.info("총 %s개의 접수 문서가 삭제되었습니다.", deleted_count)
        return deleted_count