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
    """Save a piece of knowledge to long-term database memory."""
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
    """Search the long-term database memory for context."""
    if not embedder: return "Memory system offline."
    try:
        db: Session = SessionLocal()
        query_embedding = embedder.encode(query).tolist()
        # Find top 3 most similar documents using pgvector
        results = db.query(DocumentEmbedding).order_by(
            DocumentEmbedding.embedding.l2_distance(query_embedding)
        ).limit(3).all()
        db.close()
        if not results: return "No relevant memory found."
        return "\n".join([r.content for r in results])
    except Exception as e:
        return f"Failed to search: {e}"

async def get_relevant_tools(query: str, all_tools: list) -> list:
    """Semantic Tool Router: Uses Groq to decide which tools to inject."""
    # Build a compact list of tools
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
        # Wrap requests.post in run_in_executor to not block event loop
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, lambda: requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=data))
        res_json = response.json()
        content = res_json['choices'][0]['message']['content']
        # Extract array (hacky but handles if LLM outputs an object instead)
        if "{" in content:
            parsed = json.loads(content)
            # Try to find a list value
            for v in parsed.values():
                if isinstance(v, list):
                    return v
            return []
        else:
            return json.loads(content)
    except Exception as e:
        print(f"Tool routing failed: {e}")
        return [t.name for t in all_tools[:2]] # Fallback to hack

async def process_user_message(message: str) -> str:
    try:
        # Save user message to basic Message history (Optional, but good practice)
        db = SessionLocal()
        db.add(Message(role="user", content=message))
        db.commit()
        db.close()
        
        async with AsyncExitStack() as stack:
            sessions = {}
            function_map = {
                "save_to_memory": save_to_memory,
                "search_memory": search_memory
            }
            agents = []
            
            # Setup User Proxy
            user_proxy = autogen.UserProxyAgent(
                name="UserProxy",
                human_input_mode="NEVER",
                max_consecutive_auto_reply=5,
                is_termination_msg=lambda x: x.get("content", "") and x.get("content", "").rstrip().endswith("TERMINATE"),
                code_execution_config={"use_docker": False}
            )

            # Initialize MCP Servers
            for s_cfg in servers_config:
                server_params = StdioServerParameters(
                    command=s_cfg["command"],
                    args=s_cfg["args"],
                    env=os.environ.copy()
                )
                
                try:
                    read, write = await stack.enter_async_context(stdio_client(server_params))
                    session = await stack.enter_async_context(ClientSession(read, write))
                    await session.initialize()
                    sessions[s_cfg["name"]] = session
                    
                    # Fetch tools
                    tools_resp = await session.list_tools()
                    
                    # SEMANTIC TOOL ROUTING
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
                    
                    # Only create agent if it has relevant tools
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
                    print(f"Warning: Failed to load MCP Server {s_cfg['name']}: {e}")
                    continue

            # Create Chief Coordinator with RAG memory tools
            chief_llm_config = llm_config_groq.copy()
            chief_llm_config["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": "search_memory",
                        "description": "Search the pgvector long-term database memory for past context or user preferences.",
                        "parameters": {
                            "type": "object",
                            "properties": {"query": {"type": "string", "description": "The search query"}},
                            "required": ["query"]
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "save_to_memory",
                        "description": "Save an important fact, summary, or user preference to long-term memory.",
                        "parameters": {
                            "type": "object",
                            "properties": {"content": {"type": "string", "description": "The fact to remember"}},
                            "required": ["content"]
                        }
                    }
                }
            ]
            
            # Inject auto-context
            past_context = search_memory(message)
            enriched_message = f"User Query: {message}\n\n[Retrieved Context from Memory]:\n{past_context}"
            
            chief_agent = autogen.AssistantAgent(
                name="ChiefCoordinator",
                system_message=(
                    "You are J.A.R.V.I.S., the Chief Coordinator. "
                    "You have direct access to database memory via save_to_memory and search_memory. "
                    "You delegate tasks to specialized agents if you need to use Notion or Google Workspace. "
                    "Once you have successfully executed the necessary tools, provide a helpful and professional final response. "
                    "Do NOT output the word TERMINATE unless the user's request is completely fulfilled."
                ),
                llm_config=chief_llm_config,
            )
            agents.append(chief_agent)
            
            # Register all tools to UserProxy
            user_proxy.register_function(function_map=function_map)
            
            if not agents:
                return "System Error: No AI agents could be initialized due to MCP failures."
                
            # GroupChat Setup
            groupchat = autogen.GroupChat(
                agents=[user_proxy] + agents,
                messages=[],
                max_round=10
            )
            manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=llm_config_groq)
            
            # Start chat
            await user_proxy.a_initiate_chat(manager, message=enriched_message)
            
            # Extract final response
            for msg in reversed(groupchat.messages):
                if msg.get("name") == "ChiefCoordinator" and msg.get("content") and "tool_calls" not in msg:
                    return msg["content"].replace("TERMINATE", "").strip()
                elif msg.get("role") == "assistant" and msg.get("content") and "tool_calls" not in msg:
                    return msg["content"].replace("TERMINATE", "").strip()
                
            return "Task execution finished."

    except Exception as e:
        import traceback
        return f"System Error: Failed to process MCP request. Details: {str(e)}\n\n{traceback.format_exc()}"
