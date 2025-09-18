"""
Lang2SQL Streamlit 애플리케이션.

자연어로 입력된 질문을 SQL 쿼리로 변환하고,
ClickHouse 데이터베이스에 실행한 결과를 출력합니다.
"""

import sys
import os

# import 경로 문제 해결: 프로젝트 루트를 sys.path에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)  # interface의 상위 디렉토리 (lang2sql)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import re
from dotenv import load_dotenv

# .env 파일 로딩 (최우선 실행)
load_dotenv()

import streamlit as st
import time
import json
from langchain.chains.sql_database.prompt import SQL_PROMPTS
from langchain_core.messages import AIMessage, HumanMessage

# from db_utils import get_db_connector
# from db_utils.base_connector import BaseConnector
# from infra.db.connect_db import ConnectDB
from viz.display_chart import DisplayChart
from engine.query_executor import execute_query as execute_query_common
from llm_utils.llm_response_parser import LLMResponseParser
from infra.observability.token_usage import TokenUtils
from llm_utils.graph_utils.enriched_graph import builder as enriched_builder
from llm_utils.graph_utils.basic_graph import builder
from llm_utils.graph_utils.base import (
    GET_TABLE_INFO,
    PROFILE_EXTRACTION, 
    CONTEXT_ENRICHMENT,
    QUERY_MAKER
)


TITLE = "⚡ 신위험률 일원화테이블 Text2Pyspark"
DEFAULT_QUERY = "난청(노년난청제외) 연간환자수를 실손데이터에서 CY별, 성, 연령 5세단위로 집계하는 쿼리"
SIDEBAR_OPTIONS = {
    "show_token_usage": "Show Token Usage",
    "show_result_description": "Show Result Description",
    "show_sql": "Show SQL",
    "show_question_reinterpreted_by_ai": "Show User Question Reinterpreted by AI",
    "show_referenced_tables": "Show List of Referenced Tables",
    "show_table": "Show Table",
    "show_chart": "Show Chart",
}


def get_node_display_name(node_name: str) -> str:
    """노드 이름을 사용자 친화적인 한국어로 변환합니다."""
    node_names = {
        GET_TABLE_INFO: "📋 테이블 정보 검색",
        PROFILE_EXTRACTION: "🔍 질문 프로파일 추출",
        CONTEXT_ENRICHMENT: "💡 컨텍스트 보강",
        QUERY_MAKER: "⚡ SQL 쿼리 생성"
    }
    return node_names.get(node_name, node_name)


def display_node_status(status_container, current_node: str, progress: float, total_nodes: int):
    """현재 실행 중인 노드 상태를 표시합니다."""
    with status_container:
        st.markdown("### 🔄 실행 상태")
        
        # 진행률 바
        st.progress(progress)
        st.write(f"진행률: {progress:.1%} ({int(progress * total_nodes)}/{total_nodes} 노드 완료)")
        
        # 현재 실행 중인 노드
        if current_node:
            st.markdown(f"**현재 실행 중:** {get_node_display_name(current_node)}")


