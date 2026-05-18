import json
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.tools import StructuredTool
from decouple import config

# Cache tools so we don't reconnect on every request.
# FIX: Only cache when tools actually loaded successfully (non-empty list).
_cached_tools = None


def _safe_mcp_tool(tool, source: str):
    """
    Wraps an MCP tool with:
    - A namespaced name: "{source}__{tool.name}" (e.g. "notion__API-get-block-children")
    - Error handling so one failing tool doesn't crash the whole agent
    """
    async def _call_tool(**kwargs):
        try:
            return await tool.ainvoke(kwargs)
        except Exception as exc:
            return (
                f"Tool error from {tool.name} ({source}): {exc}. "
                "The requested resource may not exist."
            )

    return StructuredTool.from_function(
        coroutine=_call_tool,
        name=f"{source}__{tool.name}",
        description=f"[{source.upper()}] {tool.description}",
        args_schema=tool.args_schema,
    )


async def get_mcp_tools():
    """
    Connects to GitHub and Notion MCP servers and returns all available tools.
    Results are cached after the first successful (non-empty) load.

    FIX: Previously, an empty list would be cached if tools failed to load,
    causing every subsequent call to reuse the empty cache silently.
    Now we only cache when at least one tool was returned.
    """
    global _cached_tools

    # FIX: Use falsy check (not `is not None`) so empty list is never reused.
    if _cached_tools:
        return _cached_tools

    client = MultiServerMCPClient(
        {
            "github": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-github"],
                "env": {
                    "GITHUB_PERSONAL_ACCESS_TOKEN": config("GITHUB_TOKEN"),
                    "GITHUB_REPO": f"{config('GITHUB_OWNER')}/{config('GITHUB_REPO')}"
                },
                "transport": "stdio",
            },
            "notion": {
                "command": "npx",
                "args": ["-y", "@notionhq/notion-mcp-server"],
                "env": {
                    "OPENAPI_MCP_HEADERS": json.dumps({
                        "Authorization": f"Bearer {config('NOTION_TOKEN')}",
                        "Notion-Version": "2022-06-28",
                    })
                },
                "transport": "stdio",
            }
        }
    )

    tools = await client.get_tools()
    print(f"ALL TOOLS LOADED ({len(tools)}): {[t.name for t in tools]}")

    # FIX: Don't cache an empty list — something went wrong, let next call retry.
    if not tools:
        print(
            "⚠️ WARNING: No MCP tools loaded.\n"
            "   • Is Node.js installed and npx available?\n"
            "   • Are GITHUB_TOKEN and NOTION_TOKEN set in .env?\n"
            "   • Try running the MCP servers manually to check for errors.\n"
            "   NOT caching empty result — next call will retry."
        )
        return []

    _cached_tools = tools
    return tools


# ── Tool Name Allowlists ──────────────────────────────────────────────────────
# These must exactly match the tool names printed in "ALL TOOLS LOADED".
# If you see a mismatch, run the app once, copy the names from the log,
# and update these sets.

GITHUB_TOOL_NAMES = {
    "get_file_contents",
    "search_code",
    "list_commits",
    "list_pull_requests",
    "get_pull_request",
    "get_pull_request_files",
    "get_pull_request_status",
    "list_issues",
    "search_issues",
    "get_issue",
}

NOTION_TOOL_NAMES = {
    "API-retrieve-a-page",
    "API-get-block-children",
    "API-post-search",
}


# ── Tool Getters ──────────────────────────────────────────────────────────────

async def get_github_tools():
    """
    Returns only GitHub tools, wrapped with _safe_mcp_tool.
    Names become: "github__<original_tool_name>"
    """
    all_tools = await get_mcp_tools()
    github_tools = [
        _safe_mcp_tool(t, "github")
        for t in all_tools
        if t.name in GITHUB_TOOL_NAMES
    ]
    print(f"GITHUB TOOLS ({len(github_tools)}): {[t.name for t in github_tools]}")

    if not github_tools:
        print(
            "⚠️ WARNING: No GitHub tools matched.\n"
            f"   GITHUB_TOOL_NAMES has {len(GITHUB_TOOL_NAMES)} entries.\n"
            f"   Loaded tool names: {[t.name for t in all_tools]}\n"
            "   Update GITHUB_TOOL_NAMES to match the exact names above."
        )

    return github_tools


async def get_notion_tools():
    """
    Returns only Notion tools, wrapped with _safe_mcp_tool.
    Names become: "notion__<original_tool_name>"
    e.g. "notion__API-get-block-children"

    In agent.py, look up tools using these prefixed names:
        notion_tools_map.get("notion__API-get-block-children")
    """
    all_tools = await get_mcp_tools()
    notion_tools = [
        _safe_mcp_tool(t, "notion")
        for t in all_tools
        if t.name in NOTION_TOOL_NAMES
    ]
    print(f"NOTION TOOLS ({len(notion_tools)}): {[t.name for t in notion_tools]}")

    if not notion_tools:
        print(
            "⚠️ WARNING: No Notion tools matched.\n"
            f"   NOTION_TOOL_NAMES has {len(NOTION_TOOL_NAMES)} entries: {NOTION_TOOL_NAMES}\n"
            f"   Loaded tool names: {[t.name for t in all_tools]}\n"
            "   Update NOTION_TOOL_NAMES to match the exact names above."
        )

    return notion_tools


def clear_tool_cache():
    """
    Call this to force tools to reload on the next request.
    Useful after restarting MCP servers or changing credentials.

    Usage:
        from app.agent.mcp_servers import clear_tool_cache
        clear_tool_cache()
    """
    global _cached_tools
    _cached_tools = None
    print("Tool cache cleared — tools will reload on next request.")