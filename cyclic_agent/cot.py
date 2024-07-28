from typing import Callable

from cyclic_agent import State


class CoT(State[None]):
    exit_: Callable[[str], State]
    llm: State
    prompt: str

    def next(self, signal: None = None) -> State:
        prompt = self.prompt + "Let's think step by step."

        def callback(answer: str) -> State:
            return self.exit_(answer)

        return self.llm(prompt=prompt, callback=callback)