def display_node_result(results_container, node_name: str, input_data: dict, output_data: dict, execution_time: float):
    """노드 실행 결과를 표시합니다."""
    with results_container:
        # 노드 상태에 따른 아이콘
        status_icon = "✅"
        if execution_time > 5:
            status_icon = "⚠️"  # 실행 시간이 길면 경고
        
        with st.expander(f"{status_icon} {get_node_display_name(node_name)} - {execution_time:.2f}초", expanded=True):
            
            # 탭으로 정보 구분
            tab1, tab2, tab3 = st.tabs(["📥 입력", "📤 출력", "🔍 상세"])
            
            with tab1:
                st.markdown("**입력 데이터:**")
                if node_name == GET_TABLE_INFO:
                    st.markdown("📝 **사용자 질문:**")
                    user_msg = input_data.get('messages', [{}])[0]
                    question = user_msg.get('content', 'N/A') if isinstance(user_msg, dict) else getattr(user_msg, 'content', 'N/A')
                    st.code(question, language='text')
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("검색기", input_data.get('retriever_name', 'N/A'))
                    with col2:
                        st.metric("상위 N개", input_data.get('top_n', 'N/A'))
                    with col3:
                        st.metric("디바이스", input_data.get('device', 'N/A'))
                        
                elif node_name == PROFILE_EXTRACTION:
                    st.markdown("📝 **분석할 질문:**")
                    user_msg = input_data.get('messages', [{}])[0]
                    question = user_msg.get('content', 'N/A') if isinstance(user_msg, dict) else getattr(user_msg, 'content', 'N/A')
                    st.code(question, language='text')
                    
                elif node_name == CONTEXT_ENRICHMENT:
                    st.markdown("🔍 **프로파일 정보:**")
                    profile = output_data.get('question_profile', {})  # 이전 노드 결과 사용
                    if profile:
                        if hasattr(profile, 'model_dump'):
                            st.json(profile.model_dump())
                        else:
                            st.json(profile)
                    
                elif node_name == QUERY_MAKER:
                    st.markdown("💭 **최종 입력 질문:**")
                    messages = output_data.get('messages', [])
                    if len(messages) > 1:
                        last_message = messages[-2]  # QUERY_MAKER 직전 메시지
                        content = last_message.content if hasattr(last_message, 'content') else str(last_message)
                        st.code(content, language='text')
            
            with tab2:
                st.markdown("**출력 결과:**")
                if node_name == GET_TABLE_INFO:
                    tables = output_data.get('searched_tables', {})
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("검색된 테이블 수", len(tables))
                    with col2:
                        try:
                            scores = [float(table.get('score', 0)) for table in tables.values() if table.get('score') != 'N/A']
                            avg_score = sum(scores) / len(scores) if scores else 0
                            st.metric("평균 유사도", f"{avg_score:.3f}")
                        except:
                            st.metric("평균 유사도", "계산 불가")
                    
                    if tables:
                        st.markdown("**📋 검색된 테이블 목록:**")
                        for i, (table_name, table_info) in enumerate(list(tables.items())[:5]):
                            score = table_info.get('score', 'N/A')
                            table_desc = table_info.get('table_description', 'N/A')
                            st.write(f"{i+1}. **{table_name}** (유사도: {score})")
                            st.write(f"   📄 {table_desc}")
                    else:
                        st.warning("검색된 테이블이 없습니다. 벡터 DB 또는 임베딩 설정을 확인해주세요.")
                            
                elif node_name == PROFILE_EXTRACTION:
                    profile = output_data.get('question_profile', {})
                    if profile:
                        st.markdown("**🏷️ 추출된 프로파일:**")
                        if hasattr(profile, 'model_dump'):
                            profile_dict = profile.model_dump()
                        else:
                            profile_dict = profile
                        
                        # 중요한 속성들을 메트릭으로 표시
                        cols = st.columns(3)
                        for i, (key, value) in enumerate(list(profile_dict.items())[:6]):
                            with cols[i % 3]:
                                st.metric(key.replace('_', ' ').title(), str(value))
                                
                elif node_name == CONTEXT_ENRICHMENT:
                    messages = output_data.get('messages', [])
                    if len(messages) > 1:
                        last_message = messages[-1]
                        content = last_message.content if hasattr(last_message, 'content') else str(last_message)
                        st.markdown("**💡 보강된 질문:**")
                        st.code(content, language='text')
                        
                elif node_name == QUERY_MAKER:
                    generated_query = output_data.get('generated_query')
                    if generated_query:
                        query_content = generated_query.content if hasattr(generated_query, 'content') else str(generated_query)
                        
                        # SQL과 해석 부분 분리
                        try:
                            sql = LLMResponseParser.extract_sql(query_content)
                            st.markdown("**🔧 생성된 SQL:**")
                            st.code(sql, language="sql")
                            
                            interpretation = LLMResponseParser.extract_interpretation(query_content)
                            if interpretation:
                                st.markdown("**📖 쿼리 해석:**")
                                st.write(interpretation)
                        except Exception as e:
                            st.code(query_content, language="sql")
            
            with tab3:
                st.markdown("**상세 정보:**")
                
                # 실행 시간 정보
                if execution_time < 1:
                    time_status = "🟢 빠름"
                elif execution_time < 3:
                    time_status = "🟡 보통"
                else:
                    time_status = "🔴 느림"
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("실행 시간", f"{execution_time:.2f}초", delta=time_status)
                    
                with col2:
                    st.metric("메모리 사용", "추정 중...")  # 향후 메모리 모니터링 추가 가능
                
                # 노드별 상세 정보
                if node_name == GET_TABLE_INFO:
                    st.markdown("**🔍 검색 상세:**")
                    retriever_info = {
                        "검색 방식": input_data.get('retriever_name', 'N/A'),
                        "벡터 DB 유형": "FAISS",
                        "임베딩 모델": "추정 중..."
                    }
                    st.json(retriever_info)
                    
                elif node_name == PROFILE_EXTRACTION:
                    st.markdown("**🎯 프로파일 추출 상세:**")
                    st.write("질문의 특성을 분석하여 적절한 SQL 패턴을 결정합니다.")
                    
                elif node_name == CONTEXT_ENRICHMENT:
                    st.markdown("**🔄 컨텍스트 보강 상세:**")
                    st.write("프로파일과 테이블 정보를 활용하여 질문을 더 구체적으로 만듭니다.")
                    
                elif node_name == QUERY_MAKER:
                    st.markdown("**⚙️ SQL 생성 상세:**")
                    st.write("LLM을 사용하여 자연어 질문을 SQL 쿼리로 변환합니다.")
                
                # 전체 상태 정보 (디버깅용)
                with st.expander("🔧 디버깅 정보 (전체 상태)"):
                    st.json({
                        "input_keys": list(input_data.keys()),
                        "output_keys": list(output_data.keys()),
                        "messages_count": len(output_data.get('messages', [])),
                        "node_name": node_name
                    })


