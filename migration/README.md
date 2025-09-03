# Migration Scripts

이 폴더는 ChromaDB에서 Supabase로의 데이터 마이그레이션 관련 스크립트들을 포함합니다.

## 스크립트 설명

### 데이터 추출 및 마이그레이션

- `extract_chroma_data.py`: ChromaDB에서 데이터를 추출하는 스크립트
- `migrate_to_supabase.py`: 추출된 데이터를 Supabase로 마이그레이션하는 메인 스크립트
- `migrate_reception_data.py`: 접수 문서 데이터 전용 마이그레이션 스크립트

### 테스트 및 검증

- `test_supabase_integration.py`: Supabase 통합 테스트
- `test_final_structure.py`: 최종 데이터 구조 검증 테스트

### 보고서

- `reports/`: 마이그레이션 과정에서 생성된 보고서들이 저장되는 폴더

## 사용법

마이그레이션은 이미 완료되었으며, 이 스크립트들은 참고용으로 보관됩니다.
현재 시스템은 ChromaDB를 사용하도록 구성되어 있습니다.