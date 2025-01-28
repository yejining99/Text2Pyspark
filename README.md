# AutoSQL

AutoSQL은 자연어 입력을 기반으로 SQL을 생성하는 프로젝트입니다. LangGraph, DataHub를 활용하여 데이터를 분석하고 최적의 SQL 쿼리를 생성 및 최적화합니다.

## 📌 프로젝트 목표
1. 자연어 입력을 기반으로 SQL 쿼리를 자동으로 생성
2. DataHub를 활용하여 관련 테이블 및 컬럼 메타데이터 조회
3. Best Practice Query를 참고하여 최적의 SQL 생성
4. SQL 최적화 과정을 거쳐 성능 향상

---

## 🚀 기술 스택
- **LangGraph**: LLM 기반의 쿼리 생성
- **DataHub**: 테이블 및 컬럼 메타데이터 조회

---

## 📦 설치 방법

### 1️⃣ 필수 패키지 설치

```bash
pip install -r requirements.txt
```

### 4️⃣ 환경 변수 설정

다음 환경 변수들은 설정되어야 합니다. `.env` 파일을 생성하여 다음과 같이 관리할 수 있습니다:

```
OPENAI_API_KEY=your-api-key-here
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=autosql
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
LANGCHAIN_API_KEY=your-langchain-api-key
```

---

## 🎯 사용 방법

1. **자연어 입력을 기반으로 테이블 조회**
2. **테이블의 스키마 및 컬럼 정보 확인**
3. **최적의 SQL 쿼리 생성**
4. **쿼리 최적화 실행**

---

## 📄 라이선스
MIT License

