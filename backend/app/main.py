from fastapi import FastAPI
from pydantic import BaseModel
from app.agent.agent import ask_agent

# starting the API server
app = FastAPI()

# Requesting the modal structure
class ChatRequest(BaseModel):
    question: str

# when someome visits,it returns a json resposne(confirms server running)
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
    