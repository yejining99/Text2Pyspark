import os
import re
from datetime import datetime

from langchain_core.prompts import PromptTemplate
from langgraph.prebuilt.chat_agent_executor import AgentState


def get_prompt_template(prompt_name: str) -> str:
    try:
        with open(os.path.join(os.path.dirname(__file__), f"{prompt_name}.md"), "r", encoding="utf-8") as f:
            template = f.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"경고: '{prompt_name}.md' 파일을 찾을 수 없습니다.")
    return template

if __name__ == "__main__":
    print(get_prompt_template("system_prompt"))
    # print(apply_prompt_template("prompt_md_sample", {"messages": []}))