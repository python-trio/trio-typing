import trio
from abc import abstractmethod, abstractproperty
from typing import (
    Any,
    Awaitable,
    Callable,
    FrozenSet,
    Generic,
    Optional,
    TypeVar,
    overload,
)
from typing_extensions import Protocol
from mypy_extensions import NamedArg

__all__ = ["CancelScope", "Nursery", "TaskStatus"]

T = TypeVar("T")
StarArgs = TypeVar("StarArgs")
T_contra = TypeVar("T_contra", contravariant=True)
T1 = TypeVar("T1")
T2 = TypeVar("T2")
T3 = TypeVar("T3")
T4 = TypeVar("T4")


class ArgsForCallable:
    pass


def takes_callable_and_args(fn: T) -> T:
    return fn


class TaskStatus(Protocol[T_contra]):
    def started(self, value: T_contra = ...) -> None: ...


class CancelScope:
    deadline: float
    shield: bool
    cancel_called: bool
    cancelled_caught: bool
    def cancel(self) -> None: ...


class Nursery:
    cancel_scope: CancelScope
    @property
    def child_tasks(self) -> FrozenSet[trio.hazmat.Task]: ...
    @property
    def parent_task(self) -> trio.hazmat.Task: ...
    @takes_callable_and_args
    def start_soon(
        self,
        async_fn: Callable[[ArgsForCallable], Awaitable[None]],
        *args: ArgsForCallable,
        name: object = None,
    ) -> None: ...
    @takes_callable_and_args
    async def start(
        self,
        async_fn: Callable[
            [ArgsForCallable, NamedArg(TaskStatus[T], "task_status")], Awaitable[None]
        ],
        *args: ArgsForCallable,
        name: object = None,
    ) -> T: ...
