import asyncio

from app.agent.mcp_servers import get_mcp_tools


async def main():

    tools = await get_mcp_tools()

    for tool in tools:

        if tool.name == "get_file_contents":

            result = await tool.ainvoke(
                {
                    "owner": "amritheshsiva",
                    "repo": "CineX",
                    "path": ""
                }
            )

            print(result)


asyncio.run(main())