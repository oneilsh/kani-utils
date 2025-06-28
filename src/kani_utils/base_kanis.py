
from kani import Kani, ChatMessage
from kani_utils.kani_streamlit_server import UIOnlyMessage
import streamlit as st

class EnhancedKani(Kani):
    def __init__(self,
                 *args,
                 name = "Agent Name",
                 greeting = "Greetings! This greeting is shown to the user before the interaction, to provide instructions or other information. The LLM does not see it.",
                 description = "A brief description of the agent, shown in the user interface.",
                 avatar = "🤖",
                 user_avatar = "👤",
                 **kwargs):
        
        super().__init__(*args, **kwargs)

        self.name = name
        self.greeting = greeting
        self.description = description
        self.avatar = avatar
        self.user_avatar = user_avatar


    def update_system_prompt(self, system_prompt):
        """Update the system prompt of the agent."""
        self.system_prompt = system_prompt
        self.always_included_messages = [ChatMessage(role="system", content=system_prompt)]
            

    # https://github.com/zhudotexe/kani/issues/29#issuecomment-2140905232
    async def add_completion_to_history(self, completion):
        # if self.engine is a CostAwareEngine, we need to add the tokens used to the cost tracker
        if hasattr(self.engine, 'add_tokens_used'):
            self.engine.add_tokens_used(completion.prompt_tokens, completion.completion_tokens)

        return await super().add_completion_to_history(completion)
    

    def get_convo_cost(self):
        """Get the total cost of the conversation so far. This may be overridden to provide a custom cost calculation (e.g. when using [sub-kanis](https://kani.readthedocs.io/en/latest/advanced/subkani.html))."""
        if hasattr(self.engine, 'get_convo_cost'):
            return self.engine.get_convo_cost()
        return None
    

    def get_convo_tokens(self):
        """Get the total number of tokens used in the conversation so far. This may be overridden to provide a custom token count (e.g. when using [sub-kanis](https://kani.readthedocs.io/en/latest/advanced/subkani.html))."""
        if hasattr(self.engine, 'tokens_used_prompt') and hasattr(self.engine, 'tokens_used_completion'):
            return {"prompt_tokens": self.engine.tokens_used_prompt, "completion_tokens": self.engine.tokens_used_completion}
        return None


class StreamlitKani(EnhancedKani):
    def __init__(self,
                 *args,
                 **kwargs):

        super().__init__(*args, **kwargs)

        self.display_messages = []
        self.delayed_display_messages = []


    def render_in_streamlit_chat(self, func, delay = True, share_func = None):
        """Renders UI components in the chat. Takes a function that takes no parameters that should render the elements."""
        if not delay:
            self.display_messages.append(UIOnlyMessage(func, share_func = share_func))
        else:
            self.delayed_display_messages.append(UIOnlyMessage(func, share_func = share_func))


    def render_delayed_messages(self):
        """Used by the server when the agent is done with its turn to render any delayed messages."""
        self.display_messages.extend(self.delayed_display_messages)
        self.delayed_display_messages = []


    def render_sidebar(self):
        st.markdown(self.description)

        cost = self.get_convo_cost()
        tokens = self.get_convo_tokens()

        if cost is not None:
            st.markdown(f"""
                        ### Session Cost: ${(0.01 + cost if cost > 0 else 0.00):.2f}
                        """, help = f"""Prompt tokens: {tokens["prompt_tokens"]}, Completion tokens: {tokens["completion_tokens"]}""")
