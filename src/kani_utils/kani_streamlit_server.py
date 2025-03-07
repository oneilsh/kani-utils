import streamlit as st
import logging
from kani import ChatRole, ChatMessage
import asyncio
import asyncio
from upstash_redis import Redis
import base64
import dill
import hashlib
import urllib.parse
from kani_utils.utils import _seconds_to_days_hours, _sync_generator_from_kani_streammanager


class UIOnlyMessage:
    def __init__(self, func, role=ChatRole.ASSISTANT, icon="💡", type = "ui_element"):
        self.func = func # the function that will render the UI element
        self.role = role
        self.icon = icon
        self.type = type # the type of message, e.g. "ui_element" or "tool_use"


def initialize_app_config(**kwargs):
    _initialize_session_state(**kwargs)

    # this is kind of a hack, we want the user to be able to configure the default settings for
    # which needs to be set in the session state, so we pass in kwargs to _initialize_session_state() above, but they can't 
    # go to set_page_config below, so we remove them here
    del kwargs["show_function_calls"]
    del kwargs["share_chat_ttl_seconds"]

    defaults = {
        "page_title": "Kani AI",
        "page_icon": None,
        "layout": "centered",
        "initial_sidebar_state": "collapsed",
        "menu_items": {
            "Get Help": "https://github.com/monarch-initiative/agent-smith-ai",
            "Report a Bug": "https://github.com/monarch-initiative/agent-smith-ai/issues",
            "About": "Agent Smith (AI) is a framework for developing tool-using AI-based chatbots.",
        }
    }

    # set the page title to the session_state as we'll need it later
    st.session_state.page_title = kwargs.get("page_title", defaults["page_title"])

    st.set_page_config(
        **{**defaults, **kwargs}
    )


def set_app_agents(agents_func, reinit = False):
    if "agents" not in st.session_state or reinit:
        agents = agents_func()
        st.session_state.agents = agents
        st.session_state.agents_func = agents_func

        if not reinit:
            st.session_state.current_agent_name = list(st.session_state.agents.keys())[0]



def serve_app():
    assert "agents" in st.session_state, "No agents have been set. Use set_app_agents() to set agents prior to serve_app()"
    loop = st.session_state.get("event_loop")
    
    loop.run_until_complete(_main())



# Initialize session states
def _initialize_session_state(**kwargs):
    if "logger" not in st.session_state:
        st.session_state.logger = logging.getLogger(__name__)
        st.session_state.logger.handlers = []
        st.session_state.logger.setLevel(logging.INFO)
        st.session_state.logger.addHandler(logging.StreamHandler())

    st.session_state.setdefault("event_loop", asyncio.new_event_loop())
    st.session_state.setdefault("default_api_key", None)  # Store the original API key
    st.session_state.setdefault("ui_disabled", False)
    st.session_state.setdefault("lock_widgets", False)
    ttl_seconds = kwargs.get("share_chat_ttl_seconds", 60*60*24*30)  # 30 days default
    st.session_state.setdefault("share_chat_ttl_seconds", ttl_seconds)

    if "show_function_calls" in kwargs:
        st.session_state.setdefault("show_function_calls", kwargs["show_function_calls"])
    else:
        st.session_state.setdefault("show_function_calls", False)




# Render chat message
def _render_message(message):
    current_agent = st.session_state.agents[st.session_state.current_agent_name]
    current_agent_avatar = current_agent.avatar
    current_user_avatar = current_agent.user_avatar

    current_action = "*Thinking...*"


    # first, check if this is a UIOnlyMessage,
    # if so, render it and return
    if isinstance(message, UIOnlyMessage):
        if message.role == ChatRole.USER:
            role = "user"
        else:
            role = "assistant"

        if message.type == "ui_element":
            with st.chat_message(role, avatar=message.icon):
                message.func()

        elif message.type == "tool_use" and st.session_state.show_function_calls:
            with st.chat_message(role, avatar=message.icon):
                message.func()

        return current_action
    
    elif message.role == ChatRole.USER:
        with st.chat_message("user", avatar = current_user_avatar):
            st.write(message.text)

    elif message.role == ChatRole.SYSTEM:
        with st.chat_message("assistant", avatar="ℹ️"):
            st.write(message.text)

    elif message.role == ChatRole.ASSISTANT and (message.tool_calls == None or message.tool_calls == []):
        with st.chat_message("assistant", avatar=current_agent_avatar):
            st.write(message.text)
    
    return current_action



