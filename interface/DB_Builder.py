"""
FAISS Vector DB 관리 및 확인 페이지

FAISS 데이터베이스의 상태를 확인하고 관리할 수 있는 기능을 제공합니다.
- 벡터 DB 상태 확인
- 저장된 테이블 정보 조회
- 검색 테스트
- 새로운 테이블 정보 추가
"""

import streamlit as st
import os
import json
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional
import traceback

# LangSQL 모듈들
from llm_utils.vectordb import get_vector_db
from llm_utils.retrieval import search_tables
from llm_utils.llm import get_embeddings

# 페이지 설정
st.set_page_config(
    page_title="DB Builder", 
    page_icon="🗄️", 
    layout="wide"
)

st.title("🗄️ FAISS Vector DB 관리자")
st.markdown("---")

def get_vectordb_info():
    """벡터 DB 정보를 가져옵니다."""
    try:
        # 기본 경로
        vectordb_path = os.path.join(os.getcwd(), "table_info_db")
        
        info = {
            "path": vectordb_path,
            "exists": os.path.exists(vectordb_path),
            "faiss_file": os.path.join(vectordb_path, "index.faiss"),
            "pkl_file": os.path.join(vectordb_path, "index.pkl"),
            "faiss_exists": os.path.exists(os.path.join(vectordb_path, "index.faiss")),
            "pkl_exists": os.path.exists(os.path.join(vectordb_path, "index.pkl")),
        }
        
        # 파일 크기 정보
        if info["faiss_exists"]:
            info["faiss_size"] = os.path.getsize(info["faiss_file"]) / 1024  # KB
            info["faiss_modified"] = datetime.fromtimestamp(
                os.path.getmtime(info["faiss_file"])
            )
            
        if info["pkl_exists"]:
            info["pkl_size"] = os.path.getsize(info["pkl_file"]) / 1024  # KB
            info["pkl_modified"] = datetime.fromtimestamp(
                os.path.getmtime(info["pkl_file"])
            )
            
        return info
    except Exception as e:
        st.error(f"벡터 DB 정보 조회 중 오류: {e}")
        return None

def test_vectordb_connection():
    """벡터 DB 연결을 테스트합니다."""
    try:
        db = get_vector_db()
        # 간단한 검색으로 테스트
        docs = db.similarity_search("테스트", k=1)
        return True, len(docs), db
    except Exception as e:
        return False, str(e), None

def extract_all_documents(db):
    """벡터 DB의 모든 문서를 추출합니다."""
    try:
        # FAISS에서 모든 문서 가져오기
        all_docs = []
        
        # docstore에서 직접 가져오기
        if hasattr(db, 'docstore') and hasattr(db.docstore, '_dict'):
            for doc_id, doc in db.docstore._dict.items():
                all_docs.append({
                    "id": doc_id,
                    "content": doc.page_content,
                    "metadata": doc.metadata
                })
        
        return all_docs
    except Exception as e:
        st.error(f"문서 추출 중 오류: {e}")
        return []

def parse_table_info(content: str) -> Dict:
    """테이블 정보 텍스트를 파싱합니다."""
    try:
        lines = content.split("\n")
        
        if ": " not in lines[0]:
            return {"error": "잘못된 형식"}
            
        table_name, table_desc = lines[0].split(": ", 1)
        
        columns = {}
        current_section = None
        
        for line in lines[1:]:
            line = line.strip()
            if line == "Columns:":
                current_section = "columns"
                continue
                
            if current_section == "columns" and ": " in line:
                col_name, col_desc = line.split(": ", 1)
                columns[col_name.strip()] = col_desc.strip()
        
        return {
            "table_name": table_name,
            "table_description": table_desc.strip(),
            "columns": columns,
            "column_count": len(columns)
        }
    except Exception as e:
        return {"error": str(e)}

