import streamlit as st
from langchain_core.messages import HumanMessage
from llm_utils.graph import builder

# Streamlit 앱 제목
st.title("AutoSQL")

# 사용자 입력 받기
user_query = st.text_area(
    "쿼리를 입력하세요:",
    value="고객 데이터를 기반으로 유니크한 유저 수를 카운트하는 쿼리",
)


# Token usage 집계 함수 정의
def summarize_total_tokens(data):
    total_tokens = 0
    for item in data:
        print(item)
        token_usage = getattr(item, "usage_metadata", {})
        total_tokens += token_usage.get("total_tokens", 0)
    return total_tokens


# 버튼 클릭 시 실행
if st.button("쿼리 실행"):
    # 그래프 컴파일 및 쿼리 실행
    graph = builder.compile()
    human_message = HumanMessage(content=user_query)
    res = graph.invoke(input=human_message)
    total_tokens = summarize_total_tokens(res)

    # 결과 출력
    st.write("총 토큰 사용량:", total_tokens)
    st.write("결과:", res[-1].content)
