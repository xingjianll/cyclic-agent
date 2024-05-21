import inspect
from typing import Callable, Generic, TypeVar, Any

A = TypeVar('A')
B = TypeVar('B')


class Cycle(Generic[A, B]):
    def __init__(self, fn: Callable[[A], 'Cycle[B, Any]'], initial_state: A):
        self.fn = fn
        self.initial_state = initial_state

    def run(self) -> 'Cycle[B, Any]':
        return self.fn(self.initial_state)

    def __call__(self) -> 'Cycle[B, Any]':
        return self.run()


def cyc(fn: Callable[[A], 'Cycle[B, Any]']):
    sig = inspect.signature(fn)

    def wrapper(*args, **kwargs):
        bound_args = sig.bind(*args, **kwargs)
        bound_args.apply_defaults()
        if bound_args.arguments:
            initial_state = next(iter(bound_args.arguments.values()))
        else:
            raise ValueError("Function requires at least one argument, none provided")

        return Cycle(fn, initial_state=initial_state)

    return wrapper


def main():
    @cyc
    def create_increment_cycle(state: int) -> 'Cycle[int, int]':
        state += 1
        print(state)
        return create_increment_cycle(state=state)

    cycle = create_increment_cycle(state=0)

    for i in range(5):
        cycle = cycle()


if __name__ == "__main__":
    main()


