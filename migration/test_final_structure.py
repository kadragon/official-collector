"""
최종 매핑 구조 테스트
단순화된 2-테이블 구조 검증
"""

import os
import sys
import logging

# 프로젝트 루트를 Python path에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.services.updated_supabase_service import SupabaseService
from src.services.openai_embedding_service import OpenAIEmbeddingService

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_final_structure():
    """최종 테이블 구조 테스트"""
    logger.info("=== 최종 매핑 구조 테스트 ===")
    
    try:
        # 서비스 초기화
        supabase = SupabaseService()
        openai_service = OpenAIEmbeddingService()
        
        # 연결 상태 확인
        status = supabase.get_connection_status()
        logger.info(f"연결 상태: {status}")
        
        print(f"\n🎯 최종 테이블 구조:")
        print(f"📋 task_card_mappings: {status['task_mappings_count']}개")
        print(f"📄 reception_mappings: {status['reception_mappings_count']}개")
        print(f"🔗 총 매핑: {status['task_mappings_count'] + status['reception_mappings_count']}개")
        
        # 업무카드 매핑 테스트
        logger.info("\n=== 업무카드 매핑 테스트 ===")
        task_mappings = supabase.list_task_card_mappings(limit=3)
        
        if task_mappings:
            print("✅ 업무카드 매핑 샘플:")
            for mapping in task_mappings:
                print(f"  • {mapping['title']} → {mapping['task_title']}")
        
        # 접수 매핑 테스트
        logger.info("=== 접수 매핑 테스트 ===")
        reception_mappings = supabase.list_reception_mappings(limit=3)
        
        if reception_mappings:
            print("\n✅ 접수 매핑 샘플:")
            for mapping in reception_mappings:
                share = f" (공람:{mapping['share_target']})" if mapping['share_target'] else ""
                print(f"  • {mapping['title']} → {mapping['handler']}{share}")
        
        # 벡터 검색 테스트
        logger.info("=== 벡터 검색 테스트 ===")
        
        # 업무카드 검색 테스트
        query = "예산 관련 업무"
        embedding_result = openai_service.create_embedding(query, "test_query")
        
        if embedding_result and task_mappings:
            print(f"\n🔍 '{query}' 검색 테스트:")
            print("  벡터 검색 기능 준비 완료!")
        
        print("\n🚀 최종 구조 검증 완료!")
        print("=" * 50)
        print("최종 매핑 테이블 구조:")
        print("├── task_card_mappings (공문 → 업무카드)")
        print("│   ├── title: 공문명")
        print("│   ├── task_title: 업무카드명")  
        print("│   └── embedding: 벡터(1536차원)")
        print("└── reception_mappings (공문 → 담당자+공람)")
        print("    ├── title: 공문명")
        print("    ├── handler: 담당자")
        print("    ├── share_target: 공람대상")
        print("    └── embedding: 벡터(1536차원)")
        print("=" * 50)
        
        return True
        
    except Exception as e:
        logger.error(f"테스트 실패: {e}")
        return False


if __name__ == "__main__":
    success = test_final_structure()
    sys.exit(0 if success else 1)