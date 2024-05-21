import os
from dataclasses import dataclass
from time import sleep

from langchain_community.chat_models import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser

from base import Cyclable, CyclicExecutor
from src.cycle import cyc


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


llm = ChatOpenAI(openai_api_key=os.getenv('OPENAI_API_KEY'))
output_parser = StrOutputParser()
chain = llm | output_parser


@cyc
def ask_question(conv: list[tuple[str, str]]) -> list[tuple[str, str]]:
    value = chain.invoke(conv)
    conv.append(("assistant", value))
    return conv

ask_question.bind()


if __name__ == '__main__':
    agent = SimpleLangChainAgent()
    executor = CyclicExecutor(1, agent)
    executor.start(
        [("system", "If the last message is not a question, ask a question. Otherwise answer the question.")])
    sleep(10)
    executor.kill()
