import os
from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
    SystemMessagePromptTemplate,
)
from pydantic import BaseModel, Field

from llm_utils.llm import get_llm

from prompt.template_loader import get_prompt_template


llm = get_llm()


class QuestionProfile(BaseModel):
    is_timeseries: bool = Field(description="시계열 분석 필요 여부")
    is_aggregation: bool = Field(description="집계 함수 필요 여부")
    has_filter: bool = Field(description="조건 필터 필요 여부")
    is_grouped: bool = Field(description="그룹화 필요 여부")
    has_ranking: bool = Field(description="정렬/순위 필요 여부")
    has_temporal_comparison: bool = Field(description="기간 비교 포함 여부")
    intent_type: str = Field(description="질문의 주요 의도 유형")

# QueryMakerChain
def create_query_maker_chain(llm):
    # SystemPrompt만 yaml 파일로 불러와서 사용
    prompt = get_prompt_template("query_maker_prompt")
    query_maker_prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessagePromptTemplate.from_template(prompt),
            (
                "system",
                "아래는 사용자의 질문입니다:",
            ),
            MessagesPlaceholder(variable_name="user_input"),
            (
                "system",
                "다음은 사용자의 db 환경정보와 사용 가능한 테이블 및 컬럼 정보 와 예시쿼리 및 용어집 정보입니다:",
            ),
            MessagesPlaceholder(variable_name="user_database_env"),
            MessagesPlaceholder(variable_name="searched_tables"),
            (
                "system",
                "위 정보를 바탕으로 사용자 질문에 대한 최적의 SQL 쿼리를 최종 형태 예시와 같은 형태로 생성하세요.",
            ),
        ]
    )
    return query_maker_prompt | llm


def create_query_enrichment_chain(llm):
    prompt = get_prompt_template("query_enrichment_prompt")

    enrichment_prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessagePromptTemplate.from_template(prompt),
        ]
    )

    chain = enrichment_prompt | llm
    return chain


def create_profile_extraction_chain(llm):
    prompt = get_prompt_template("profile_extraction_prompt")

    profile_prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessagePromptTemplate.from_template(prompt),
        ]
    )

    chain = profile_prompt | llm.with_structured_output(QuestionProfile)
    return chain


query_maker_chain = create_query_maker_chain(llm)
profile_extraction_chain = create_profile_extraction_chain(llm)
query_enrichment_chain = create_query_enrichment_chain(llm)

if __name__ == "__main__":
    pass
