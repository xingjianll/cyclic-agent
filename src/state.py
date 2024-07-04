import inspect
from abc import abstractmethod
from typing import Generic, TypeVar, Protocol

from pydantic import BaseModel

SigT = TypeVar('SigT')


class Endomorphic(Protocol):
    """Endomorphism"""
    def next(self: 'Endomorphic') -> 'Endomorphic':
        ...


class State(Endomorphic, BaseModel, Generic[SigT]):
    @abstractmethod
    def next(self, signal: SigT | None = None) -> 'State':
        """Transition to the next state."""
        raise NotImplementedError


# def state(fn: Callable[[A], S]):
#     sig = inspect.signature(fn)
#
#     def wrapper(*args, **kwargs) -> State[A, S]:
#         bound_args = sig.bind(*args, **kwargs)
#         bound_args.apply_defaults()
#         if bound_args.arguments:
#             state_input = next(iter(bound_args.arguments.values()))
#         else:
#             raise ValueError("Function requires at least one argument, none provided")
#         a: State[A, S] = State(state_input, fn)
#         return a
#
#     return wrapper
