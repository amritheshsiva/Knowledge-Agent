from fastapi import FastAPI
from pydantic import BaseModel

from app.agent.agent import ask_agent

app = FastAPI()

class ChatRequest(BaseModel):
    question: str
@app.get("/")
def home():
    return {
        "message": "Backend running"
    }
@app.post("/chat")
async def chat(request: ChatRequest):

    answer = await ask_agent(request.question)

    return {
        "question": request.question,
        "answer": answer
    }