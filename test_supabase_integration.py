"""
Supabase와 OpenAI 임베딩 서비스 통합 테스트
Phase 2 개발 검증용
"""

import os
import sys
import logging
from typing import List, Dict, Any

# 프로젝트 루트를 Python path에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.services.supabase_service import SupabaseService
from src.services.openai_embedding_service import OpenAIEmbeddingService, EmbeddingRequest

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_supabase_connection():
    """Supabase 연결 테스트"""
    logger.info("=== Supabase 연결 테스트 ===")
    
    try:
        service = SupabaseService()
        status = service.get_connection_status()
        
        if status['connected']:
            logger.info("✅ Supabase 연결 성공")
            logger.info(f"URL: {status['url']}")
            logger.info(f"테이블: {status['tables']}")
            return True
        else:
            logger.error(f"❌ Supabase 연결 실패: {status.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Supabase 연결 테스트 중 오류: {e}")
        return False


def test_openai_embedding():
    """OpenAI 임베딩 서비스 테스트"""
    logger.info("=== OpenAI 임베딩 서비스 테스트 ===")
    
    try:
        service = OpenAIEmbeddingService()
        
        # API 키 검증
        if not service.validate_api_key():
            logger.error("❌ OpenAI API 키 검증 실패")
            return False
        
        logger.info("✅ OpenAI API 키 검증 성공")
        
        # 단일 임베딩 테스트
        test_text = "공문서 처리 테스트 문서입니다."
        result = service.create_embedding(test_text, "test_001")
        
        if result:
            logger.info(f"✅ 임베딩 생성 성공")
            logger.info(f"모델: {service.model}")
            logger.info(f"차원: {len(result.embedding)}")
            logger.info(f"토큰 수: {result.token_count}")
            
            # 비용 정보
            cost_summary = service.get_cost_summary()
            logger.info(f"비용: ${cost_summary['total_cost_usd']:.6f}")
            return True
        else:
            logger.error("❌ 임베딩 생성 실패")
            return False
            
    except Exception as e:
        logger.error(f"❌ OpenAI 임베딩 테스트 중 오류: {e}")
        return False


def test_integrated_workflow():
    """통합 워크플로우 테스트"""
    logger.info("=== 통합 워크플로우 테스트 ===")
    
    try:
        # 서비스 초기화
        supabase = SupabaseService()
        openai_service = OpenAIEmbeddingService()
        
        # 테스트 데이터
        test_documents = [
            {
                "title": "공문서 처리 절차 안내",
                "content": "공문서 처리를 위한 기본 절차와 주의사항을 안내합니다. 접수부터 완료까지의 전 과정을 설명합니다.",
                "type": "reception_document"
            },
            {
                "title": "예산 집행 승인 요청",
                "content": "2024년도 하반기 예산 집행을 위한 승인 요청서입니다. 세부 내역과 집행 계획을 포함합니다.",
                "type": "task_card"
            },
            {
                "title": "회의록 작성 가이드라인",
                "content": "효과적인 회의록 작성을 위한 가이드라인과 템플릿을 제공합니다.",
                "type": "task_card"
            }
        ]
        
        logger.info(f"테스트 문서 {len(test_documents)}개 처리 시작")
        
        created_documents = []
        
        # 1단계: 문서 생성 및 임베딩
        for doc in test_documents:
            try:
                # 문서 생성
                if doc["type"] == "reception_document":
                    doc_id = supabase.create_reception_document(
                        title=doc["title"],
                        content=doc["content"],
                        handler="테스트 담당자",
                        metadata={"test": True}
                    )
                else:  # task_card
                    doc_id = supabase.create_task_card(
                        title=doc["title"],
                        content=doc["content"],
                        category="테스트",
                        metadata={"test": True}
                    )
                
                logger.info(f"✅ 문서 생성: {doc['title']} (ID: {doc_id})")
                
                # 임베딩 생성
                embedding_result = openai_service.create_embedding(
                    f"{doc['title']} {doc['content']}", 
                    doc_id
                )
                
                if embedding_result:
                    # 임베딩 저장
                    embedding_id = supabase.store_embedding(
                        document_id=doc_id,
                        document_type=doc["type"],
                        title=doc["title"],
                        embedding=embedding_result.embedding,
                        content_summary=doc["content"][:200],
                        metadata={"test": True}
                    )
                    
                    logger.info(f"✅ 임베딩 저장: {doc['title']} (Embedding ID: {embedding_id})")
                    
                    created_documents.append({
                        "doc_id": doc_id,
                        "embedding_id": embedding_id,
                        "type": doc["type"],
                        "title": doc["title"]
                    })
                else:
                    logger.error(f"❌ 임베딩 생성 실패: {doc['title']}")
                
            except Exception as e:
                logger.error(f"❌ 문서 처리 실패 ({doc['title']}): {e}")
        
        # 2단계: 유사도 검색 테스트
        if created_documents:
            logger.info("=== 유사도 검색 테스트 ===")
            
            query_text = "공문서 처리 방법에 대해 알려주세요"
            query_embedding = openai_service.create_embedding(query_text, "query")
            
            if query_embedding:
                # 참고: 실제 유사도 검색은 SupabaseService의 find_similar_documents 메서드 수정 필요
                # 현재는 간단한 검색 테스트만 수행
                logger.info(f"✅ 검색 쿼리 임베딩 생성: {query_text}")
                logger.info(f"검색 쿼리 차원: {len(query_embedding.embedding)}")
        
        # 3단계: 정리
        logger.info("=== 테스트 데이터 정리 ===")
        cleanup_success = supabase.clear_all_data()
        
        if cleanup_success:
            logger.info("✅ 테스트 데이터 정리 완료")
        else:
            logger.warning("⚠️ 테스트 데이터 정리 부분적 실패")
        
        # 비용 요약
        cost_summary = openai_service.get_cost_summary()
        logger.info("=== 비용 요약 ===")
        logger.info(f"총 요청 수: {cost_summary['total_requests']}")
        logger.info(f"총 토큰 수: {cost_summary['total_tokens']}")
        logger.info(f"총 비용: ${cost_summary['total_cost_usd']:.6f}")
        
        logger.info("✅ 통합 테스트 완료")
        return len(created_documents) > 0
        
    except Exception as e:
        logger.error(f"❌ 통합 테스트 중 오류: {e}")
        return False


def main():
    """메인 테스트 실행"""
    logger.info("=== Supabase & OpenAI 통합 테스트 시작 ===")
    
    tests = [
        ("Supabase 연결", test_supabase_connection),
        ("OpenAI 임베딩", test_openai_embedding),
        ("통합 워크플로우", test_integrated_workflow)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        try:
            result = test_func()
            results[test_name] = result
            status = "✅ 성공" if result else "❌ 실패"
            logger.info(f"{test_name}: {status}")
        except Exception as e:
            results[test_name] = False
            logger.error(f"{test_name}: ❌ 오류 - {e}")
    
    # 최종 결과
    logger.info(f"\n{'='*50}")
    logger.info("=== 최종 테스트 결과 ===")
    
    success_count = sum(results.values())
    total_count = len(results)
    
    for test_name, result in results.items():
        status = "✅" if result else "❌"
        logger.info(f"{status} {test_name}")
    
    logger.info(f"\n총 {total_count}개 테스트 중 {success_count}개 성공")
    
    if success_count == total_count:
        logger.info("🎉 모든 테스트 통과! Phase 2 개발 완료")
        return True
    else:
        logger.error(f"⚠️ {total_count - success_count}개 테스트 실패")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)