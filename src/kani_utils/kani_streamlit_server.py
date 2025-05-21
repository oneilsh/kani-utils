import streamlit as st
import logging
from kani import ChatRole, ChatMessage
import asyncio
from upstash_redis import Redis
import base64
import dill
import hashlib
import urllib.parse
from kani_utils.utils import _seconds_to_days_hours, _sync_generator_from_kani_streammanager
import json
import datetime
import os

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
    if "show_function_calls" in kwargs:
        del kwargs["show_function_calls"]
    if "share_chat_ttl_seconds" in kwargs:
        del kwargs["share_chat_ttl_seconds"]
    if "show_function_calls_status" in kwargs:
        del kwargs["show_function_calls_status"]

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

    st.session_state.setdefault("show_function_calls", kwargs.get("show_function_calls", False))
    st.session_state.setdefault("show_function_calls_status", kwargs.get("show_function_calls_status", True))




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


async def _process_input(prompt):
    prompt = prompt.strip()

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

    if st.session_state.show_function_calls_status:
        orig_status = "Thinking..."
        status = st.status(orig_status)

    with st.chat_message("assistant", avatar = agent.avatar):
        async for stream in agent.full_round_stream(prompt):
            if stream.role == ChatRole.ASSISTANT:
                st.write_stream(_sync_generator_from_kani_streammanager(stream))

            message = await stream.message()

            # compute the status as the most recent set of tool calls
            if message is not None and message.tool_calls is not None and st.session_state.show_function_calls_status:
                # I don't think message.tool_calls is ever None, but just in case
                if(len(message.tool_calls) > 0):
                    all_tool_calls = [f"`{tool_call.function.name}`" for tool_call in message.tool_calls]
                    distinct_tool_calls = set(all_tool_calls)
                    status.update(label = f"Checking sources: {', '.join(distinct_tool_calls)}")

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


# Handle chat input and responses
async def _handle_chat_input(given_prompt = None):
    if prompt := st.chat_input(disabled=False, on_submit=_lock_ui):
        await _process_input(prompt)
        return

    # not working...    
    # if given_prompt:
    #     await _process_input(given_prompt)


# Lock the UI when user submits input
def _lock_ui():
    st.session_state.lock_widgets = True


def _clear_chat_current_agent():
    current_agent = st.session_state.agents[st.session_state.current_agent_name]
    current_agent.display_messages = []
    current_agent.delayed_display_messages = []
    current_agent.tokens_used_prompt = 0
    current_agent.tokens_used_completion = 0
    current_agent.chat_history = []


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
        # if UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN are both set, we can connect to the Redis database
        # otherwise, we assume no database is configured
        if "UPSTASH_REDIS_REST_URL" in os.environ and "UPSTASH_REDIS_REST_TOKEN" in os.environ:
            try:
                redis = Redis.from_env()
                dbsize = redis.dbsize()
                st.session_state.logger.info(f"Shared chats DB size: {dbsize}")

            except Exception as e:
                st.session_state.logger.error(f"Error connecting to database, or no database to connect to. Error:\n{e}")
            
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


def _get_unpicklable(obj):
    """Returns a string representation of the unpicklable objects in the given object, with indentation."""
    try:
        dill.dumps(obj)
        return ""
    except Exception as e:
        unpicklable_str = f"Cannot pickle: {e}"
        if hasattr(obj, "__dict__"):
            for k, v in obj.__dict__.items():
                unpicklable_str += "\n" + _get_unpicklable(v)
        elif isinstance(obj, (list, tuple, set)):
            for idx, item in enumerate(obj):
                unpicklable_str += "\n" + _get_unpicklable(item)
        elif isinstance(obj, dict):
            for k, v in obj.items():
                unpicklable_str += "\n" + _get_unpicklable(v)
        return unpicklable_str



def _share_chat():
    try:
        current_agent = st.session_state.agents[st.session_state.current_agent_name]

        session_state_bytes_rep = dill.dumps(st.session_state)
        session_state_str_rep = base64.b64encode(session_state_bytes_rep).decode('utf-8')

        ## encode the chat data
        chat_data_dict = {"display_messages": current_agent.display_messages,
                   "agent_greeting": current_agent.greeting,
                   "agent_system_prompt": current_agent.system_prompt,
                   "agent_avatar": current_agent.avatar,
                   "session_state": session_state_str_rep,
                   }

        chat_data_bytes_rep = dill.dumps(chat_data_dict)
        chat_data_str_rep = base64.b64encode(chat_data_bytes_rep).decode('utf-8')

        # generate chat summary
        async def summarize():
            agent_based_summary_prompt = "I am preparing to share this chat with others. Please summarize it in a few sentences."
            agent_based_summary = await current_agent.chat_round_str(agent_based_summary_prompt)
            return agent_based_summary
        
        agent_based_summary = asyncio.run(summarize())


        redis = Redis.from_env()

        # generate convo key, and compute access count (0 if new)
        key = st.session_state.page_title + "@" + current_agent.name + "@" + hashlib.md5(chat_data_str_rep.encode()).hexdigest()
        keycheck = redis.get(key)

        access_count = 0
        if keycheck is not None:
            access_count = keycheck["access_count"] + 1

        # computed metadata
        agent_model = current_agent.engine.model if current_agent.engine.model else "Unknown"
        convo_cost = current_agent.get_convo_cost()
        current_date_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # chat_data stores the agents display_messages, greeting, system_prompt
        save_dict = {"summary": agent_based_summary,
                     "agent_name": current_agent.name,
                     "agent_chat_cost": convo_cost,
                     "agent_model": agent_model,
                     "agent_description": current_agent.description,
                     "access_count": access_count,
                     "chat_data": chat_data_str_rep,
                     "chat_date": current_date_str,
                     }

        # save the chat with a new TTL
        new_ttl_seconds = st.session_state.share_chat_ttl_seconds
        redis.set(key, save_dict, ex=new_ttl_seconds)

        # display the share dialog
        url = urllib.parse.quote(key)
        ttl_human = _seconds_to_days_hours(new_ttl_seconds)

        @st.dialog("Share Chat")
        def share_dialog():
            st.write(f"Chat saved. Share this link: [Chat Link](/?session_id={url})\n\nThis link will expire in {ttl_human}. Any visit to the URL will reset the timer.")

        share_dialog()

    except Exception as e:
        st.write(f"Error saving chat.")
        st.session_state.logger.error(f"Error saving chat. Traceback: {e}")
        st.session_state.logger.error(f"Unpicklable objects: {_get_unpicklable(st.session_state)}")


