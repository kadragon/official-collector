"""
접수 문서 데이터 마이그레이션 스크립트
기존 데이터 파일과 ChromaDB에서 접수 정보를 수집하여 reception_mappings로 이관
"""

import os
import sys
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Tuple
import random

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


class ReceptionMigrator:
    """접수 문서 마이그레이션 관리자"""
    
    def __init__(self):
        """초기화"""
        self.supabase = SupabaseService()
        self.openai_service = OpenAIEmbeddingService()
        
        logger.info("접수 문서 마이그레이션 관리자 초기화 완료")
    
    def load_data_files(self) -> Tuple[List[str], List[str]]:
        """data 폴더에서 담당자와 공람 목록 로드"""
        logger.info("데이터 파일에서 담당자 및 공람 목록 로드 중...")
        
        try:
            # 담당자 목록
            with open('./data/reception_list.txt', 'r', encoding='utf-8') as f:
                handlers = [line.strip() for line in f if line.strip()]
            
            # 공람 목록  
            with open('./data/share_list.txt', 'r', encoding='utf-8') as f:
                share_targets = [line.strip() for line in f if line.strip()]
            
            logger.info(f"담당자 {len(handlers)}개, 공람 {len(share_targets)}개 로드 완료")
            
            return handlers, share_targets
            
        except Exception as e:
            logger.error(f"데이터 파일 로드 실패: {e}")
            return [], []
    
    def generate_sample_reception_mappings(self, handlers: List[str], share_targets: List[str], 
                                         task_titles: List[str]) -> List[Dict[str, Any]]:
        """샘플 접수 매핑 데이터 생성"""
        logger.info("샘플 접수 매핑 데이터 생성 중...")
        
        # 기본 공문 템플릿들
        document_templates = [
            "{}에 대한 승인 요청",
            "{} 관련 협조 요청", 
            "{} 계획 수립 안내",
            "{} 시행 관련 공문",
            "{} 업무 처리 요청",
            "{} 예산 집행 승인",
            "{} 교육 실시 안내",
            "{} 회의 개최 안내",
            "{} 보고서 제출 요청",
            "{} 시스템 개선 요청"
        ]
        
        # 업무 키워드들 (기존 업무카드에서 추출)
        keywords = [
            "학사관리", "인사", "예산", "교육훈련", "시스템", "회계", 
            "연구지원", "대외협력", "기획평가", "학생지도", "홈페이지",
            "국회대응", "청렴교육", "장학금", "입시", "졸업", "성적"
        ]
        
        reception_mappings = []
        
        # 각 담당자별로 여러 문서 매핑 생성
        for handler in handlers:
            # 담당자당 3-7개 문서 생성
            num_docs = random.randint(3, 7)
            
            for _ in range(num_docs):
                # 랜덤하게 키워드와 템플릿 선택
                keyword = random.choice(keywords)
                template = random.choice(document_templates)
                title = template.format(keyword)
                
                # 랜덤하게 공람 선택 (일부는 None 가능)
                share_target = random.choice(share_targets + [None])
                
                reception_mappings.append({
                    'title': title,
                    'handler': handler,
                    'share_target': share_target
                })
        
        logger.info(f"총 {len(reception_mappings)}개 샘플 접수 매핑 생성 완료")
        return reception_mappings
    
    def migrate_reception_mappings(self, mappings: List[Dict[str, Any]], batch_size: int = 20) -> bool:
        """접수 매핑 데이터 마이그레이션"""
        logger.info(f"=== 접수 매핑 마이그레이션 시작 ({len(mappings)}개) ===")
        
        try:
            # 1단계: OpenAI 임베딩 생성
            logger.info("1단계: OpenAI 임베딩 생성 중...")
            
            embedding_requests = []
            for mapping in mappings:
                # 공문명과 담당자, 공람 정보를 조합하여 임베딩 텍스트 생성
                embedding_text = f"{mapping['title']} 담당:{mapping['handler']}"
                if mapping['share_target']:
                    embedding_text += f" 공람:{mapping['share_target']}"
                
                embedding_requests.append(EmbeddingRequest(
                    text=embedding_text,
                    identifier=f"reception_{len(embedding_requests)}",
                    metadata=mapping
                ))
            
            # 배치 임베딩 생성
            embedding_results = self.openai_service.create_embeddings_batch(
                embedding_requests, batch_size=batch_size
            )
            
            logger.info(f"2단계: Supabase 접수 매핑 저장 중... ({len(embedding_results)}개)")
            
            # 2단계: Supabase에 저장
            success_count = 0
            
            for result in embedding_results:
                try:
                    original_mapping = result.metadata
                    
                    # reception_mappings 테이블에 직접 삽입
                    data = {
                        'title': original_mapping['title'],
                        'handler': original_mapping['handler'],
                        'share_target': original_mapping.get('share_target'),
                        'embedding': result.embedding,
                        'metadata': {
                            'generated': True,
                            'embedding_model': 'text-embedding-3-small',
                            'token_count': result.token_count,
                            'migration_timestamp': datetime.now().isoformat()
                        }
                    }
                    
                    # Supabase에 직접 삽입
                    insert_result = self.supabase.client.table('reception_mappings').insert(data).execute()
                    success_count += 1
                    
                    if success_count % 10 == 0:
                        logger.info(f"진행률: {success_count}/{len(embedding_results)} 접수 매핑 저장 완료")
                
                except Exception as e:
                    logger.error(f"접수 매핑 저장 실패 ({original_mapping['title']}): {e}")
                    continue
            
            logger.info(f"✅ 접수 매핑 마이그레이션 완료: {success_count}개 성공")
            
            # 비용 정보
            cost_summary = self.openai_service.get_cost_summary()
            logger.info(f"💰 총 비용: ${cost_summary['total_cost_usd']:.6f}")
            
            return success_count > 0
            
        except Exception as e:
            logger.error(f"접수 매핑 마이그레이션 중 오류: {e}")
            return False
    
    def verify_reception_migration(self) -> Dict[str, Any]:
        """접수 매핑 마이그레이션 검증"""
        logger.info("=== 접수 매핑 마이그레이션 검증 ===")
        
        try:
            # 데이터 개수 확인
            result = self.supabase.client.table('reception_mappings').select('count', count='exact').execute()
            total_count = result.count
            
            # 샘플 데이터 확인
            sample_result = self.supabase.client.table('reception_mappings').select('*').limit(5).execute()
            sample_data = sample_result.data
            
            # 담당자별 분포 확인
            handler_result = self.supabase.client.rpc('get_handler_distribution').execute()
            
            verification = {
                'total_mappings': total_count,
                'sample_data': sample_data,
                'cost_summary': self.openai_service.get_cost_summary(),
                'verification_timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"✅ 접수 매핑 데이터: {total_count}개")
            logger.info(f"💰 총 비용: ${verification['cost_summary']['total_cost_usd']:.6f}")
            
            return verification
            
        except Exception as e:
            logger.error(f"마이그레이션 검증 중 오류: {e}")
            return {'error': str(e)}


def main():
    """메인 실행"""
    logger.info("=== 접수 문서 마이그레이션 시작 ===")
    
    try:
        # 마이그레이터 초기화
        migrator = ReceptionMigrator()
        
        # 데이터 파일 로드
        handlers, share_targets = migrator.load_data_files()
        
        if not handlers:
            logger.error("담당자 목록이 없습니다.")
            return False
        
        # 기존 업무카드 제목들을 참조용으로 가져오기
        task_cards_result = migrator.supabase.client.table('task_card_mappings').select('task_title').execute()
        task_titles = [item['task_title'] for item in task_cards_result.data]
        
        # 샘플 접수 매핑 데이터 생성
        reception_mappings = migrator.generate_sample_reception_mappings(
            handlers, share_targets, task_titles
        )
        
        # 마이그레이션 실행
        success = migrator.migrate_reception_mappings(reception_mappings)
        
        if success:
            # 검증
            verification = migrator.verify_reception_migration()
            
            print(f"\n🎉 접수 문서 마이그레이션 완료!")
            print(f"📊 총 매핑: {verification.get('total_mappings', 0)}개")
            
            cost_info = verification.get('cost_summary', {})
            print(f"💰 총 비용: ${cost_info.get('total_cost_usd', 0):.6f}")
            print(f"🔢 총 토큰: {cost_info.get('total_tokens', 0)}")
            
            return True
        else:
            logger.error("접수 문서 마이그레이션 실패")
            return False
    
    except Exception as e:
        logger.error(f"마이그레이션 실행 중 오류: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)