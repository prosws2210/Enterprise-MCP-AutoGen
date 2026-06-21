import os
import autogen
import asyncio
import json
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import requests
from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session
from .database import SessionLocal
from .models import DocumentEmbedding, Message

# Ensure API Key is loaded
os.environ["GROQ_API_KEY"] = os.environ.get("GROQ_API_KEY", "")

llm_config_groq = {
    "config_list": [
        {
            "model": "llama-3.1-8b-instant", 
            "api_key": os.environ.get("GROQ_API_KEY"),
            "base_url": "https://api.groq.com/openai/v1",
            "api_type": "openai"
        }
    ],
    "temperature": 0.2,
}

# Initialize local embedding model
try:
    embedder = SentenceTransformer('all-MiniLM-L6-v2')
except Exception as e:
    print(f"Failed to load sentence-transformers: {e}")
    embedder = None

servers_config = [
    {
        "name": "Notion",
        "command": "npx",
        "args": ["-y", "@notionhq/notion-mcp-server"]
    },
    {
        "name": "GoogleWorkspace",
        "command": "npx",
        "args": ["-y", "mcp-google-workspace"]
    }
]

def save_to_memory(content: str) -> str:
    if not embedder: return "Memory system offline."
    try:
        db: Session = SessionLocal()
        embedding = embedder.encode(content).tolist()
        doc = DocumentEmbedding(content=content, embedding=embedding)
        db.add(doc)
        db.commit()
        db.close()
        return "Successfully saved to memory."
    except Exception as e:
        return f"Failed to save: {e}"

def search_memory(query: str) -> str:
    if not embedder: return "Memory system offline."
    try:
        db: Session = SessionLocal()
        query_embedding = embedder.encode(query).tolist()
        results = db.query(DocumentEmbedding).order_by(
            DocumentEmbedding.embedding.l2_distance(query_embedding)
        ).limit(3).all()
        db.close()
        if not results: return "No relevant memory found."
        return "\n".join([r.content for r in results])
    except Exception as e:
        return f"Failed to search: {e}"

async def get_relevant_tools(query: str, all_tools: list) -> list:
    tool_summaries = [f"- {t.name}: {t.description}" for t in all_tools]
    tool_text = "\n".join(tool_summaries)
    
    prompt = f"User query: '{query}'\n\nAvailable tools:\n{tool_text}\n\nReturn ONLY a JSON array of strings containing the exact names of the 1 to 3 most relevant tools to answer the user query. If none apply, return []. Do not output any markdown or other text."
    
    headers = {
        "Authorization": f"Bearer {os.environ['GROQ_API_KEY']}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0,
        "response_format": {"type": "json_object"}
    }
    
    try:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=data))
        res_json = response.json()
        content = res_json['choices'][0]['message']['content']
        if "{" in content:
            parsed = json.loads(content)
            for v in parsed.values():
                if isinstance(v, list):
                    return v
            return []
        else:
            return json.loads(content)
    except Exception as e:
        print(f"Tool routing failed: {e}")
        return [t.name for t in all_tools[:2]]

