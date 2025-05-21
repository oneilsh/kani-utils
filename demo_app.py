# Example usage of StreamlitKani

########################
##### 0 - load libs
########################

# kani_streamlit imports
import kani_utils.kani_streamlit_server as ks

# for reading API keys from .env file
import os
import dotenv # pip install python-dotenv

# kani imports
from kani.engines.openai import OpenAIEngine

# load app-defined agents
from demo_agents import AuthorSearchKani, MemoryKani, FileKani, TableKani, SystemPromptEditorKani


# read API keys .env file (e.g. set OPENAI_API_KEY=.... in .env and gitignore .env)
dotenv.load_dotenv() 

########################
##### 1 - Configuration
########################

# initialize the application and set some page settings
# parameters here are passed to streamlit.set_page_config, 
# see more at https://docs.streamlit.io/library/api-reference/utilities/st.set_page_config
# this function MUST be run first
ks.initialize_app_config(
    show_function_calls = True,
    show_function_calls_status = True,
    page_title = "StreamlitKani Demo",
    page_icon = "🦀", # can also be a URL
    initial_sidebar_state = "expanded", # or "collapsed"
    menu_items = {
            "Get Help": "https://github.com/.../issues",
            "Report a Bug": "https://github.com/.../issues",
            "About": "StreamlitKani is a Streamlit-based UI for Kani agents.",
        },
    share_chat_ttl_seconds = (60 * 60 * 24) * 60, # 60 days
)


########################
##### 2 - Define Agents
########################

# define an engine to use (see Kani documentation for more info)
engine = OpenAIEngine(os.environ["OPENAI_API_KEY"], model="gpt-4o")

# We also have to define a function that returns a dictionary of agents to serve
# Agents are keyed by their name, which is what the user will see in the UI
# cost is in dollars per 1000000 tokens
def get_agents():
    return {
            "Author Search Agent": AuthorSearchKani(engine, prompt_tokens_cost = 0.005, completion_tokens_cost = 0.015),
            "Author Search Agent (No costs shown)": AuthorSearchKani(engine),
            "Memory Agent": MemoryKani(engine, prompt_tokens_cost = 0.005, completion_tokens_cost = 0.015),
            "File Agent": FileKani(engine, prompt_tokens_cost = 0.005, completion_tokens_cost = 0.015),
            "Table Agent": TableKani(engine, prompt_tokens_cost = 0.005, completion_tokens_cost = 0.015),
            "Editable System Prompt": SystemPromptEditorKani(engine, prompt_tokens_cost = 0.005, completion_tokens_cost = 0.015),
           }


# tell the app to use that function to create agents when needed
ks.set_app_agents(get_agents)


########################
##### 3 - Serve App
########################

ks.serve_app()
