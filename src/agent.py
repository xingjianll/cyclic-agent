import os
from time import sleep

from langchain_community.chat_models import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser

from base import Cycle


class SimpleLangChainAgent(Cycle[list[tuple[str, str]]]):
    def __init__(self):
        print(os.getenv('OPENAI_API_KEY'))
        llm = ChatOpenAI(openai_api_key=os.getenv('OPENAI_API_KEY'))
        output_parser = StrOutputParser()
        self.chain = llm | output_parser
        super().__init__(1)

    def evoke(self, state: list[tuple[str, str]]):
        print(state)
        value = self.chain.invoke(state)
        return state.append(("assistant", value))


if __name__ == '__main__':
    agent_cycle = SimpleLangChainAgent()
    agent_cycle.start([("system", "If the last message is not a question, ask a question. Otherwise answer the question.")])
    sleep(10)
    agent_cycle.kill()
