from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import text
from .database import engine, Base
from . import models, agent_utils

# Ensure pgvector extension exists before creating tables
with engine.connect() as conn:
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    conn.commit()

# Create database tables
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

import asyncio
import json
from fastapi.responses import StreamingResponse

class ChatRequest(BaseModel):
    message: str

@app.post("/chat")
async def chat_with_chief(request: ChatRequest):
    # Pass to the async AutoGen agent processor
    response_content = await agent_utils.process_user_message(request.message)
    return {"response": response_content}

@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    async def event_generator():
        queue = asyncio.Queue()
        # Start AutoGen chat in background
        task = asyncio.create_task(agent_utils.process_user_message_stream(request.message, queue))
        
        while True:
            msg = await queue.get()
            if msg is None: # End of stream
                break
            # Yield SSE format
            yield f"data: {json.dumps(msg)}\n\n"
            
        await task
        
    return StreamingResponse(event_generator(), media_type="text/event-stream")
