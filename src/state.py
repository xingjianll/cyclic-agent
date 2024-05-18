from typing import Generic, TypeVar, Callable, Tuple

S = TypeVar('S')
A = TypeVar('A')
B = TypeVar('B')


class State(Generic[S, A]):
    def __init__(self, run_state: Callable[[S], Tuple[A, S]]):
        """
        Initialize the State with a function that takes a state and returns
        a tuple of a value and a state.
        """
        self.run_state = run_state

    def __call__(self, state: S) -> Tuple[A, S]:
        """
        Run the state transformation.
        """
        return self.run_state(state)

    def bind(self, fn: Callable[[A], "State[S, B]"]) -> "State[S, B]":
        """
        The bind function for chaining stateful computations. It takes a function
        that transforms a result of type A into another State monad that computes
        a result of type B.
        """

        def new_run_state(s: S) -> Tuple[B, S]:
            a, new_s = self(s)  # Get current state and result
            return fn(a)(new_s)  # Apply the function and pass the new state

        return State(new_run_state)


if __name__ == "__main__":
    def increment(x: int) -> State[int, int]:
        return State(lambda s: (s + x, s + 1))


    def double(x: int) -> State[int, int]:
        return State(lambda s: (s * 2, s))

    initial_state = State(lambda s: (s, s))
    result_state = initial_state.bind(increment).bind(double)
    print(result_state(10))
