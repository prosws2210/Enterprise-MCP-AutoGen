import os
import autogen

# Load from env or use the one provided by user
os.environ["GROQ_API_KEY"] = os.environ.get("GROQ_API_KEY", "")

llm_config_groq = {
    "config_list": [
        {
            "model": "llama3-70b-8192", # Groq-supported model
            "api_key": os.environ.get("GROQ_API_KEY"),
            "base_url": "https://api.groq.com/openai/v1",
            "api_type": "openai"
        }
    ],
    "temperature": 0.2,
}

def create_chief_agent():
    chief_agent = autogen.AssistantAgent(
        name="ChiefAgent",
        system_message="You are the Chief Agent orchestrating tasks. You act as a digital chief of staff. Route tasks, delegate, and output the final plan or summary.",
        llm_config=llm_config_groq,
    )
    user_proxy = autogen.UserProxyAgent(
        name="UserProxy",
        human_input_mode="NEVER",
        max_consecutive_auto_reply=5,
        is_termination_msg=lambda x: x.get("content", "") and x.get("content", "").rstrip().endswith("TERMINATE"),
        code_execution_config={"use_docker": False}
    )
    return chief_agent, user_proxy

def process_user_message(message: str) -> str:
    chief, proxy = create_chief_agent()
    # In a real setup, we would capture the chat history to return it
    proxy.initiate_chat(chief, message=message)
    
    # Return the last message from the chief
    return chief.last_message()["content"]