def execute_query_with_monitoring(
    *,
    query: str,
    database_env: str,
    retriever_name: str = "기본",
    top_n: int = 5,
    device: str = "cpu",
) -> dict:
    """
    실시간 모니터링과 함께 쿼리를 실행합니다.
    """
    # 그래프 선택 (기본값을 True로 설정하여 enriched graph 우선 사용)
    use_enriched = st.session_state.get("use_enriched", True)
    graph = st.session_state.get("graph")
    
    if graph is None:
        st.error("그래프가 초기화되지 않았습니다.")
        return {}
    
    # 모니터링 UI 컨테이너 생성
    status_container = st.empty()
    results_container = st.container()
    
    # 전체 실행 시간 추적
    total_start_time = time.time()
    
    # 입력 데이터 준비
    initial_input = {
        "messages": [HumanMessage(content=query)],
        "user_database_env": database_env,
        "best_practice_query": "",
        "retriever_name": retriever_name,
        "top_n": top_n,
        "device": device,
    }
    
    # 노드 실행 추적을 위한 변수
    node_sequence = []
    if use_enriched:
        node_sequence = [GET_TABLE_INFO, PROFILE_EXTRACTION, CONTEXT_ENRICHMENT, QUERY_MAKER]
    else:
        node_sequence = [GET_TABLE_INFO, QUERY_MAKER]
    
    total_nodes = len(node_sequence)
    completed_nodes = 0
    results = {}
    
    try:
        # 스트림 실행
        for chunk in graph.stream(initial_input):
            for node_name, node_output in chunk.items():
                if node_name in node_sequence:
                    start_time = time.time()
                    
                    # 현재 노드 상태 표시
                    progress = completed_nodes / total_nodes
                    display_node_status(status_container, node_name, progress, total_nodes)
                    
                    # 노드 실행 시간 시뮬레이션 (실제로는 이미 완료된 상태)
                    execution_time = time.time() - start_time + 0.5  # 최소 0.5초 표시
                    
                    # 결과 표시
                    display_node_result(
                        results_container,
                        node_name, 
                        initial_input,
                        node_output,
                        execution_time
                    )
                    
                    completed_nodes += 1
                    results = node_output
                    
                    # UI 업데이트를 위한 짧은 지연
                    time.sleep(0.2)
        
        # 완료 상태 표시
        total_execution_time = time.time() - total_start_time
        with status_container:
            st.markdown("### ✅ 실행 완료!")
            st.success(f"전체 실행 시간: {total_execution_time:.2f}초")
            st.progress(1.0)
            
            # 실행 요약 정보
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("총 노드 수", total_nodes)
            with col2:
                st.metric("평균 노드 실행 시간", f"{total_execution_time/total_nodes:.2f}초")
            with col3:
                performance = "🟢 우수" if total_execution_time < 10 else "🟡 보통" if total_execution_time < 20 else "🔴 느림"
                st.metric("성능", performance)
        
        return results
        
    except Exception as e:
        st.error(f"실행 중 오류가 발생했습니다: {str(e)}")
        return {}


