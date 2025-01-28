from langchain_core.messages import HumanMessage

from llm_utils.graph import builder

if __name__ == "__main__":
    graph = builder.compile()
    user_query = """
        고객 데이터를 기반으로 유니크한 유저 수를 카운트하는 쿼리
    """
    human_message = HumanMessage(content=user_query)
    res = graph.invoke(input=human_message)
