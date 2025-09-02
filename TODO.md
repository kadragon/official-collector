# Supabase & OpenAI Embedding Migration TODO

## Phase 1: Infrastructure Setup ✅ COMPLETED

### Supabase Configuration
- [x] Supabase 프로젝트 생성 및 설정 ✅
- [x] 벡터 확장 (pgvector) 활성화 ✅
- [x] 데이터베이스 테이블 스키마 설계 ✅
  - [x] `reception_documents` 테이블 (접수 문서) ✅
  - [x] `task_cards` 테이블 (업무카드) ✅
  - [x] `document_embeddings` 테이블 (임베딩 저장) ✅
- [x] Row Level Security (RLS) 정책 설정 ✅
- [x] 환경변수 업데이트 (.env 파일) ✅

**Phase 1 완료 상세:**
- Supabase MCP 연결 테스트 성공
- pgvector 확장 활성화 완료
- 3개 테이블 생성 및 인덱스 구성
- HNSW 벡터 인덱스 (1536차원, text-embedding-3-small)
- RLS 정책 모든 테이블 적용
- 마이그레이션 기록: enable_vector_extension, create_*_table, enable_rls_policies

### OpenAI API 설정
- [x] OpenAI API 키 발급 및 설정 ✅ (기존 .env 파일에 설정됨)
- [x] 임베딩 모델 선택 ✅ **최종 결정: text-embedding-3-small (1536차원)**
  - pgvector 인덱스 호환성 (HNSW 지원)
  - 비용 효율성 및 성능 균형
- [ ] 요청 제한 및 비용 관리 설정

## Phase 2: Service Layer Development

### Supabase Service 개발
- [ ] `SupabaseService` 클래스 생성 (`src/services/supabase_service.py`)
  - [ ] 연결 설정 및 인증
  - [ ] CRUD 연산 메서드
  - [ ] 벡터 유사도 검색 구현
  - [ ] 배치 업데이트 기능

### OpenAI Embedding Service 개발
- [ ] `OpenAIEmbeddingService` 클래스 생성 (`src/services/openai_embedding_service.py`)
  - [ ] 텍스트 임베딩 생성
  - [ ] 배치 임베딩 처리
  - [ ] 에러 핸들링 및 재시도 로직
  - [ ] 비용 추적 기능

## Phase 3: Data Migration

### ChromaDB → Supabase 마이그레이션
- [ ] 기존 ChromaDB 데이터 추출 스크립트 작성
  - [ ] 접수 문서 데이터 추출
  - [ ] 업무카드 데이터 추출
  - [ ] 메타데이터 보존
- [ ] 임베딩 재계산
  - [ ] Ollama embedding → OpenAI embedding 변환
  - [ ] 차원 변경 (snowflake-arctic-embed → text-embedding-3-*)
  - [ ] 배치 처리로 API 요청 최적화
- [ ] Supabase 데이터 삽입 스크립트
  - [ ] 중복 제거 로직
  - [ ] 에러 처리 및 롤백
  - [ ] 진행률 표시

### 마이그레이션 스크립트 작성
- [ ] `migrate_to_supabase.py` 메인 마이그레이션 스크립트
- [ ] `backup_chroma_data.py` 백업 스크립트
- [ ] `verify_migration.py` 마이그레이션 검증 스크립트

## Phase 4: Core Application Integration

### DocumentProcessor 업데이트
- [ ] `DocumentProcessor` 클래스 수정 (`src/services/document_processor.py`)
  - [ ] ChromaService → SupabaseService 전환
  - [ ] Ollama embedding → OpenAI embedding 전환
  - [ ] 배치 업데이트 로직 유지
  - [ ] 기존 인터페이스 호환성 보장

### Configuration Management
- [ ] 환경변수 관리 강화
  - [ ] Supabase 연결 정보
  - [ ] OpenAI API 설정
  - [ ] 기존 Ollama/Chroma 설정 보존 (fallback용)
- [ ] 설정 검증 로직 추가

## Phase 5: Testing & Quality Assurance

### Integration Tests
- [ ] Supabase 연결 테스트
- [ ] OpenAI API 테스트
- [ ] 임베딩 생성/검색 테스트
- [ ] 마이그레이션 테스트
- [ ] 기존 테스트 케이스 업데이트

### Performance Testing
- [ ] 임베딩 생성 속도 비교
- [ ] 벡터 검색 성능 비교
- [ ] 배치 처리 최적화
- [ ] 메모리 사용량 모니터링

## Phase 6: Deployment & Monitoring

### Production Readiness
- [ ] 에러 로깅 강화
- [ ] 성능 메트릭 수집
- [ ] API 사용량 모니터링
- [ ] 백업/복구 전략 수립

### Documentation
- [ ] CLAUDE.md 업데이트
- [ ] 마이그레이션 가이드 작성
- [ ] 새로운 설정 방법 문서화
- [ ] 트러블슈팅 가이드

## Phase 7: Cleanup & Optimization

### Code Cleanup
- [ ] 사용하지 않는 Chroma 관련 코드 정리
- [ ] 임포트 정리
- [ ] 타입 힌트 추가/업데이트
- [ ] Pylint 점수 개선

### Optimization
- [ ] 임베딩 캐싱 전략
- [ ] API 요청 최적화
- [ ] 데이터베이스 인덱스 최적화
- [ ] 메모리 사용량 최적화

## Migration Strategy Notes

### 임베딩 차원 변경
- **기존**: Ollama snowflake-arctic-embed (차원: 384)
- **신규**: OpenAI text-embedding-3-small (1536차원) ✅ **최종 결정**
- **선택 이유**: 
  - pgvector HNSW 인덱스 호환 (2000차원 제한)
  - text-embedding-3-large (3072차원)는 인덱스 미지원으로 제외
- **주의사항**: 모든 기존 임베딩을 재계산해야 함

### 데이터 무결성 보장
- 마이그레이션 전 전체 백업
- 단계별 검증 포인트
- 롤백 계획 수립

### 비용 관리
- OpenAI API 사용량 모니터링
- 임베딩 생성 배치 최적화
- 불필요한 API 호출 방지

### 성능 고려사항
- Supabase pgvector 인덱스 최적화
- 배치 처리 크기 조정
- 네트워크 지연 최소화