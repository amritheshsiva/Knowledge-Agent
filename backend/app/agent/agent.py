from langchain_core.messages import HumanMessage, SystemMessage
from langchain.agents import create_agent
from app.agent.mcp_servers import get_mcp_tools, get_github_tools, get_notion_tools
from app.agent.rag_chain import llm
from app.agent.config import GITHUB_OWNER, GITHUB_REPO, NOTION_PAGE_ID
from app.agent.prompts import SYSTEM_PROMPT
from app.memory.rag_memory import save_memory, retrieve_memory
from app.agent.synthesis import synthesize
from app.agent.conflict import detect_conflict
import json


# ── Helpers ───────────────────────────────────────────────────────────────────

def _has_raw_tool_call(text: str) -> bool:
    return "<function=" in text or "</function>" in text

#   Converts retrieved memory into formatted(Que,Ans) context
def _build_memory_context(memories) -> str:
    context = ""
    for memory in memories:
        answer = memory["answer"]
        if _has_raw_tool_call(answer):
            continue
        if answer:
            context += f"Q: {memory['question']}\nA: {answer}\n---\n"
        else:
            context += f"User said: {memory['question']}\n---\n"
    return context


def _is_project_question(question: str) -> bool:
    """
    Force REPO route for questions containing project-related keywords.
    These questions must always hit live GitHub/Notion — never served from cache.
    """
    keywords = [
        "cinex", "project hub", "timeline", "development timeline",
        "when did i", "how long did", "started", "completed",
        "challenges", "features", "tech stack", "what i learned",
        "future improvements", "folder structure", "my project",
        "what did i learn", "what are the features", "what is the status",
        "who developed", "developer", "what i built", "i built",
        "my app", "my repo", "repository", "codebase", "source code",
        "components", "pages", "routes", "dependencies", "package",
        "deployment", "vercel", "improvements", "what did you learn",
        "app.js", "index.js", "code", "src","repository","repo","folder",
        "folder structure","project structure","architecture","frontend",
        "backend","app.js","index.js","src","package.json","commit","commits",
        "recent changes","latest changes","pull request","issue","github",
        "codebase","react",
    ]
    q = question.lower()
    return any(k in q for k in keywords)

# use llm to classify - REPO/GENERAL que
async def _classify_question(question: str) -> str:
    response = await llm.ainvoke([
        SystemMessage(content="""
You are a router that classifies user questions.

Classify into exactly one of:

- REPO: user asks about a GitHub repository, codebase, project structure,
  files, folders, tech stack, components, code, frameworks, dependencies,
  OR asks about a project's features, challenges, timeline, status, goals,
  what they learned, or anything about a specific named project like CineX,
  OR anything about "CineX Project Hub", development timeline, project history.
  Examples:
  "What does this project do?"
  "What files are in the src folder?"
  "What framework does this app use?"
  "What does App.js contain?"
  "What challenges did I face?"
  "What did I learn from building this?"
  "What are the features of CineX?"
  "What is the status of CineX?"
  "Tell me everything about CineX"
  "What is my development timeline?"
  "Development timeline of CineX Project Hub"
  "When did I start CineX?"
  "How long did CineX take to build?"
  "What are future improvements for CineX?"
  "Who developed CineX?"

- GENERAL: anything else — general knowledge, facts, definitions.
  Examples:
  "What is React?"
  "What is in a burger?"
  "What is the capital of France?"

Reply with ONLY one word: REPO or GENERAL
"""),
        HumanMessage(content=question)
    ])

    route = response.content.strip().upper()
    if route not in ("REPO", "GENERAL"):
        return "GENERAL"
    return route


def _is_statement(question: str) -> bool:
    """
    Returns True only for genuine statements (facts the user is sharing),
    NOT for short noun-phrase questions like "Features of CineX".
    """
    q = question.strip().lower()

    # Short phrases (<=3 words) are almost always questions, not statements.
    if len(q.split()) <= 3:
        return False

    question_starters = (
        "what", "who", "where", "when", "why", "how",
        "is", "are", "do", "does", "did", "can", "could",
        "will", "would", "should", "which", "tell me",
        "explain", "describe", "show me", "list", "give me",
        "summarize", "features", "challenges", "timeline",
    )

    if q.endswith("?"):   
        return False

    if any(q.startswith(s) for s in question_starters):
        return False

    return True