# 메인 레이아웃
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("📊 DB 상태 정보")
    
    # 벡터 DB 정보 표시
    db_info = get_vectordb_info()
    
    if db_info:
        st.markdown("**📂 파일 경로:**")
        st.code(db_info["path"])
        
        # 상태 표시
        if db_info["exists"]:
            st.success("✅ 디렉토리 존재")
        else:
            st.error("❌ 디렉토리 없음")
            
        # 파일 상태
        col_a, col_b = st.columns(2)
        with col_a:
            if db_info["faiss_exists"]:
                st.success("✅ FAISS 파일")
                st.write(f"크기: {db_info['faiss_size']:.1f} KB")
                st.write(f"수정: {db_info['faiss_modified'].strftime('%Y-%m-%d %H:%M')}")
            else:
                st.error("❌ FAISS 파일 없음")
                
        with col_b:
            if db_info["pkl_exists"]:
                st.success("✅ PKL 파일")
                st.write(f"크기: {db_info['pkl_size']:.1f} KB")
                st.write(f"수정: {db_info['pkl_modified'].strftime('%Y-%m-%d %H:%M')}")
            else:
                st.error("❌ PKL 파일 없음")
    
    st.markdown("---")
    
    # 연결 테스트
    st.subheader("🔌 연결 테스트")
    
    if st.button("DB 연결 테스트"):
        with st.spinner("연결 테스트 중..."):
            success, result, db = test_vectordb_connection()
            
            if success:
                st.success(f"✅ 연결 성공! ({result}개 문서 확인)")
                st.session_state["db_connected"] = True
                st.session_state["vector_db"] = db
            else:
                st.error(f"❌ 연결 실패: {result}")
                st.session_state["db_connected"] = False

