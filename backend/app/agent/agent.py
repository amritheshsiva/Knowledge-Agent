from langchain.agents import create_agent
from langchain_core.messages import HumanMessage, SystemMessage

from app.agent.mcp_servers import get_mcp_tools
from app.agent.rag_chain import llm
from app.agent.config import GITHUB_OWNER, GITHUB_REPO
from app.agent.prompts import SYSTEM_PROMPT
from app.memory.rag_memory import save_memory, retrieve_memory


def _has_raw_tool_call(text: str) -> bool:
    return "<function=" in text or "</function>" in text


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


async def _classify_question(question: str) -> str:
    response = await llm.ainvoke([
        SystemMessage(content="""
You are a router that classifies user questions.

Classify into exactly one of:

- REPO: user asks about a GitHub repository, codebase, project structure,
  files, folders, tech stack, components, code, frameworks, dependencies.
  Examples:
  "What does this project do?"
  "What files are in the src folder?"
  "What framework does this app use?"
  "What does App.js contain?"

- GENERAL: anything else — general knowledge, facts, definitions.
  Examples:
  "What is React?"
  "What is in a burger?"
  "Who is Batman?"
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
    Detects if the input is a statement/fact
    rather than a question.
    """
    q = question.strip().lower()

    # Questions usually start with these
    question_starters = (
        "what", "who", "where", "when", "why", "how",
        "is", "are", "do", "does", "did", "can", "could",
        "will", "would", "should", "which", "tell me",
        "explain", "describe", "show me", "list"
    )

    # If it ends with ? it's a question
    if q.endswith("?"):
        return False

    # If it starts with a question word it's a question
    if any(q.startswith(s) for s in question_starters):
        return False

    return True


async def ask_agent(question: str):

    print(f"\nQUESTION: {question}")

    # ── STEP 1: IF STATEMENT → SAVE AND RESPOND ───
    # e.g. "My laptop is Asus Tuf F15"
    # Save immediately and respond naturally
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

    # ── STEP 2: SEARCH CHROMADB FOR SIMILAR ───────
    memories = retrieve_memory(question)
    memory_context = _build_memory_context(memories)
    has_relevant_memory = len(memories) > 0
    print(f"MEMORIES FOUND: {len(memories)}")
    print(f"MEMORY CONTEXT:\n{memory_context}")

    # ── STEP 3: IF MEMORY FOUND → ANSWER FROM IT ──
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

    # ── STEP 4: CLASSIFY → REPO OR GENERAL ────────
    route = await _classify_question(question)
    print(f"ROUTE: {route}")

    # ── REPO FLOW ─────────────────────────────────
    if route == "REPO":
        print("USING REPO FLOW")
        tools = await get_mcp_tools()
        agent = create_agent(
            model=llm,
            tools=tools,
            system_prompt=SYSTEM_PROMPT
        )
        try:
            response = await agent.ainvoke({
                "messages": [{
                    "role": "user",
                    "content": f"Owner: {GITHUB_OWNER}\nRepo: {GITHUB_REPO}\nQuestion: {question}"
                }]
            })
            final_answer = response["messages"][-1].content
            if _has_raw_tool_call(final_answer):
                final_answer = (
                    "The model returned a raw tool call. Please try again."
                )
        except Exception as e:
            final_answer = f"Agent error: {e}"

    # ── GENERAL FLOW ──────────────────────────────
    else:
        print("USING GENERAL FLOW")
        response = await llm.ainvoke([
            SystemMessage(content="You are a helpful AI assistant."),
            HumanMessage(content=question)
        ])
        final_answer = response.content

    # ── STEP 5: SAVE FINAL ANSWER ─────────────────
    if final_answer and not _has_raw_tool_call(final_answer):
        save_memory(question, final_answer)

    return final_answer