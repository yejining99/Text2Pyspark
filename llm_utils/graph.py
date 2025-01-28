from dotenv import load_dotenv

from typing import Sequence
from langchain_core.messages import BaseMessage
from langgraph.prebuilt import ToolNode
from langgraph.graph import END, MessageGraph

load_dotenv()

from llm_utils.chains import tool_choice_chain, table_filter_chain, query_maker_chain
from llm_utils.tools import get_table_info, get_column_info

TOOL_CHOICE = "tool_choice"
TOOL = "tool"
TABLE_FILTER = "table_filter"
QUERY_MAKER = "query_maker"
tool_node = ToolNode([get_table_info, get_column_info])


def tool_choice_node(state: Sequence[BaseMessage]):
    tool_choice = (
        state[-1].tool_choice if hasattr(state[-1], "tool_choice") else "get_table_info"
    )
    res = tool_choice_chain.invoke(
        input={"user_input": [state[-1].content], "tool_choice": [tool_choice]}
    )

    return res


def table_filter_node(state: Sequence[BaseMessage]):

    if state[-1].name == "get_table_info":
        res = table_filter_chain.invoke(
            input={
                "user_input": [state[0].content],
                "searched_tables": [state[-1].content],
            }
        )
        res.tool_choice = "get_column_info"
        return res

    elif len(state) >= 4:
        state[-1].is_end = True
        return state


def query_maker_node(state: Sequence[BaseMessage]):
    search_columns = [i.content for i in state if i.name == "get_column_info"]

    res = query_maker_chain.invoke(
        input={
            "user_input": [state[0].content],
            "searched_tables": [state[3].content],
            "searched_columns": search_columns,
        }
    )
    return res


# 조건부 경로 추가
def should_end(state: Sequence[BaseMessage]):
    # 종료 조건을 정의하는 함수
    return len(state) > 0 and hasattr(state[-1], "is_end") and state[-1].is_end


builder = MessageGraph()

builder.set_entry_point(TOOL_CHOICE)

builder.add_node(TOOL_CHOICE, tool_choice_node)
builder.add_node(TOOL, tool_node)
builder.add_node(TABLE_FILTER, table_filter_node)
builder.add_node(QUERY_MAKER, query_maker_node)

builder.add_edge(TOOL_CHOICE, TOOL)
builder.add_edge(TOOL, TABLE_FILTER)

builder.add_conditional_edges(
    source=TABLE_FILTER,
    path=should_end,
    path_map={True: QUERY_MAKER, False: TOOL_CHOICE},
)

builder.add_edge(QUERY_MAKER, END)
