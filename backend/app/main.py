from fastapi import FastAPI
from pydantic import BaseModel
from .database import engine, Base
from . import models, agent_utils

# Create database tables
# In production, use Alembic for migrations
Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI-POS Backend")

class ChatRequest(BaseModel):
    message: str

@app.get("/")
def read_root():
    return {"message": "AI-POS Backend is running"}

@app.post("/chat")
def chat_with_chief(request: ChatRequest):
    response_content = agent_utils.process_user_message(request.message)
    return {"response": response_content}
