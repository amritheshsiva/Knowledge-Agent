from langchain_groq import ChatGroq

from app.agent.config import (
    GROQ_API_KEY,
    MODEL_NAME
)

from app.agent.prompts import SYSTEM_PROMPT


llm = ChatGroq(
    groq_api_key=GROQ_API_KEY,
    model_name=MODEL_NAME
)