from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.tools import StructuredTool

from decouple import config

def _safe_mcp_tool(tool):
    async def _call_tool(**kwargs):
        try:
            return await tool.ainvoke(kwargs)
        except Exception as exc:
            return (
                f"Tool error from {tool.name}: {exc}. "
                "The requested GitHub resource may not exist. "
                "Discover valid paths with get_file_contents using path=\"\", "
                "then retry with one of the returned paths."
            )

    return StructuredTool.from_function(
        coroutine=_call_tool,
        name=tool.name,
        description=(
            "Read a file or directory from the configured GitHub repository."
            if tool.name == "get_file_contents"
            else f"GitHub MCP tool: {tool.name}."
        ),
        args_schema=tool.args_schema,
    )

async def get_mcp_tools():
    client = MultiServerMCPClient(
        {
            "github": {
                "command": "npx",
                "args": [
                    "-y",
                    "@modelcontextprotocol/server-github"
                ],
                "env": {
                    "GITHUB_PERSONAL_ACCESS_TOKEN":
                    config("GITHUB_TOKEN"),

                    "GITHUB_REPO":
                    f"{config('GITHUB_OWNER')}/{config('GITHUB_REPO')}"
                },

                "transport": "stdio",
            }
        }
    )

    tools = await client.get_tools()

    return [
        _safe_mcp_tool(tool)
        for tool in tools
    ]