def _render_shared_chat():
    session_id = st.query_params["session_id"]

    try:
        # load the session data from the given key
        redis = Redis.from_env()
        session_dict_raw = redis.get(session_id)
        session_dict = json.loads(session_dict_raw)

        if session_dict is None:
            # throw an exception to trigger the error message
            raise ValueError(f"Session Key {session_id} not found in database")
        
        chat_data_str_rep = session_dict["chat_data"]
        chat_data_bytes_rep = base64.b64decode(chat_data_str_rep.encode('utf-8'))
        chat_data = dill.loads(chat_data_bytes_rep)

        # update ttl and access count, save back to redis
        new_ttl_seconds = st.session_state.share_chat_ttl_seconds
        access_count = session_dict["access_count"] + 1
        session_dict["access_count"] = access_count

        redis.set(session_id, session_dict, ex=new_ttl_seconds)


        # load chat data
        display_messages = chat_data["display_messages"]
        agent_system_prompt = chat_data["agent_system_prompt"]
        agent_greeting = chat_data["agent_greeting"]
        agent_avatar = chat_data["agent_avatar"]

        # load session state
        st_session_state_str_rep = chat_data["session_state"]
        st_session_state_bytes_rep = base64.b64decode(st_session_state_str_rep.encode('utf-8'))
        st.session_state = dill.loads(st_session_state_bytes_rep)

        # load other metadata
        agent_name = session_dict["agent_name"]
        agent_description = session_dict["agent_description"]
        agent_chat_cost = session_dict["agent_chat_cost"]
        agent_model = session_dict["agent_model"]
        agent_summary = session_dict["summary"]
        chat_date = session_dict["chat_date"]

        # override show_function_calls to False, but only once
        if "first_func_calls_off_flag" not in st.session_state:
            st.session_state.show_function_calls = False
            st.session_state.first_func_calls_off_flag = True

        # compute the human-readable TTL
        ttl_human = _seconds_to_days_hours(redis.ttl(session_id))

        # display session details in expander
        with st.expander("Details"):
            st.markdown(f"##### This chat record will expire in {ttl_human}. Revisiting this URL will reset the expiration timer.")
            st.markdown(f"You can chat with this agent [here](/), selecting *{agent_name}* in the sidebar.")
            # render checkbox for showing function calls
            st.checkbox("🛠️ Show full message contexts", 
                        key="show_function_calls",
                        value = False)
            st.markdown("**Chat date:** " + str(chat_date))
            st.markdown("**Chat summary:** " + str(agent_summary))
            st.markdown("**Chat access count:** " + str(access_count))
            st.markdown(f"**Chat Cost:** ${0.01 + agent_chat_cost:.2f} (includes summary generation)") # rounded up to 1c
            st.markdown("**Agent Description:** " + str(agent_description))
            st.markdown("**Agent Model:** " + str(agent_model))
            st.markdown("**Agent System Prompt (*at time of chat share*):**")
            st.code(str(agent_system_prompt), language=None, wrap_lines=True, line_numbers=True)


        # display the chat as in the main UI: agent name, greeting, messages

        st.header(agent_name)

        with st.chat_message("assistant", avatar = agent_avatar):
            st.write(agent_greeting)

        for message in display_messages:
            _render_message(message)

    except Exception as e:
        st.session_state.logger.error(f"Error connecting to Redis: {e}")
        st.write(f"Error connecting to database.")


# Main Streamlit UI
async def _main():

    if "session_id" in st.query_params:
        _render_shared_chat()
        return
    
    else:
        _render_sidebar()

        current_agent = st.session_state.agents[st.session_state.current_agent_name]

        st.header(current_agent.name)

        with st.chat_message("assistant", avatar = current_agent.avatar):
            st.write(current_agent.greeting)

        # not working...
        # def _send_button_to_chat(button_text):
        #     asyncio.run(_handle_chat_input(button_text))
        #     #await _handle_chat_input(button_text)

        # if current_agent.buttons:
        #     for button in current_agent.buttons:
        #         st.button(button, on_click=_send_button_to_chat, args=(button,))

        for message in current_agent.display_messages:
            _render_message(message)

        await _handle_chat_input()



