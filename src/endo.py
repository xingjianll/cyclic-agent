from typing import Protocol, Self, TypeVar


class State:
    def evoke(self) -> 'State':
        raise NotImplementedError


class Child(State):
    def evoke(self) -> State:
        return Child2()


class Child2(State):
    def evoke(self) -> Child:
        ...