def execute_query(
    *,
    query: str,
    database_env: str,
    retriever_name: str = "기본",
    top_n: int = 5,
    device: str = "cpu",
) -> dict:
    """
    자연어 쿼리를 SQL로 변환하고 실행 결과를 반환하는 Lang2SQL 그래프 인터페이스 함수입니다.

    이 함수는 공용 execute_query 함수를 호출하여 Lang2SQL 파이프라인을 실행합니다.
    Streamlit 세션 상태를 활용하여 그래프를 재사용합니다.

    Args:
        query (str): 사용자가 입력한 자연어 기반 질문.
        database_env (str): 사용할 데이터베이스 환경 이름 또는 키 (예: "dev", "prod").
        retriever_name (str, optional): 테이블 검색기 이름. 기본값은 "기본".
        top_n (int, optional): 검색된 상위 테이블 수 제한. 기본값은 5.
        device (str, optional): LLM 실행에 사용할 디바이스 ("cpu" 또는 "cuda"). 기본값은 "cpu".

    Returns:
        dict: 다음 정보를 포함한 Lang2SQL 실행 결과 딕셔너리:
            - "generated_query": 생성된 SQL 쿼리 (`AIMessage`)
            - "messages": 전체 LLM 응답 메시지 목록
            - "searched_tables": 참조된 테이블 목록 등 추가 정보
    """

    return execute_query_common(
        query=query,
        database_env=database_env,
        retriever_name=retriever_name,
        top_n=top_n,
        device=device,
        use_enriched_graph=st.session_state.get("use_enriched", True),
        session_state=st.session_state,
    )


