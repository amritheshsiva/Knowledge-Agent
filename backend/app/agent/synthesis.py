from langchain_core.messages import HumanMessage, SystemMessage
from app.agent.rag_chain import llm


async def synthesize(question: str, sources: dict) -> str:
    """
    Merges answers from multiple sources (github, notion) into one coherent answer.

    FIX: Previously, if one source returned an empty string, the LLM might
    treat both as equal weight and hallucinate. Now we explicitly tell the LLM
    which sources actually have content, and instruct it to rely only on those.
    """

    github_answer = sources.get("github", "").strip()
    notion_answer = sources.get("notion", "").strip()

    # Build a clear picture of what we actually have
    available_sources = []
    source_block = ""

    if github_answer:
        available_sources.append("GitHub")
        source_block += f"--- GitHub ---\n{github_answer}\n\n"

    if notion_answer:
        available_sources.append("Notion")
        source_block += f"--- Notion ---\n{notion_answer}\n\n"

    # Edge case: neither source returned anything useful
    if not available_sources:
        print("⚠️ SYNTHESIS: Both sources empty — returning fallback message")
        return (
            "I wasn't able to retrieve information from GitHub or Notion for this question. "
            "Please check that your MCP servers are running and your page/repo IDs are correct."
        )

    # Single source: no synthesis needed, just clean up and return
    if len(available_sources) == 1:
        print(f"SYNTHESIS: Only one source has content ({available_sources[0]}) — returning directly")
        only_answer = github_answer if github_answer else notion_answer
        return only_answer

    # Both sources have content: synthesize
    print(f"SYNTHESIS: Combining answers from {available_sources}")

    response = await llm.ainvoke([
        SystemMessage(content="""
You are a synthesis assistant. Your job is to combine information from multiple
sources into one clear, accurate answer.

RULES:
- Use ONLY the information provided in the source blocks below.
- Do NOT add general knowledge or make up anything not in the sources.
- If both sources say the same thing, say it once.
- If the sources say different things, present both perspectives clearly and note
  which source said what (e.g. "According to GitHub..." / "According to Notion...").
- If one source says something the other doesn't cover, include it.
- Be concise. Do not pad the answer.
- Never say "Based on my knowledge" — only "Based on the provided sources."
"""),
        HumanMessage(content=f"""
Question: {question}

Sources:
{source_block}

Please synthesize a single clear answer from the above sources.
""")
    ])

    synthesized = response.content.strip()
    print(f"SYNTHESIS RESULT (preview): {synthesized[:200]}...")
    return synthesized