# Handle chat input and responses
async def _handle_chat_input():
    #if prompt := st.chat_input(disabled=st.session_state.lock_widgets, on_submit=_lock_ui):
    if prompt := st.chat_input(disabled=False, on_submit=_lock_ui):
        # get current agent
        agent = st.session_state.agents[st.session_state.current_agent_name]

        # add user message to display and agent's history
        user_message = ChatMessage.user(prompt)
        _render_message(user_message)
        agent.display_messages.append(user_message)

        session_id = st.runtime.scriptrunner.add_script_run_ctx().streamlit_script_run_ctx.session_id
        info = {"session_id": session_id, "message": user_message.model_dump(), "agent": st.session_state.current_agent_name}
        st.session_state.logger.info(info)


        st.session_state.current_action = "*Thinking...*"

        messages = []
        message = None

        status = "Thinking..."

        with st.chat_message("assistant", avatar = agent.avatar):
            async for stream in agent.full_round_stream(prompt):
                # compute the status as the most recent set of tool calls
                if message is not None and message.tool_calls is not None:
                    all_tool_calls = [f"`{tool_call.function.name}`" for tool_call in message.tool_calls]
                    distinct_tool_calls = set(all_tool_calls)
                    status = f"Checking sources: {', '.join(distinct_tool_calls)}"

                with st.spinner(status):
                    # if this is not a function result, stream data to the UI
                    if stream.role == ChatRole.ASSISTANT:
                        st.write_stream(_sync_generator_from_kani_streammanager(stream))

                # when the message is done, add it to the list
                message = await stream.message()
                messages.append(message)

                # logging
                info = {"session_id": session_id, "message": message.model_dump(), "agent": st.session_state.current_agent_name}
                st.session_state.logger.info(info)


        # add the last message to the display
        agent.display_messages.append(messages[-1])
        # then any delayed UI-based messages
        agent.render_delayed_messages()
        
        # put together a UI element for the collected calls, and add it to the display list labeled as a tool use
        def render_messages():
            with st.expander("Full context"):
                all_json = [message.model_dump() for message in messages]
                st.write(all_json)

        render_context = UIOnlyMessage(render_messages, role=ChatRole.SYSTEM, icon="🛠️", type="tool_use")
        agent.display_messages.append(render_context)

        # unlock and rerun to clean rerender
        st.session_state.lock_widgets = False  # Step 5: Unlock the UI        
        st.rerun()


# Lock the UI when user submits input
def _lock_ui():
    st.session_state.lock_widgets = True


def _clear_chat_current_agent():
    current_agent_name = st.session_state.current_agent_name
    agents_dict = st.session_state.agents_func()
    st.session_state.agents[current_agent_name] = agents_dict[current_agent_name]

    st.session_state.current_agent = agents_dict[current_agent_name]


def _render_sidebar():
    current_agent = st.session_state.agents[st.session_state.current_agent_name]

    with st.sidebar:
        agent_names = list(st.session_state.agents.keys())

        ## First: teh dropdown of agent selections
        current_agent_name = st.selectbox(label = "**Assistant**", 
                                          options=agent_names, 
                                          key="current_agent_name", 
                                          disabled=st.session_state.lock_widgets, 
                                          label_visibility="visible")


        ## then the agent gets to render its sidebar info
        if hasattr(current_agent, "render_sidebar"):
           current_agent.render_sidebar()

        st.markdown("#")
        st.markdown("#")
        st.markdown("#")
        st.markdown("#")

        ## global UI elements
        col1, col2 = st.columns(2)

        with col1:
            st.button(label = "Clear Chat", 
                      on_click=_clear_chat_current_agent, 
                      disabled=st.session_state.lock_widgets,
                      use_container_width=True)
            
        # Try to get the database size from redis and log it
        dbsize = None
        try:
            redis = Redis.from_env()
            dbsize = redis.dbsize()
            st.session_state.logger.info(f"Shared chats DB size: {dbsize}")

        except Exception as e:
            st.session_state.logger.error(f"Error connecting to database, or no database to connect to.")
        
        if dbsize is not None:
            with col2:
                st.button(label = "Share Chat",
                          on_click=_share_chat,
                          disabled=st.session_state.lock_widgets,
                          use_container_width=True)
        
        st.checkbox("🛠️ Show full context", 
                    key="show_function_calls", 
                    disabled=st.session_state.lock_widgets)
        
        st.markdown("---")