async def process_user_message_stream(message: str, queue: asyncio.Queue):
    """Processes the message and pushes updates to an asyncio Queue for SSE streaming."""
    try:
        db = SessionLocal()
        db.add(Message(role="user", content=message))
        db.commit()
        db.close()
        
        async with AsyncExitStack() as main_stack:
            sessions = {}
            function_map = {
                "save_to_memory": save_to_memory,
                "search_memory": search_memory
            }
            agents = []
            
            user_proxy = autogen.UserProxyAgent(
                name="UserProxy",
                human_input_mode="NEVER",
                max_consecutive_auto_reply=5,
                is_termination_msg=lambda x: x.get("content", "") and x.get("content", "").rstrip().endswith("TERMINATE"),
                code_execution_config={"use_docker": False}
            )

            # Robust MCP Initialization
            for s_cfg in servers_config:
                server_params = StdioServerParameters(
                    command=s_cfg["command"],
                    args=s_cfg["args"],
                    env=os.environ.copy()
                )
                
                server_stack = AsyncExitStack()
                try:
                    read, write = await server_stack.enter_async_context(stdio_client(server_params))
                    session = await server_stack.enter_async_context(ClientSession(read, write))
                    await session.initialize()
                    
                    # Transfer cleanup to the main stack
                    main_stack.push_async_callback(server_stack.aclose)
                    sessions[s_cfg["name"]] = session
                    
                    # Fetch tools
                    tools_resp = await session.list_tools()
                    relevant_tool_names = await get_relevant_tools(message, tools_resp.tools)
                    
                    tools_list = []
                    for tool in tools_resp.tools:
                        if tool.name in relevant_tool_names:
                            tools_list.append({
                                "type": "function",
                                "function": {
                                    "name": tool.name,
                                    "description": tool.description or "No description provided.",
                                    "parameters": tool.inputSchema
                                }
                            })
                            
                            def create_tool_handler(tool_name, srv_session):
                                async def handler(**kwargs):
                                    try:
                                        res = await srv_session.call_tool(tool_name, arguments=kwargs)
                                        if res.isError: return f"Error: {res.content}"
                                        return str([c.text for c in res.content if hasattr(c, 'text')])
                                    except Exception as e: return f"Tool execution failed: {str(e)}"
                                return handler
                            
                            function_map[tool.name] = create_tool_handler(tool.name, session)
                    
                    if tools_list:
                        agent_llm_config = llm_config_groq.copy()
                        agent_llm_config["tools"] = tools_list
                        
                        specialized_agent = autogen.AssistantAgent(
                            name=f"{s_cfg['name']}Agent",
                            system_message=f"You are the {s_cfg['name']}Agent. You only have access to tools for {s_cfg['name']}. Answer the user's questions or perform actions related to {s_cfg['name']}. Provide a helpful response.",
                            llm_config=agent_llm_config,
                        )
                        agents.append(specialized_agent)
                except Exception as e:
                    # Connection failed! Clean up the isolated stack and continue gracefully
                    await server_stack.aclose()
                    print(f"Warning: Failed to load MCP Server {s_cfg['name']}: {e}")
                    await queue.put({
                        "role": "system",
                        "name": "System",
                        "content": f"[Warning] The {s_cfg['name']} integration failed to connect and will be unavailable for this session."
                    })
                    continue

            # Chief Coordinator Setup
            chief_llm_config = llm_config_groq.copy()
            chief_llm_config["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": "search_memory",
                        "description": "Search the pgvector long-term database memory for past context or user preferences.",
                        "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "save_to_memory",
                        "description": "Save an important fact, summary, or user preference to long-term memory.",
                        "parameters": {"type": "object", "properties": {"content": {"type": "string"}}, "required": ["content"]}
                    }
                }
            ]
            
            past_context = search_memory(message)
            enriched_message = f"User Query: {message}\n\n[Retrieved Context from Memory]:\n{past_context}"
            
            chief_agent = autogen.AssistantAgent(
                name="ChiefCoordinator",
                system_message=(
                    "You are J.A.R.V.I.S., the Chief Coordinator. "
                    "You have direct access to database memory via save_to_memory and search_memory. "
                    "You delegate tasks to specialized agents if you need to use external tools. "
                    "CRITICAL: If a tool returns no results (e.g. 'No relevant memory found.'), DO NOT call it again with the same arguments. Accept the result and respond directly to the user. "
                    "Once you have answered the user or fulfilled their request, you MUST append the word TERMINATE to the very end of your final message to end the conversation."
                ),
                llm_config=chief_llm_config,
            )
            agents.append(chief_agent)
            user_proxy.register_function(function_map=function_map)
            
            if not agents:
                await queue.put({"role": "system", "name": "Error", "content": "System Error: No AI agents could be initialized due to MCP failures."})
                return
                
            # SSE Hook Function
            def capture_message(recipient, messages, sender, config):
                last_msg = messages[-1]
                # Filter out empty terminal messages
                if not last_msg.get("content") and not last_msg.get("tool_calls"):
                    return False, None
                
                # Push to async queue without blocking
                asyncio.create_task(queue.put({
                    "role": "agent" if sender.name != "UserProxy" else "system",
                    "name": sender.name,
                    "content": last_msg.get("content", ""),
                    "tool_calls": [t.get("function", {}).get("name") for t in last_msg.get("tool_calls", [])] if "tool_calls" in last_msg else []
                }))
                return False, None

            # Register hook on the manager so it captures all agent broadcasts
            groupchat = autogen.GroupChat(
                agents=[user_proxy] + agents,
                messages=[],
                max_round=15
            )
            manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=llm_config_groq)
            manager.register_reply([autogen.Agent, None], capture_message, position=1)
            
            # Initiate chat
            await user_proxy.a_initiate_chat(manager, message=enriched_message)
            
    except Exception as e:
        import traceback
        await queue.put({"role": "system", "name": "Error", "content": f"Critical Error: {str(e)}\n\n{traceback.format_exc()}"})
    finally:
        await queue.put(None) # Signal end of stream

# Keeping original method just for backward compatibility if needed
async def process_user_message(message: str) -> str:
    return "This endpoint has been replaced by /chat/stream"
