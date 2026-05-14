import asyncio

from app.agent.mcp_servers import get_mcp_tools


async def main():

    tools = await get_mcp_tools()

    print("\nAVAILABLE TOOLS:\n")

    for tool in tools:

        print(tool.name)
        print(tool.description)
        print("-------------------------")


asyncio.run(main())