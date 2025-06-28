from kani.engines import WrapperEngine


class CostAwareEngine(WrapperEngine):
    """
    A wrapper engine that tracks the cost of the conversation based on token usage.
    It requires the prompt and completion token costs to be set.
    """

    def __init__(self, engine, *args, prompt_tokens_cost=None, completion_tokens_cost=None, **kwargs):
        super().__init__(engine, *args, **kwargs)

        self.prompt_tokens_cost = prompt_tokens_cost
        self.completion_tokens_cost = completion_tokens_cost
        self.tokens_used_prompt = 0
        self.tokens_used_completion = 0


    def add_tokens_used(self, prompt_tokens, completion_tokens):
        """Add the number of tokens used in the conversation."""
        self.tokens_used_prompt += prompt_tokens
        self.tokens_used_completion += completion_tokens


    def get_convo_cost(self):
        """Get the total cost of the conversation so far."""
        if self.prompt_tokens_cost is None or self.completion_tokens_cost is None:
            return None
        
        return (self.tokens_used_prompt / 1000000.0) * self.prompt_tokens_cost + (self.tokens_used_completion / 1000000.0) * self.completion_tokens_cost
