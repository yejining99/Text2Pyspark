"""
LangGraph 워크플로우를 Streamlit에서 구성하고 세션에 적용하는 페이지.

기능 개요:
- 프리셋(기본/확장) 또는 커스텀 토글로 노드 시퀀스를 구성
- QUERY_MAKER 포함 여부를 토글하여 마지막 노드를 제어
- 선택이 바뀌면 즉시 컴파일된 그래프를 세션 상태에 반영
- 현재 적용된 그래프 설정을 확인 가능
"""

from typing import List

import streamlit as st
from langgraph.graph import StateGraph, END

from llm_utils.graph_utils.base import (
    QueryMakerState,
    GET_TABLE_INFO,
    PROFILE_EXTRACTION,
    CONTEXT_ENRICHMENT,
    QUERY_MAKER,
    get_table_info_node,
    profile_extraction_node,
    context_enrichment_node,
    query_maker_node,
)


def build_selected_sequence(
    preset: str, use_profile: bool, use_context: bool
) -> List[str]:
    """
    프리셋과 커스텀 토글에 따라 실행할 노드 시퀀스를 생성합니다.

    Args:
        preset (str): "기본" | "확장" | "커스텀" 중 하나
        use_profile (bool): 커스텀에서 PROFILE_EXTRACTION 포함 여부
        use_context (bool): 커스텀에서 CONTEXT_ENRICHMENT 포함 여부

    Returns:
        List[str]: 노드 식별자들의 실행 순서
    """
    sequence: List[str] = [GET_TABLE_INFO]

    if preset == "기본":
        sequence += [QUERY_MAKER]
    elif preset == "확장":
        sequence += [PROFILE_EXTRACTION, CONTEXT_ENRICHMENT, QUERY_MAKER]
    else:
        if use_profile:
            sequence.append(PROFILE_EXTRACTION)
        if use_context:
            sequence.append(CONTEXT_ENRICHMENT)
        sequence.append(QUERY_MAKER)

    return sequence


def build_state_graph(sequence: List[str]) -> StateGraph:
    """
    주어진 시퀀스대로 노드를 추가하고, 인접 노드 간 엣지를 연결한 그래프 빌더를 반환합니다.

    마지막 노드는 항상 END로 연결합니다.

    Args:
        sequence (List[str]): 실행 순서에 따른 노드 식별자 목록

    Returns:
        StateGraph: 컴파일 전 그래프 빌더 객체
    """
    builder = StateGraph(QueryMakerState)
    builder.set_entry_point(GET_TABLE_INFO)

    # 노드 등록
    for node_id in sequence:
        if node_id == GET_TABLE_INFO:
            builder.add_node(GET_TABLE_INFO, get_table_info_node)
        elif node_id == PROFILE_EXTRACTION:
            builder.add_node(PROFILE_EXTRACTION, profile_extraction_node)
        elif node_id == CONTEXT_ENRICHMENT:
            builder.add_node(CONTEXT_ENRICHMENT, context_enrichment_node)
        elif node_id == QUERY_MAKER:
            builder.add_node(QUERY_MAKER, query_maker_node)

    # 엣지 연결
    for i in range(len(sequence) - 1):
        builder.add_edge(sequence[i], sequence[i + 1])

    # 종료 연결: 마지막 노드가 무엇이든 END로 연결
    if len(sequence) > 0:
        builder.add_edge(sequence[-1], END)

    return builder


def render_sequence(sequence: List[str]) -> str:
    """
    노드 시퀀스를 사람이 읽기 쉬운 문자열로 변환합니다.

    Args:
        sequence (List[str]): 실행 순서에 따른 노드 식별자 목록

    Returns:
        str: 예) "GET_TABLE_INFO → PROFILE_EXTRACTION → ..."
    """
    label_map = {
        GET_TABLE_INFO: "GET_TABLE_INFO",
        PROFILE_EXTRACTION: "PROFILE_EXTRACTION",
        CONTEXT_ENRICHMENT: "CONTEXT_ENRICHMENT",
        QUERY_MAKER: "QUERY_MAKER",
    }
    return " → ".join(label_map[s] for s in sequence)


st.title("LangGraph 구성 UI")
st.caption("기본/확장/커스텀으로 StateGraph를 구성하고 세션에 적용합니다.")

preset = st.radio("프리셋 선택", ("기본", "확장", "커스텀"), horizontal=True)

use_profile = False
use_context = False
if preset == "커스텀":
    st.subheader("커스텀 옵션")
    use_profile = st.checkbox("PROFILE_EXTRACTION 포함", value=True)
    use_context = st.checkbox("CONTEXT_ENRICHMENT 포함", value=True)
    use_query_maker = st.checkbox("QUERY_MAKER 포함", value=True)
