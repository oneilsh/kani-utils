# Example usage of StreamlitKani

########################
##### 0 - load libs
########################

# kani_streamlit imports
import kani_utils.kani_streamlit_server as ks
from kani_utils.base_engines import CostAwareEngine
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
base_engine = OpenAIEngine(os.environ["OPENAI_API_KEY"], model="gpt-4o")

# these each track their own token usage and costs, for use with the agents below
# (it is not recommended to share a single CostAwareEngine instance across multiple agents in the main UI)
cost_engine1 = CostAwareEngine(base_engine, prompt_tokens_cost=5, completion_tokens_cost=20)
cost_engine2 = CostAwareEngine(base_engine, prompt_tokens_cost=5, completion_tokens_cost=20)
cost_engine3 = CostAwareEngine(base_engine, prompt_tokens_cost=5, completion_tokens_cost=20)
cost_engine4 = CostAwareEngine(base_engine, prompt_tokens_cost=5, completion_tokens_cost=20)
cost_engine5 = CostAwareEngine(base_engine, prompt_tokens_cost=5, completion_tokens_cost=20)

# We also have to define a function that returns a dictionary of agents to serve
# Agents are keyed by their name, which is what the user will see in the UI
# cost is in dollars per 1000000 tokens
def get_agents():
    return {
            "Author Search Agent": AuthorSearchKani(cost_engine1),
            "Author Search Agent (No costs shown)": AuthorSearchKani(base_engine),
            "Memory Agent": MemoryKani(cost_engine2),
            "File Agent": FileKani(cost_engine3),
            "Table Agent": TableKani(cost_engine4),
            "Editable System Prompt": SystemPromptEditorKani(cost_engine5),
           }


# tell the app to use that function to create agents when needed
ks.set_app_agents(get_agents)


########################
##### 3 - Serve App
########################

ks.serve_app()