with col2:
    st.subheader("🔍 DB 내용 탐색")
    
    # 탭 생성
    tab1, tab2, tab3 = st.tabs(["📋 테이블 목록", "🔎 검색 테스트", "➕ 새 테이블 추가"])
    
    with tab1:
        if st.session_state.get("db_connected", False):
            db = st.session_state.get("vector_db")
            
            if st.button("📥 모든 테이블 정보 불러오기"):
                with st.spinner("테이블 정보 로딩 중..."):
                    all_docs = extract_all_documents(db)
                    
                    if all_docs:
                        st.success(f"총 {len(all_docs)}개의 테이블 정보를 찾았습니다.")
                        
                        # 테이블 정보 파싱 및 표시
                        table_data = []
                        
                        for doc in all_docs:
                            parsed = parse_table_info(doc["content"])
                            if "error" not in parsed:
                                table_data.append({
                                    "테이블명": parsed["table_name"],
                                    "설명": parsed["table_description"][:50] + "..." if len(parsed["table_description"]) > 50 else parsed["table_description"],
                                    "컬럼수": parsed["column_count"],
                                    "ID": doc["id"]
                                })
                        
                        if table_data:
                            df = pd.DataFrame(table_data)
                            st.dataframe(df, use_container_width=True)
                            
                            # 선택한 테이블의 상세 정보
                            selected_table = st.selectbox(
                                "상세 정보를 볼 테이블 선택:",
                                options=[t["테이블명"] for t in table_data],
                                key="selected_table"
                            )
                            
                            if selected_table:
                                # 선택된 테이블의 전체 정보 표시
                                selected_doc = None
                                for doc in all_docs:
                                    parsed = parse_table_info(doc["content"])
                                    if "error" not in parsed and parsed["table_name"] == selected_table:
                                        selected_doc = doc
                                        break
                                
                                if selected_doc:
                                    st.markdown(f"### 📋 {selected_table} 상세 정보")
                                    
                                    parsed = parse_table_info(selected_doc["content"])
                                    st.write(f"**설명:** {parsed['table_description']}")
                                    
                                    if parsed["columns"]:
                                        st.write("**컬럼 정보:**")
                                        columns_df = pd.DataFrame([
                                            {"컬럼명": col, "설명": desc}
                                            for col, desc in parsed["columns"].items()
                                        ])
                                        st.dataframe(columns_df, use_container_width=True)
                                    
                                    # 원본 텍스트
                                    with st.expander("📄 원본 텍스트"):
                                        st.code(selected_doc["content"])
                        else:
                            st.warning("파싱 가능한 테이블 정보가 없습니다.")
                    else:
                        st.warning("저장된 테이블 정보가 없습니다.")
        else:
            st.info("먼저 DB 연결 테스트를 실행해주세요.")
    
    with tab2:
        st.markdown("### 🔎 검색 기능 테스트")
        
        search_query = st.text_input(
            "검색할 키워드를 입력하세요:",
            value="난청 환자",
            key="search_query"
        )
        
        col_search1, col_search2 = st.columns(2)
        with col_search1:
            retriever_type = st.selectbox(
                "검색 방식:",
                ["기본", "Reranker"],
                key="search_retriever"
            )
        with col_search2:
            top_k = st.slider("결과 개수:", 1, 10, 5, key="search_top_k")
        
        if st.button("🔍 검색 실행"):
            if search_query.strip():
                with st.spinner("검색 중..."):
                    try:
                        results = search_tables(
                            query=search_query,
                            retriever_name=retriever_type,
                            top_n=top_k,
                            device="cpu"
                        )
                        
                        if results:
                            st.success(f"✅ {len(results)}개의 테이블을 찾았습니다.")
                            
                            for i, (table_name, table_info) in enumerate(results.items(), 1):
                                with st.expander(f"{i}. {table_name} (유사도: {table_info.get('score', 'N/A')})"):
                                    st.write(f"**설명:** {table_info.get('table_description', 'N/A')}")
                                    
                                    # 컬럼 정보 표시
                                    columns = {k: v for k, v in table_info.items() 
                                             if k not in ['table_description', 'score', 'rank']}
                                    if columns:
                                        st.write("**주요 컬럼:**")
                                        for col, desc in list(columns.items())[:5]:  # 상위 5개만
                                            st.write(f"- **{col}**: {desc}")
                        else:
                            st.warning("검색 결과가 없습니다.")
                            
                    except Exception as e:
                        st.error(f"검색 중 오류 발생: {e}")
                        with st.expander("오류 상세"):
                            st.code(traceback.format_exc())
            else:
                st.warning("검색어를 입력해주세요.")
    
    with tab3:
        st.markdown("### ➕ 새로운 테이블 정보 추가")
        st.info("현재는 읽기 전용입니다. 새로운 테이블 정보를 추가하려면 table_catalog.csv를 수정한 후 create_faiss.py를 실행하세요.")
        
        with st.expander("📝 테이블 정보 형식 예시"):
            st.code("""
테이블명: 설명
Columns:
컬럼명1: 컬럼 설명1
컬럼명2: 컬럼 설명2
            """)
        
        st.markdown("**💡 추가 방법:**")
        st.markdown("""
1. `table_catalog.csv` 파일에 새로운 테이블/컬럼 정보 추가
2. `create_faiss.py` 스크립트 실행하여 벡터 DB 재생성
3. Streamlit 앱 재시작
        """)

# 사이드바에 추가 정보
st.sidebar.markdown("### 📖 사용 가이드")
st.sidebar.markdown("""
**DB Builder의 주요 기능:**

1. **DB 상태 확인**: FAISS 인덱스 파일 상태 모니터링
2. **테이블 탐색**: 저장된 모든 테이블 정보 조회
3. **검색 테스트**: 벡터 검색 기능 테스트
4. **정보 관리**: 테이블 메타데이터 관리

**주의사항:**
- 수정 작업은 신중하게 진행하세요
- 백업을 권장합니다
""")

# 환경 정보
with st.sidebar.expander("🔧 환경 정보"):
    st.write("**임베딩 모델 정보:**")
    try:
        embeddings = get_embeddings()
        st.write(f"- 모델: {getattr(embeddings, 'model', 'Unknown')}")
        st.write(f"- 제공자: {type(embeddings).__name__}")
    except Exception as e:
        st.write(f"- 오류: {e}")
