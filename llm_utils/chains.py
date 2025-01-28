import os
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from .tools import get_table_info, get_column_info
from .llm_factory import get_llm

llm = get_llm(
    model_type="openai", model_name="gpt-4o", openai_api_key=os.getenv("OPENAI_API_KEY")
)


# ToolChoiceChain
def create_tool_choice_chain(llm):
    tool_choice_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """
                너는 User Input에 대해 관련된 테이블, 컬럼을 찾는 Assistance이다.
                """,
            ),
            MessagesPlaceholder(variable_name="user_input"),
            (
                "system",
                """
                위의 질의와 관련된 테이블을 찾아주세요
                다음 tool을 사용할 수 있습니다:
                get_table_info - 전체 table_name과 table_description을 가져옵니다.
                get_column_info - table_name을 input으로 넣으면 column_name과 column description을 가져옵니다.
                아래 툴을 사용해주세요
                """,
            ),
            MessagesPlaceholder(variable_name="tool_choice"),
        ]
    )

    tools = [get_table_info, get_column_info]

    return tool_choice_prompt | llm.bind_tools(tools)


# TableFilterChain
def create_table_filter_chain(llm):
    table_filter_prompt = ChatPromptTemplate.from_messages(
        [
            MessagesPlaceholder(variable_name="user_input"),
            (
                "system",
                """
                너는 위의 User Input에 대해 관련된 테이블을 찾는 Assistance이다.
                아래 테이블 목록을 참고해서 관련된 테이블을 찾아주세요.
                참고사항은 
                    dim_~: 테이블은 metadata 테이블임
                    fact_~: 테이블은 실제 데이터가 저장된 테이블임
                    stg_~: 테이블은 데이터 적재 테이블임
                응답형태는 'table_name - table_description' 형태로 출력해주세요.
                최소 2개 이상의 테이블을 출력해주세요.
                테이블 목록은 다음과 같습니다:
                """,
            ),
            MessagesPlaceholder(variable_name="searched_tables"),
        ]
    )
    return table_filter_prompt | llm


# QueryMakerChain
def create_query_maker_chain(llm):
    query_maker_prompt = ChatPromptTemplate.from_messages(
        [
            MessagesPlaceholder(variable_name="user_input"),
            ("system", "너는 위의 User Input에 대해 쿼리를 작성하는 Assistance이다."),
            ("system", "다음 테이블과 컬럼을 참고해서 쿼리를 작성해주세요."),
            ("system", "테이블 목록은 다음과 같습니다:"),
            MessagesPlaceholder(variable_name="searched_tables"),
            ("system", "컬럼 목록은 다음과 같습니다:"),
            MessagesPlaceholder(variable_name="searched_columns"),
            (
                "system",
                """최종 형태는 반드시 아래와 같아야합니다.
                최종 쿼리:
                    SELECT COUNT(DISTINCT user_id) FROM stg_users WHERE user_id = 1
                참고한 테이블 목록:
                    stg_users, dim_users
                참고한 컬럼 목록:
                    stg_users.user_id, dim_users.user_id
                """,
            ),
        ]
    )
    return query_maker_prompt | llm


tool_choice_chain = create_tool_choice_chain(llm)
table_filter_chain = create_table_filter_chain(llm)
query_maker_chain = create_query_maker_chain(llm)
