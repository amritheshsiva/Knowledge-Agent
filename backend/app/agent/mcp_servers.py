from langchain_mcp_adapters.client import MultiServerMCPClient
from decouple import config

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
                    "GITHUB_PERSONAL_ACCESS_TOKEN": config("GITHUB_TOKEN")
                },
                "transport": "stdio",
            }
        }
    )

    tools = await client.get_tools()

    return tools