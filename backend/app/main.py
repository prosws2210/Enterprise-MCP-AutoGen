from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from .database import engine, Base
from . import models, agent_utils

# Create database tables
# In production, use Alembic for migrations
Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI-POS Backend")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://192.168.1.102:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str

@app.get("/")
def read_root():
    return {"message": "AI-POS Backend is running"}

@app.post("/chat")
def chat_with_chief(request: ChatRequest):
    response_content = agent_utils.process_user_message(request.message)
    return {"response": response_content}
