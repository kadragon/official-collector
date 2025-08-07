# 공문 자동화 시스템 (Official Collector)

Python 3.12+ 기반의 공문 자동화 시스템입니다. RPA(Robotic Process Automation)를 사용하여 공문을 자동으로 분류하고 처리합니다. 외부 API 없이 Ollama와 Chroma를 사용하여 완전히 로컬에서 동작합니다.

## 주요 기능

- **완전 로컬 동작**: 외부 API 의존성 없음 - 로컬 Ollama와 Chroma 사용
- **RPA 자동화**: 한국 공문 처리 워크플로우 자동화
- **지능형 매칭**: 벡터 유사도 검색을 통한 문서 분류
- **배치 처리**: 큐잉된 데이터베이스 작업으로 최적화된 성능
- **대화형 모드**: 문서 처리 결정에 대한 사용자 확인 옵션

## 빠른 설치

### 1. 필수 프로그램 설치

winget을 사용하여 Python, uv, Ollama를 설치합니다:

```bash
# Python 3.12+ 설치
winget install Python.Python.3.12

# uv (Python 패키지 관리자) 설치
winget install astral-sh.uv

# Ollama 설치
winget install Ollama.Ollama
```

### 2. 설정 파일 준비

`data/` 디렉토리에 다음 세 개의 설정 파일을 생성합니다 (.example 파일을 복사하여 사용자 환경에 맞게 수정):

```txt
data/card_list.txt      # 업무카드 카테고리 목록 (한 줄에 하나씩)
data/reception_list.txt # 문서 담당자 목록 (한 줄에 하나씩)
data/share_list.txt     # 회람 옵션 목록 (한 줄에 하나씩)
```

### 3. 환경 설정

`.env` 파일을 생성합니다:

```env
# Ollama 설정 (필수)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=snowflake-arctic-embed

# Chroma 설정 (필수)
CHROMA_PERSIST_DIR=./chroma_db
```

### 4. 의존성 설치

```bash
uv install
```

### 5. Ollama 모델 설정

```bash
# 임베딩 모델 다운로드
ollama pull snowflake-arctic-embed

# Ollama 실행 상태 확인
ollama list
```

## 사용법

### 애플리케이션 실행

```bash
# 표준 모드 (자동 계속 처리)
uv run ./src/main.py

# 대화형 모드 (각 문서에 대해 사용자 확인)
uv run ./src/main.py --interactive

# 저장된 데이터 삭제
uv run ./src/main.py --delete
```

### 통합 테스트

```bash
# 개발 의존성 설치
uv sync --group dev

# Ollama와 Chroma 연결 테스트
pytest tests/integration/test_chroma_integration.py -v
```

### 코드 품질 검사

```bash
# 코드 품질 검사 실행
uv run pylint src/
```

## 아키텍처

- **로컬 우선**: 임베딩을 위한 Ollama와 벡터 저장을 위한 Chroma 사용
- **RPA 통합**: Windows 자동화를 위한 pywinauto
- **배치 처리**: 더 나은 성능을 위한 최적화된 데이터베이스 작업
- **벡터 유사도**: 의미적 검색을 사용한 지능형 문서 매칭

## 데이터 관리

시스템은 다음과 같은 로컬 데이터 저장소를 유지합니다:

- Chroma 데이터베이스의 벡터 임베딩 (`./chroma_db`)
- `data/` 디렉토리의 설정 파일