def _share_chat():
    try:
        current_agent = st.session_state.agents[st.session_state.current_agent_name]

        agent_model = current_agent.engine.model if current_agent.engine.model else "Unknown"

        to_save = {"display_messages": current_agent.display_messages,
                   "agent_name": current_agent.name,
                   "agent_greeting": current_agent.greeting,
                   "agent_description": current_agent.description,
                   "agent_system_prompt": current_agent.system_prompt,
                   "agent_chat_cost": current_agent.get_convo_cost(),
                   "agent_avatar": current_agent.avatar,
                   "agent_model": agent_model}

        bytes_rep = dill.dumps(to_save)
        str_rep = base64.b64encode(bytes_rep).decode('utf-8')

        redis = Redis.from_env()

        # we need a unique session ID for this chat as an alphanumeric hex string
        # need to safely url encode the current_agent.name to avoid issues; need proper data cleaning
        key = st.session_state.page_title + "@" + current_agent.name + "@" + hashlib.md5(str_rep.encode()).hexdigest()
        url = urllib.parse.quote(key)
        ttl_seconds = st.session_state.share_chat_ttl_seconds
        redis.set(key, str_rep, ex=ttl_seconds)


        ttl_human = _seconds_to_days_hours(ttl_seconds)

        @st.dialog("Share Chat")
        def share_dialog():
            st.write(f"Chat saved. Share this link: [Chat Link](/?session_id={url})\n\nThis link will expire in {ttl_human}. Any visit to the URL will reset the timer.")

        share_dialog()

    except Exception as e:
        st.write(f"Error saving chat.")


# Main Streamlit UI
async def _main():

    if "session_id" in st.query_params:
        session_id = st.query_params["session_id"]

        try:
            redis = Redis.from_env()
            str_rep = redis.get(session_id)
            
            if str_rep is None:
                # throw an exception to trigger the error message
                raise ValueError(f"Session ID {session_id} not found in database")
            
            ttl_human = _seconds_to_days_hours(redis.ttl(session_id))
            bytes_rep = base64.b64decode(str_rep.encode('utf-8'))
            to_load = dill.loads(bytes_rep)

            display_messages = to_load["display_messages"]
            agent_name = to_load["agent_name"]
            agent_greeting = to_load["agent_greeting"]
            agent_description = to_load["agent_description"]
            agent_system_prompt = to_load["agent_system_prompt"]
            agent_chat_cost = to_load["agent_chat_cost"]
            agent_avatar = to_load["agent_avatar"]
            agent_model = to_load["agent_model"]
            
            # override show_function_calls to False, but only once
            if "first_func_calls_off_flag" not in st.session_state:
                st.session_state.show_function_calls = False
                st.session_state.first_func_calls_off_flag = True


            # write the system prompt as an expander
            with st.expander("Details"):
                st.markdown(f"##### This chat record will expire in {ttl_human}. Revisiting this URL will reset the expiration timer.")
                st.markdown(f"**Chat Cost:** ${0.01 + agent_chat_cost:.2f}")
                st.markdown("**Agent Description:** " + str(agent_description))
                st.markdown("**Agent Model:** " + str(agent_model))
                st.markdown("**Agent System Prompt:**\n```\n" + str(agent_system_prompt) + "\n```")
                # chat cost rounded up to nearest 0.01
        
                # render checkbox for showing function calls
                st.checkbox("🛠️ Show full message contexts", 
                            key="show_function_calls",
                            value = False)


            st.header(agent_name)

            with st.chat_message("assistant", avatar = agent_avatar):
                st.write(agent_greeting)

            for message in display_messages:
                _render_message(message)

        except Exception as e:
            st.session_state.logger.error(f"Error connecting to Redis: {e}")
            st.write(f"Error connecting to database.")

    else:
        _render_sidebar()

        current_agent = st.session_state.agents[st.session_state.current_agent_name]

        st.header(current_agent.name)

        with st.chat_message("assistant", avatar = current_agent.avatar):
            st.write(current_agent.greeting)

        for message in current_agent.display_messages:
            _render_message(message)

        await _handle_chat_input()



