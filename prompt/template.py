import os
import re
from datetime import datetime

from langchain_core.prompts import PromptTemplate
from langgraph.prebuilt.chat_agent_executor import AgentState


def get_prompt_template(prompt_name: str) -> str:
    template = open(os.path.join(os.path.dirname(__file__), f"{prompt_name}.md")).read()
    
    # Escape curly braces using backslash (중괄호를 문자로 처리)
    template = template.replace("{", "{{").replace("}", "}}")
    
    # Replace `<<VAR>>` with `{VAR}`
    template = re.sub(r"<<([^>>]+)>>", r"{\1}", template)
    return template


def apply_prompt_template(prompt_name: str, state: AgentState) -> list:
    system_prompt = PromptTemplate(
        input_variables=["CURRENT_TIME"],
        template=get_prompt_template(prompt_name),
    ).format(CURRENT_TIME=datetime.now().strftime("%a %b %d %Y %H:%M:%S %z"), **state)
    
    # system prompt template 설정
    return [{"role": "system", "content": system_prompt}] + state["messages"]


if __name__ == "__main__":
    print(get_prompt_template("prompt_md_sample"))
    # print(apply_prompt_template("prompt_md_sample", {"messages": []}))