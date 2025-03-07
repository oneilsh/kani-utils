
from kani import Kani
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
                 prompt_tokens_cost = None,
                 completion_tokens_cost = None,
                 **kwargs):
        
        super().__init__(*args, **kwargs)

        self.name = name
        self.greeting = greeting
        self.description = description
        self.avatar = avatar
        self.user_avatar = user_avatar

        self.prompt_tokens_cost = prompt_tokens_cost
        self.completion_tokens_cost = completion_tokens_cost
        self.tokens_used_prompt = 0
        self.tokens_used_completion = 0

            
    def get_convo_cost(self):
        """Get the total cost of the conversation so far."""
        if self.prompt_tokens_cost is None or self.completion_tokens_cost is None:
            return None
        
        return (self.tokens_used_prompt / 1000.0) * self.prompt_tokens_cost + (self.tokens_used_completion / 1000.0) * self.completion_tokens_cost

    # https://github.com/zhudotexe/kani/issues/29#issuecomment-2140905232
    async def add_completion_to_history(self, completion):
        self.tokens_used_prompt += completion.prompt_tokens
        self.tokens_used_completion += completion.completion_tokens
        return await super().add_completion_to_history(completion)


class StreamlitKani(EnhancedKani):
    def __init__(self,
                 *args,
                 **kwargs):

        super().__init__(*args, **kwargs)

        self.display_messages = []
        self.delayed_display_messages = []


    def render_in_streamlit_chat(self, func, delay = True):
        """Renders UI components in the chat. Takes a function that takes no parameters that should render the elements."""
        if not delay:
            self.display_messages.append(UIOnlyMessage(func))
        else:
            self.delayed_display_messages.append(UIOnlyMessage(func))


    def render_delayed_messages(self):
        """Used by the server when the agent is done with its turn to render any delayed messages."""
        self.display_messages.extend(self.delayed_display_messages)
        self.delayed_display_messages = []


    def render_sidebar(self):
        st.markdown(self.description)

        cost = self.get_convo_cost()

        if cost is not None:
            st.markdown(f"""
                        ### Conversation Cost: ${(0.01 + cost if cost > 0 else 0.00):.2f}
                        Prompt tokens: {self.tokens_used_prompt}, Completion tokens: {self.tokens_used_completion}
                        """)
