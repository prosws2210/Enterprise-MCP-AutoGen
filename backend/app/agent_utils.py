import os
import autogen
import asyncio
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

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

async def process_user_message(message: str) -> str:
    try:
        async with AsyncExitStack() as stack:
            sessions = {}
            function_map = {}
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
                
                # Enter context managers
                read, write = await stack.enter_async_context(stdio_client(server_params))
                session = await stack.enter_async_context(ClientSession(read, write))
                await session.initialize()
                sessions[s_cfg["name"]] = session
                
                # Fetch tools
                tools_resp = await session.list_tools()
                tools_list = []
                
                for tool in tools_resp.tools[:2]: # Limit tools to prevent TPM crash
                    tools_list.append({
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": tool.description or "No description provided.",
                            "parameters": tool.inputSchema
                        }
                    })
                    
                    # Create async handler bound to this specific session
                    def create_tool_handler(tool_name, srv_session):
                        async def handler(**kwargs):
                            try:
                                res = await srv_session.call_tool(tool_name, arguments=kwargs)
                                if res.isError:
                                    return f"Error: {res.content}"
                                return str([c.text for c in res.content if hasattr(c, 'text')])
                            except Exception as e:
                                return f"Tool execution failed: {str(e)}"
                        return handler
                    
                    function_map[tool.name] = create_tool_handler(tool.name, session)
                
                # Create specialized agent for this MCP server
                agent_llm_config = llm_config_groq.copy()
                agent_llm_config["tools"] = tools_list
                
                specialized_agent = autogen.AssistantAgent(
                    name=f"{s_cfg['name']}Agent",
                    system_message=f"You are the {s_cfg['name']}Agent. You only have access to tools for {s_cfg['name']}. Answer the user's questions or perform actions related to {s_cfg['name']}. Provide a helpful response.",
                    llm_config=agent_llm_config,
                )
                agents.append(specialized_agent)

            # Create Chief Coordinator
            chief_agent = autogen.AssistantAgent(
                name="ChiefCoordinator",
                system_message=(
                    "You are J.A.R.V.I.S., the Chief Coordinator. "
                    "You delegate tasks to the specialized agents if necessary, or answer directly if you can. "
                    "Once you have successfully executed the necessary tools, provide a helpful and professional final response. "
                    "Do NOT output the word TERMINATE unless the user's request is completely fulfilled."
                ),
                llm_config=llm_config_groq, # No tools for chief directly
            )
            agents.append(chief_agent)
            
            # Register all tools to UserProxy
            user_proxy.register_function(function_map=function_map)
            
            # GroupChat Setup
            groupchat = autogen.GroupChat(
                agents=[user_proxy] + agents,
                messages=[],
                max_round=10
            )
            manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=llm_config_groq)
            
            # Start chat
            await user_proxy.a_initiate_chat(manager, message=message)
            
            # Extract final response
            for msg in reversed(groupchat.messages):
                if msg.get("name") == "ChiefCoordinator" and msg.get("content"):
                    return msg["content"].replace("TERMINATE", "").strip()
                elif msg.get("role") == "assistant" and msg.get("content") and "tool_calls" not in msg:
                    return msg["content"].replace("TERMINATE", "").strip()
                
            return "Task execution finished."

    except Exception as e:
        import traceback
        return f"System Error: Failed to process MCP request. Details: {str(e)}\n\n{traceback.format_exc()}"
