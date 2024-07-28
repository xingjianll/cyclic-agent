from typing import Callable, Annotated

from cyclic_agent import State


class Search(State[None]):
    query: str
    exit_: Callable[[[Annotated[str, "search result"]]], State]

    def next(self, signal: None = None) -> State:
        search_result = self.search(self.query)
        return self.exit_(search_result)

    def search(self, query: str) -> str:
        raise NotImplementedError
