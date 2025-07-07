import json

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
    query_maker_node_without_refiner,
)

"""
QUERY_REFINER 단계를 제거한 단순화된 워크플로우입니다.
GET_TABLE_INFO → PROFILE_EXTRACTION → CONTEXT_ENRICHMENT → QUERY_MAKER 순서로 실행됩니다.
초기 사용자 입력만을 사용하여 더 정확한 쿼리를 생성합니다.
"""

# StateGraph 생성 및 구성
builder = StateGraph(QueryMakerState)
builder.set_entry_point(GET_TABLE_INFO)

# 노드 추가
builder.add_node(GET_TABLE_INFO, get_table_info_node)
builder.add_node(PROFILE_EXTRACTION, profile_extraction_node)
builder.add_node(CONTEXT_ENRICHMENT, context_enrichment_node)
builder.add_node(QUERY_MAKER, query_maker_node_without_refiner)

# 기본 엣지 설정
builder.add_edge(GET_TABLE_INFO, PROFILE_EXTRACTION)
builder.add_edge(PROFILE_EXTRACTION, CONTEXT_ENRICHMENT)
builder.add_edge(CONTEXT_ENRICHMENT, QUERY_MAKER)

# QUERY_MAKER 노드 후 종료
builder.add_edge(QUERY_MAKER, END)