# raw Notion --> readable text
def _parse_notion_blocks(blocks_result) -> str:
    """Parse Notion blocks result into clean readable text."""
    try:
        raw = blocks_result[0]["text"] if blocks_result else "" # gets raw json
        data = json.loads(raw)  #json --> python dict
        blocks = data.get("results", [])  # get all notion block

        page_content = ""
        for block in blocks:
            block_type = block.get("type", "") # gets block type-heading,paragraph,buletin,etc
            type_data = block.get(block_type, {}) 
            rich_text = type_data.get("rich_text", [])
            text = "".join([t.get("plain_text", "") for t in rich_text])

            if not text:   # skips empty blocks
                continue

# Formats different block types ,eg: #-h1,##-2,etc
            if block_type == "heading_1":
                page_content += f"\n# {text}\n"
            elif block_type == "heading_2":
                page_content += f"\n## {text}\n"
            elif block_type == "heading_3":
                page_content += f"\n### {text}\n"
            elif block_type == "bulleted_list_item":
                page_content += f"- {text}\n"
            elif block_type == "numbered_list_item":
                page_content += f"• {text}\n"
            elif block_type == "paragraph":
                page_content += f"{text}\n"
            elif block_type == "code":
                page_content += f"```\n{text}\n```\n"

        return page_content

    except Exception as e:
        print(f"Error parsing notion blocks: {e}")
        return ""


def _extract_agent_answer(response: dict) -> str:
    """
    Safely extract the final text answer from create_agent response.
    create_agent returns {"messages": [AIMessage, ToolMessage, AIMessage, ...]}
    We want the last message with real text content (not a raw tool call).
    """
    messages = response.get("messages", [])

    # Walk backwards — last real text message is the final answer
    for msg in reversed(messages):
        content = msg.content if hasattr(msg, "content") else str(msg)
        if content and content.strip() and not _has_raw_tool_call(content):
            return content

    return ""


# ── Main Agent ────────────────────────────────────────────────────────────────

