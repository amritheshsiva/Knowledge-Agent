# test_mcp.py

import asyncio
from app.agent.mcp_servers import get_mcp_tools
async def main():
    tools = await get_mcp_tools()
    for tool in tools:
        print(tool.name)
asyncio.run(main())