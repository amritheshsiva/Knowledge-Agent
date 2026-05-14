from langchain_core.messages import HumanMessage, SystemMessage
from app.agent.rag_chain import llm


async def detect_conflict(sources: dict) -> dict:
    """
    Checks whether GitHub and Notion answers contradict each other.

    Returns:
        {
            "has_conflict": bool,
            "conflict_description": str  # empty string if no conflict
        }
    """

    github_answer = sources.get("github", "").strip()
    notion_answer = sources.get("notion", "").strip()

    # No point checking conflict if one or both sources are empty
    if not github_answer or not notion_answer:
        return {
            "has_conflict": False,
            "conflict_description": ""
        }

    response = await llm.ainvoke([
        SystemMessage(content="""
You are a conflict detection assistant.

You will be given two answers about the same topic from different sources.
Your job is to determine if they CONTRADICT each other — not just differ in detail,
but actually say opposing things (e.g. different dates, different tech stacks,
different status, different people).

Reply in this exact format:
CONFLICT: YES or NO
DESCRIPTION: <one sentence describing the conflict, or "None" if no conflict>

Do not add anything else.
"""),
        HumanMessage(content=f"""
Source 1 (GitHub):
{github_answer}

Source 2 (Notion):
{notion_answer}
""")
    ])

    raw = response.content.strip()
    lines = raw.splitlines()

    has_conflict = False
    description = ""

    for line in lines:
        if line.upper().startswith("CONFLICT:"):
            value = line.split(":", 1)[-1].strip().upper()
            has_conflict = value == "YES"
        elif line.upper().startswith("DESCRIPTION:"):
            description = line.split(":", 1)[-1].strip()
            if description.lower() == "none":
                description = ""

    return {
        "has_conflict": has_conflict,
        "conflict_description": description,
    }