async def ask_agent(question: str):

    print(f"\n{'='*60}")
    print(f"QUESTION: {question}")
    print(f"{'='*60}")

    # ── STEP 1: IF STATEMENT → SAVE AND RESPOND ──────────────────────────────
    if _is_statement(question):
        print("DETECTED AS STATEMENT — SAVING TO MEMORY")

        save_memory(question, "")

        response = await llm.ainvoke([
            SystemMessage(content="""
                          You are a helpful AI assistant.
                          The user is sharing information about themselves.
                          Acknowledge it briefly and naturally in one sentence.
                          """),
            HumanMessage(content=question)
        ])
        final_answer = response.content
        save_memory(question, final_answer)
        return final_answer

    # ── STEP 2: SEARCH CHROMADB FOR SIMILAR Previous Conversations──────────────────
    memories = retrieve_memory(question)   # from rag_memory.py
    memory_context = _build_memory_context(memories)
    has_relevant_memory = len(memories) > 0
    print(f"MEMORIES FOUND: {len(memories)}")
    print(f"MEMORY CONTEXT:\n{memory_context}")

    # Project questions ALWAYS bypass memory and hit live sources.
    # Prevents stale cached answers from being returned for codebase/Notion questions.
    if has_relevant_memory and _is_project_question(question):
        print("PROJECT QUESTION DETECTED — BYPASSING MEMORY, FORCING LIVE REPO ROUTE")
        has_relevant_memory = False

    # ── STEP 3: IF MEMORY FOUND → ANSWER FROM IT ─────────────────────────────
    if has_relevant_memory:
        print("CHECKING IF MEMORY IS ENOUGH TO ANSWER")

        check_response = await llm.ainvoke([
            SystemMessage(content="""
You are a helpful AI assistant with memory.

You will be given previous conversation memories and a current question.

IMPORTANT:
- If the memories contain ANY information related to the question,
  use it to answer directly.
- Treat every "User said:" entry as a confirmed fact about the user.
- NEVER use general knowledge if the answer exists in memories.
- NEVER say you don't know if a relevant memory exists.
- Only reply MEMORY_NOT_ENOUGH if the memories have absolutely zero
  relation to the question.

Do not explain. Just answer or say MEMORY_NOT_ENOUGH.
"""),
            HumanMessage(content=f"""
                         Previous Memories:
                         {memory_context}
                         Current Question:
                         {question}
""")
])

        memory_answer = check_response.content.strip()
        print(f"MEMORY ANSWER: {memory_answer}")

        if "MEMORY_NOT_ENOUGH" not in memory_answer:
            print("ANSWERED FROM MEMORY")
            save_memory(question, memory_answer)
            return memory_answer

        print("MEMORY NOT ENOUGH — ROUTING FURTHER")

    # ── STEP 4: CLASSIFY → REPO OR GENERAL ───────────────────────────────────
    if _is_project_question(question):
        route = "REPO"
        print("ROUTE: REPO (keyword match)")
    else:
        route = await _classify_question(question)
        print(f"ROUTE: {route} (LLM classifier)")

    # ── REPO FLOW ─────────────────────────────────────────────────────────────
    if route == "REPO":
        print("\n--- REPO FLOW ---")
        # To Load Github and Notion Tools
        github_tools = await get_github_tools()
        notion_tools = await get_notion_tools()
        # Force repository root inspection first
        try:
            #First calls get_file_contents tool,returns top-level folders/files
            root_tool = next(   
                t for t in github_tools
                if "get_file_contents" in t.name
                )
            root_result = await root_tool.ainvoke({
                "owner": GITHUB_OWNER,
                "repo": GITHUB_REPO,
                "path": ""
                })
            print("\nROOT REPOSITORY STRUCTURE:")
            print(root_result)
            
        except Exception as e:
            print(f"Failed to inspect repository root: {e}")

        # ── Query GitHub via create_agent ─────────────────────────────────────
        github_answer = ""
        try:
            
            github_agent = create_agent(
                model=llm,
                tools=github_tools,
                system_prompt=SYSTEM_PROMPT,
            )

            github_response = await github_agent.ainvoke({
                "messages": [{
                    "role": "user",
                    "content": (
                        f"Owner: {GITHUB_OWNER}\n"
                        f"Repo: {GITHUB_REPO}\n"
                        f"Repository Root Structure:\n{root_result}\n\n"
                        f"Question: {question}"
                    )
                }]
            })

            github_answer = _extract_agent_answer(github_response)
            print(f"\nGITHUB ANSWER (preview): {github_answer[:200]}...")

        except Exception as e:
            print(f"❌ GitHub error: {e}")
            import traceback
            traceback.print_exc()

        # ── Query Notion (direct tool call — no agent needed) ─────────────────
        notion_answer = ""
        try:
            notion_tools_map = {t.name: t for t in notion_tools}
            print(f"NOTION TOOLS AVAILABLE: {list(notion_tools_map.keys())}")

            blocks_tool = notion_tools_map.get("notion__API-get-block-children")

            if not blocks_tool:
                print(
                    f"❌ CRITICAL: 'notion__API-get-block-children' not found.\n"
                    f"   Available tools: {list(notion_tools_map.keys())}\n"
                    f"   Update NOTION_TOOL_NAMES in mcp_servers.py to match exact names above."
                )
            else:
                #directly fetches notion page
                blocks_result = await blocks_tool.ainvoke({  
                    "block_id": NOTION_PAGE_ID
                })

                page_content = _parse_notion_blocks(blocks_result)
                print(f"\nPARSED NOTION CONTENT (preview):\n{page_content[:500]}...")

                if page_content:
                    notion_response = await llm.ainvoke([
                        SystemMessage(content="""
You are a helpful assistant.
Answer the question using ONLY the Notion page content provided.
Do not use general knowledge.
Look carefully through ALL sections — tech stack, overview, features,
timeline, challenges, what I learned, future improvements, links.
If the answer is genuinely not anywhere in the content, say "Not found in Notion page."
"""),
                        HumanMessage(content=f"""
Notion page content:
{page_content}

Question: {question}
""")
                    ])
                    notion_answer = notion_response.content
                else:
                    print("⚠️ NO PAGE CONTENT PARSED FROM NOTION — check block structure")

            print(f"\nNOTION ANSWER (preview): {notion_answer[:200]}...")

        except Exception as e:
            print(f"❌ Notion error: {e}")
            import traceback
            traceback.print_exc()

        # ── Conflict Detection ────────────────────────────────────────────────
        sources = {
            "github": github_answer,
            "notion": notion_answer,
        }

        conflict = await detect_conflict(sources)
        if conflict["has_conflict"]:
            print(f"⚠️ CONFLICT DETECTED: {conflict['conflict_description']}")

        # ── Synthesize Final Answer ───────────────────────────────────────────
        final_answer = await synthesize(question, sources)

    # ── GENERAL FLOW ──────────────────────────────────────────────────────────
    else:
        print("\n--- GENERAL FLOW ---")
        response = await llm.ainvoke([
            SystemMessage(content="You are a helpful AI assistant."),
            HumanMessage(content=question)
        ])
        final_answer = response.content

    # ── STEP 5: SAVE FINAL ANSWER ─────────────────────────────────────────────
    if final_answer and not _has_raw_tool_call(final_answer):
        save_memory(question, final_answer)
    else:
        print("⚠️ Final answer empty or contains raw tool call — NOT saving to memory")

    print(f"\nFINAL ANSWER (preview): {final_answer[:200]}...")
    return final_answer