def display_result(
    *,
    res: dict,
    database,
) -> None:
    """
    Lang2SQL 실행 결과를 Streamlit 화면에 출력합니다.

    Args:
        res (dict): Lang2SQL 실행 결과 딕셔너리.
        database (ConnectDB): SQL 쿼리 실행을 위한 데이터베이스 연결 객체.

    출력 항목:
        - 총 토큰 사용량
        - 생성된 SQL 쿼리
        - 결과 설명
        - AI가 재해석한 사용자 질문
        - 참조된 테이블 목록
        - 쿼리 실행 결과 테이블
    """

    def should_show(_key: str) -> bool:
        return st.session_state.get(_key, True)

    has_query = bool(res.get("generated_query"))
    # 섹션 표시 여부를 QUERY_MAKER 출력 유무에 따라 제어
    show_sql_section = has_query and should_show("show_sql")
    show_result_desc = has_query and should_show("show_result_description")
    show_reinterpreted = has_query and should_show("show_question_reinterpreted_by_ai")
    show_table_section = has_query and should_show("show_table")
    show_chart_section = has_query and should_show("show_chart")

    if should_show("show_token_usage"):
        st.markdown("---")
        token_summary = TokenUtils.get_token_usage_summary(data=res["messages"])
        st.write("**토큰 사용량:**")
        st.markdown(
            f"""
        - Input tokens: `{token_summary['input_tokens']}`
        - Output tokens: `{token_summary['output_tokens']}`
        - Total tokens: `{token_summary['total_tokens']}`
        """
        )

    if show_sql_section:
        st.markdown("---")
        generated_query = res.get("generated_query")
        if generated_query:
            query_text = (
                generated_query.content
                if isinstance(generated_query, AIMessage)
                else str(generated_query)
            )

            # query_text가 문자열인지 확인
            if isinstance(query_text, str):
                try:
                    sql = LLMResponseParser.extract_sql(query_text)
                    st.markdown("**생성된 SQL 쿼리:**")
                    st.code(sql, language="sql")
                except ValueError:
                    st.warning("SQL 블록을 추출할 수 없습니다.")
                    st.text(query_text)

                interpretation = LLMResponseParser.extract_interpretation(query_text)
                if interpretation:
                    st.markdown("**결과 해석:**")
                    st.code(interpretation)
            else:
                st.warning("쿼리 텍스트가 문자열이 아닙니다.")
                st.text(str(query_text))

    if show_result_desc:
        st.markdown("---")
        st.markdown("**결과 설명:**")
        result_message = res["messages"][-1].content

        if isinstance(result_message, str):
            try:
                sql = LLMResponseParser.extract_sql(result_message)
                st.code(sql, language="sql")
            except ValueError:
                st.warning("SQL 블록을 추출할 수 없습니다.")
                st.text(result_message)

            interpretation = LLMResponseParser.extract_interpretation(result_message)
            if interpretation:
                st.code(interpretation, language="plaintext")
        else:
            st.warning("결과 메시지가 문자열이 아닙니다.")
            st.text(str(result_message))

    if show_reinterpreted:
        st.markdown("---")
        st.markdown("**AI가 재해석한 사용자 질문:**")
        try:
            if len(res["messages"]) > 1:
                candidate = res["messages"][-2]
                question_text = (
                    candidate.content
                    if hasattr(candidate, "content")
                    else str(candidate)
                )
            else:
                question_text = res["messages"][0].content
        except Exception:
            question_text = str(res["messages"][0].content)
        st.code(question_text)

    if should_show("show_referenced_tables"):
        st.markdown("---")
        st.markdown("**참고한 테이블 목록:**")
        st.write(res.get("searched_tables", []))

    # QUERY_MAKER가 비활성화된 경우 안내 메시지 출력
    if not has_query:
        st.info("QUERY_MAKER 없이 실행되었습니다. 검색된 테이블 정보만 표시합니다.")

    if show_table_section:
        st.markdown("---")
        try:
            sql_raw = (
                res["generated_query"].content
                if isinstance(res["generated_query"], AIMessage)
                else str(res["generated_query"])
            )
            if isinstance(sql_raw, str):
                sql = LLMResponseParser.extract_sql(sql_raw)
                df = database.run_sql(sql)
                st.dataframe(df.head(10) if len(df) > 10 else df)
            else:
                st.error("SQL 원본이 문자열이 아닙니다.")
        except Exception as e:
            st.error(f"쿼리 실행 중 오류 발생: {e}")

    if show_chart_section:
        st.markdown("---")
        try:
            sql_raw = (
                res["generated_query"].content
                if isinstance(res["generated_query"], AIMessage)
                else str(res["generated_query"])
            )
            if isinstance(sql_raw, str):
                sql = LLMResponseParser.extract_sql(sql_raw)
                df = database.run_sql(sql)
                st.markdown("**쿼리 결과 시각화:**")
                try:
                    if len(res["messages"]) > 1:
                        candidate = res["messages"][-2]
                        chart_question = (
                            candidate.content
                            if hasattr(candidate, "content")
                            else str(candidate)
                        )
                    else:
                        chart_question = res["messages"][0].content
                except Exception:
                    chart_question = str(res["messages"][0].content)

                display_code = DisplayChart(
                    question=chart_question,
                    sql=sql,
                    df_metadata=f"Running df.dtypes gives:\n{df.dtypes}",
                )
                # plotly_code 변수도 따로 보관할 필요 없이 바로 그려도 됩니다
                fig = display_code.get_plotly_figure(
                    plotly_code=display_code.generate_plotly_code(), df=df
                )
                st.plotly_chart(fig)
            else:
                st.error("SQL 원본이 문자열이 아닙니다.")
        except Exception as e:
            st.error(f"차트 생성 중 오류 발생: {e}")


# 임시로 데이터베이스 연결 비활성화 (FAISS 테스트용)
# db = get_db_connector()
db = None

st.title(TITLE)

# 워크플로우 선택(UI)
# st.sidebar.markdown("### 워크플로우 선택")
# use_enriched = st.sidebar.checkbox(
#     "🚀 확장된 워크플로우 (프로파일 추출 & 컨텍스트 보강)", 
#     value=True,
#     help="더 정확한 SQL 생성을 위해 질문을 분석하고 컨텍스트를 보강합니다. (권장)"
# )
use_enriched = True

