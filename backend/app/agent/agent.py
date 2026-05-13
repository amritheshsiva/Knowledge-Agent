from langchain.agents import create_agent

from app.agent.mcp_servers import get_mcp_tools
from app.agent.prompts import SYSTEM_PROMPT
from app.agent.rag_chain import llm
from app.agent.config import (GITHUB_OWNER,GITHUB_REPO)


async def ask_agent(question: str):

    tools = await get_mcp_tools()

    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=SYSTEM_PROMPT
    )

    response = await agent.ainvoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": f"""
                    GitHub Repository Owner:{GITHUB_OWNER}
                    GitHub Repository Name:{GITHUB_REPO}
                    User Question:{question}
"""
                }
            ]
        }
    )

    return response["messages"][-1].content