else:
    # 프리셋에서는 QUERY_MAKER 자동 포함
    use_query_maker = True

# GET_TABLE_INFO 설정
st.subheader("GET_TABLE_INFO 설정")
_prev_cfg = st.session_state.get("graph_config", {})

_retriever_options = {
    "기본": "벡터 검색 (기본)",
    "Reranker": "Reranker 검색 (정확도 향상)",
}
_retriever_keys = list(_retriever_options.keys())
_retriever_default = _prev_cfg.get("retriever_name", "기본")
_retriever_index = (
    _retriever_keys.index(_retriever_default)
    if _retriever_default in _retriever_keys
    else 0
)

retriever_name = st.selectbox(
    "테이블 검색기",
    options=_retriever_keys,
    format_func=lambda x: _retriever_options[x],
    index=_retriever_index,
)

top_n = st.slider(
    "검색할 테이블 정보 개수",
    min_value=1,
    max_value=20,
    value=int(_prev_cfg.get("top_n", 5)),
    step=1,
)

_device_options = ["cpu", "cuda"]
_device_default = _prev_cfg.get("device", "cpu")
_device_index = (
    _device_options.index(_device_default) if _device_default in _device_options else 0
)
device = st.selectbox(
    "모델 실행 장치",
    options=_device_options,
    index=_device_index,
)


def build_sequence_with_qm(
    preset: str, use_profile: bool, use_context: bool, use_qm: bool
) -> List[str]:
    """
    QUERY_MAKER 포함 여부를 반영하여 시퀀스를 생성합니다.

    - use_qm=False면 마지막 노드는 반드시 GET_TABLE_INFO입니다.
    - use_qm=True면 프리셋/커스텀 로직에 따라 마지막 노드는 QUERY_MAKER가 됩니다.

    Args:
        preset (str): "기본" | "확장" | "커스텀" 중 하나
        use_profile (bool): PROFILE_EXTRACTION 포함 여부(커스텀 전용)
        use_context (bool): CONTEXT_ENRICHMENT 포함 여부(커스텀 전용)
        use_qm (bool): QUERY_MAKER 포함 여부

    Returns:
        List[str]: 노드 식별자들의 실행 순서
    """
    # QUERY_MAKER가 비활성화되면 마지막 노드는 반드시 GET_TABLE_INFO
    if not use_qm:
        return [GET_TABLE_INFO]
    # 활성화된 경우 프리셋/커스텀 구성에 따라 마지막 노드는 QUERY_MAKER
    base_seq = build_selected_sequence(preset, use_profile, use_context)
    return base_seq


sequence = build_sequence_with_qm(preset, use_profile, use_context, use_query_maker)

st.subheader("실행 순서")
st.write(render_sequence(sequence))

st.subheader("그래프 생성")
config = {
    "preset": preset,
    "use_profile": use_profile,
    "use_context": use_context,
    "use_query_maker": use_query_maker,
    "retriever_name": retriever_name,
    "top_n": top_n,
    "device": device,
}

# 선택이 바뀌면 자동으로 세션 그래프 갱신
prev_config = st.session_state.get("graph_config")
if ("graph" not in st.session_state) or (prev_config != config):
    _builder = build_state_graph(sequence)
    st.session_state["graph"] = _builder.compile()
    st.session_state["graph_config"] = config
    # Lang2SQL 메인 UI에서 기본값으로 사용할 옵션 전달
    st.session_state["default_retriever_name"] = retriever_name
    st.session_state["default_top_n"] = top_n
    st.session_state["default_device"] = device
    st.info("그래프가 세션에 적용되었습니다.")

# 수동 새로고침 버튼
if st.button("세션 그래프 새로고침"):
    _builder = build_state_graph(sequence)
    st.session_state["graph"] = _builder.compile()
    st.session_state["graph_config"] = config
    st.session_state["default_retriever_name"] = retriever_name
    st.session_state["default_top_n"] = top_n
    st.session_state["default_device"] = device
    st.success("세션 그래프가 새로고침되었습니다.")

with st.expander("현재 세션 그래프 설정"):
    st.json(st.session_state.get("graph_config", {}))

st.markdown("---")
st.subheader("💡 실시간 모니터링 활용 팁")
st.write("""
**🔍 실시간 노드 실행 모니터링 기능을 활용하면:**

1. **노드별 실행 시간** 확인 가능
2. **각 노드의 입력/출력값** 실시간 확인
3. **실행 진행률** 시각화
4. **에러 발생 시점** 정확한 파악

Lang2SQL 메인 페이지에서 "실시간 노드 실행 모니터링" 체크박스를 활성화하여 사용하세요!
""")