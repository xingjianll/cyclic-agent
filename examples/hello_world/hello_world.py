from __future__ import annotations
import os
import time
import cohere
from cyclic_agent import State, CyclicExecutor

co = cohere.Client(os.environ.get("COHERE_API_KEY"))

class AskQuestion(State[None]):
    def next(self, signal: None = None) -> AnswerQuestion:
        response = co.chat(message="Ask a question", temperature=1)
        print(response.text)
        return AnswerQuestion(question=response.text)

class AnswerQuestion(State[None]):
    question: str

    def next(self, signal: None = None) -> AskQuestion:
        answer = co.chat(message=self.question)
        print(answer)
        return AskQuestion()

if __name__ == "__main__":
    initial_state = AskQuestion()
    executor = CyclicExecutor(5)
    executor.start(initial_state)
    time.sleep(20)