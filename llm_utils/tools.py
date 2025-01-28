from typing import List, Dict

from langchain.tools import tool

from data_utils.datahub_source import DatahubMetadataFetcher

fetcher = DatahubMetadataFetcher()


@tool
def get_table_info() -> Dict[str, str]:
    """전체 테이블 이름과 설명을 가져오는 함수"""
    urns = fetcher.get_urns()
    table_info = {}
    for urn in urns:
        table_name = fetcher.get_table_name(urn)
        table_description = fetcher.get_table_description(urn)
        if table_name and table_description:
            table_info[table_name] = table_description
    return table_info


@tool
def get_column_info(table_name: str) -> List[Dict[str, str]]:
    """table_name에 해당하는 컬럼 이름과 설명을 가져오는 함수"""
    urns = fetcher.get_urns()
    for urn in urns:
        if fetcher.get_table_name(urn) == table_name:
            return fetcher.get_column_names_and_descriptions(urn)
    return []


@tool
def optimize_query(query: str) -> str:
    """생성된 쿼리 최적화"""
    # 쿼리 최적화 로직 추가 (예: 인덱스 사용, 조건 추가 등)
    optimized_query = query  # 예시로 동일한 쿼리 반환
    return optimized_query
