from abc import abstractmethod
from typing import Generic, TypeVar, Union

S = TypeVar('S')
StateKind = TypeVar('StateKind', bound='State')


class State(Generic[S, StateKind]):
    def __init__(self, state_input: S):
        self.state_input = state_input

    def evoke(self) -> StateKind:
        return self.state_transition(self.state_input)

    @abstractmethod
    def state_transition(self, a: S) -> StateKind:
        raise NotImplementedError


class State1(State[int, Union['State1', 'State2']]):
    def state_transition(self, a: int) -> Union['State1', 'State2']:
        print(a)
        if a == 2:
            return State2('hi')
        return State1(a + 1)


class State2(State[str, State1]):
    def state_transition(self, a: str) -> State1:
        print(a)
        return State1(0)


def main():
    state = State1(0)
    for i in range(5):
        state = state.evoke(state.state_input)


if __name__ == "__main__":
    main()
