import os
from time import sleep

from langchain_community.chat_models import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser

from base import Cyclable, CyclicExecutor


class SimpleLangChainAgent(Cyclable[list[tuple[str, str]]]):
    def __init__(self):
        llm = ChatOpenAI(openai_api_key=os.getenv('OPENAI_API_KEY'))
        output_parser = StrOutputParser()
        self.chain = llm | output_parser

    def execute_cycle(self, state: list[tuple[str, str]]) -> list[tuple[str, str]]:
        print(state)
        value = self.chain.invoke(state)
        state.append(("assistant", value))
        return state


if __name__ == '__main__':
    agent = SimpleLangChainAgent()
    executor = CyclicExecutor(1, agent)
    executor.start([("system", "If the last message is not a question, ask a question. Otherwise answer the question.")])
    sleep(10)
    executor.kill()
