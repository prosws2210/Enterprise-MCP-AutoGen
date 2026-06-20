import os
import json
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Load configuration for MCP servers
MCP_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "mcp_config.json")

async def load_mcp_servers():
    if not os.path.exists(MCP_CONFIG_PATH):
        return {}
    
    with open(MCP_CONFIG_PATH, "r") as f:
        config = json.load(f)
        
    return config.get("mcpServers", {})

async def attach_mcp_tools_to_agent(agent, server_name: str, server_config: dict):
    """
    Connects to an MCP server via stdio and registers its tools with the provided AutoGen agent.
    Note: A persistent session manager is recommended in production.
    """
    command = server_config.get("command")
    args = server_config.get("args", [])
    env = server_config.get("env", {})
    
    # Merge env with current os.environ
    full_env = {**os.environ, **env}
    
    server_params = StdioServerParameters(
        command=command,
        args=args,
        env=full_env
    )
    
    # This context block connects to the MCP server.
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Fetch tools exposed by the MCP server
            tools_response = await session.list_tools()
            
            for tool in tools_response.tools:
                # Wrap the MCP tool call into a regular python function for AutoGen
                def mcp_tool_wrapper(**kwargs):
                    # We would use session.call_tool(tool.name, arguments=kwargs) here
                    return f"Executed {tool.name} via MCP (Mock implementation)"
                
                # Register the function with the agent
                agent.register_for_llm(name=tool.name, description=tool.description)(mcp_tool_wrapper)
                print(f"Registered MCP tool {tool.name} from {server_name} to Agent {agent.name}")
