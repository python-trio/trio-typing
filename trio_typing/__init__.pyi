import trio
from abc import abstractmethod, abstractproperty
from typing import (
    Any,
    AsyncIterator,
    Awaitable,
    Callable,
    FrozenSet,
    Generic,
    Optional,
    Type,
    TypeVar,
    overload,
)
from typing_extensions import Protocol
from mypy_extensions import NamedArg

__all__ = [
    "CancelScope", "Nursery", "TaskStatus", "ArgsForCallable", "takes_callable_and_args",
    "AsyncGenerator", "AsyncGeneratorWithReturn",
]

T = TypeVar("T")
T_co = TypeVar("T_co", covariant=True)
T_co2 = TypeVar("T_co2", covariant=True)
T_contra = TypeVar("T_contra", contravariant=True)


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


if sys.version_info >= (3, 6):
    from typing import AsyncGenerator
else:
    class AsyncGenerator(AsyncIterator[T_co], Generic[T_co, T_contra]):
        @abstractmethod
        def __anext__(self) -> Awaitable[T_co]: ...

        @abstractmethod
        def asend(self, value: T_contra) -> Awaitable[T_co]: ...

        @abstractmethod
        def athrow(self, typ: Type[BaseException], val: Optional[BaseException] = ...,
                   tb: Any = ...) -> Awaitable[T_co]: ...

        @abstractmethod
        def aclose(self) -> Awaitable[T_co]: ...

        @abstractmethod
        def __aiter__(self) -> AsyncGenerator[T_co, T_contra]: ...

        @property
        def ag_await(self) -> Any: ...
        @property
        def ag_code(self) -> CodeType: ...
        @property
        def ag_frame(self) -> FrameType: ...
        @property
        def ag_running(self) -> bool: ...

class AsyncGeneratorWithReturn(
    AsyncGenerator[T_co, T_contra], Generic[T_co, T_contra, T_co2]
):
    pass

class YieldType(Generic[T_co]):
    pass

class SendType(Generic[T_contra]):
    pass

class _AgenMaker1(Generic[T_co]):
    @overload
    def __call__(
        self, __fn: Callable[..., Awaitable[None]]
    ) -> Callable[..., AsyncGenerator[T_co, None]]: ...
    @overload
    def __call__(
        self, __fn: Callable[..., Awaitable[T_co2]]
    ) -> Callable[..., AsyncGeneratorWithReturn[T_co, None, T_co2]]: ...

class _AgenMaker2(Generic[T_co, T_contra]):
    @overload
    def __call__(
        self, __fn: Callable[..., Awaitable[None]]
    ) -> Callable[..., AsyncGenerator[T_co, T_contra]]: ...
    @overload
    def __call__(
        self, __fn: Callable[..., Awaitable[T_co2]]
    ) -> Callable[..., AsyncGeneratorWithReturn[T_co, T_contra, T_co2]]: ...

@overload
def async_generator(
    __fn: Callable[..., Awaitable[None]]
) -> Callable[..., AsyncGenerator[Any, Any]]: ...

@overload
def async_generator(
    __fn: Callable[..., Awaitable[T_co]]
) -> Callable[..., AsyncGeneratorWithReturn[Any, Any, T_co]]: ...

@overload
def async_generator(__yt: Type[YieldType[T_co]]) -> _AgenMaker1[T_co]: ...

@overload
def async_generator(
    __yt: Type[YieldType[T_co]], __st: Type[SendType[T_contra]]
) -> _AgenMaker2[T_co, T_contra]: ...