# 모니터링 옵션
# st.sidebar.markdown("### 모니터링 옵션")
# enable_monitoring = st.sidebar.checkbox(
#     "🔍 실시간 노드 실행 모니터링", 
#     value=True,
#     help="각 LangGraph 노드의 실행 과정을 실시간으로 모니터링합니다."
# )
enable_monitoring = True

# 세션 상태 초기화
if "graph" not in st.session_state or st.session_state.get("use_enriched") != use_enriched:
    # 확장된 그래프로 고정
    graph_builder = enriched_builder
    st.session_state["graph"] = graph_builder.compile()
    st.session_state["use_enriched"] = use_enriched

# # 새로고침 버튼 추가
# if st.sidebar.button("Lang2SQL 새로고침"):
#     # 그래프 선택 로직
#     if st.session_state.get("use_enriched"):
#         graph_builder = enriched_builder
#         graph_type = "확장된"
#     else:
#         graph_builder = builder
#         graph_type = "기본"

#     st.session_state["graph"] = graph_builder.compile()
#     st.sidebar.success(
#         f"Lang2SQL이 성공적으로 새로고침되었습니다. ({graph_type} 워크플로우)"
#     )

user_query = st.text_area(
    "쿼리를 입력하세요:",
    value=DEFAULT_QUERY,
)
# user_database_env = st.selectbox(
#     "DB 환경정보를 입력하세요:",
#     options=SQL_PROMPTS.keys(),
#     index=0,
# )
user_database_env = "create"

# _device_options = ["cpu", "cuda"]
# _default_device = st.session_state.get("default_device", "cpu")
# _device_index = (
#     _device_options.index(_default_device) if _default_device in _device_options else 0
# )
# device = st.selectbox(
#     "모델 실행 장치를 선택하세요:",
#     options=_device_options,
#     index=_device_index,
# )
device = "cpu"

retriever_options = {
    "기본": "벡터 검색 (기본)",
    "Reranker": "Reranker 검색 (정확도 향상)",
}

_retriever_keys = list(retriever_options.keys())
_default_retriever = st.session_state.get("default_retriever_name", "기본")
_retriever_index = (
    _retriever_keys.index(_default_retriever)
    if _default_retriever in _retriever_keys
    else 0
)
user_retriever = st.selectbox(
    "검색기 유형을 선택하세요:",
    options=_retriever_keys,
    format_func=lambda x: retriever_options[x],
    index=_retriever_index,
)

user_top_n = st.slider(
    "검색할 테이블 정보 개수:",
    min_value=1,
    max_value=20,
    value=int(st.session_state.get("default_top_n", 5)),
    step=1,
    help="검색할 테이블 정보의 개수를 설정합니다. 값이 클수록 더 많은 테이블 정보를 검색하지만 처리 시간이 길어질 수 있습니다.",
)

# st.sidebar.title("Output Settings")
# for key, label in SIDEBAR_OPTIONS.items():
#     st.sidebar.checkbox(label, value=True, key=key)

if st.button("쿼리 실행"):
    
    if enable_monitoring:
        st.markdown("---")
        st.subheader("🔄 LangGraph 노드 실행 모니터링")
        st.info("각 노드의 실행 과정을 실시간으로 확인하세요!")
        
        result = execute_query_with_monitoring(
            query=user_query,
            database_env=user_database_env,
            retriever_name=user_retriever,
            top_n=user_top_n,
            device=device,
        )
        
        st.markdown("---")
        st.subheader("✅ 실행 완료")
        
    else:
        result = execute_query(
            query=user_query,
            database_env=user_database_env,
            retriever_name=user_retriever,
            top_n=user_top_n,
            device=device,
        )
    
    # 데이터베이스가 연결되지 않은 경우 SQL만 표시
    if db is None:
        st.subheader("🔍 생성된 SQL 쿼리")
        generated_query = result.get("generated_query")
        if generated_query:
            query_text = (
                generated_query.content
                if hasattr(generated_query, "content")
                else str(generated_query)
            )
            st.code(query_text, language="sql")
        st.info("💡 실제 데이터베이스에 연결하면 쿼리 결과와 차트를 볼 수 있습니다.")
    else:
        display_result(res=result, database=db)
