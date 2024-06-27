import inspect
from typing import Generic, TypeVar, Callable

A = TypeVar('A')
S = TypeVar('S', bound='State')


class State(Generic[A, S]):
    def __init__(self, state_input: A, transition_fn: Callable[[A], S] | None = None):
        self.state_input = state_input
        self.transition_fn = transition_fn

    def evoke(self) -> S:
        if self.transition_fn:
            return self.transition_fn(self.state_input)
        return self._evoke(self.state_input)

    def _evoke(self, state_input: A) -> S:
        raise NotImplementedError

    def __call__(self, *args, **kwargs) -> S:
        return self.evoke()


def state(fn: Callable[[A], S]):
    sig = inspect.signature(fn)

    def wrapper(*args, **kwargs) -> State[A, S]:
        bound_args = sig.bind(*args, **kwargs)
        bound_args.apply_defaults()
        if bound_args.arguments:
            state_input = next(iter(bound_args.arguments.values()))
        else:
            raise ValueError("Function requires at least one argument, none provided")
        a: State[A, S] = State(state_input, fn)
        return a

    return wrapper


@state
def func1(a: int) -> State[int | str, State]:
    print(a)
    if a == 2:
        return func2('hi')
    return func1(a + 1)


@state
def func2(a: str) -> State:
    print(a)
    return func1(0)


def main():
    state = func1(0)
    for i in range(5):
        state = state.evoke()


if __name__ == "__main__":
    main()
