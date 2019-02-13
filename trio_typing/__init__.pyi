import sys
import trio
from abc import abstractmethod, abstractproperty, ABCMeta
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
    Union,
    overload,
)
from types import CodeType, FrameType, TracebackType
from typing_extensions import Protocol
from mypy_extensions import NamedArg, VarArg

__all__ = [
    "Nursery",
    "TaskStatus",
    "takes_callable_and_args",
    "AsyncGenerator",
    "CompatAsyncGenerator",
]

T = TypeVar("T")
T_co = TypeVar("T_co", covariant=True)
T_co2 = TypeVar("T_co2", covariant=True)
T_contra = TypeVar("T_contra", contravariant=True)

def takes_callable_and_args(fn: T) -> T:
    return fn

class TaskStatus(Protocol[T_contra]):
    def started(self, value: T_contra = ...) -> None: ...

class Nursery:
    cancel_scope: trio.CancelScope
    @property
    def child_tasks(self) -> FrozenSet[trio.hazmat.Task]: ...
    @property
    def parent_task(self) -> trio.hazmat.Task: ...
    @takes_callable_and_args
    def start_soon(
        self,
        async_fn: Union[
            # List these explicitly instead of Callable[..., Awaitable[None]]
            # so that even without the plugin we catch cases of passing a
            # function with keyword-only arguments to start_soon().
            Callable[[], Awaitable[None]],
            Callable[[Any], Awaitable[None]],
            Callable[[Any, Any], Awaitable[None]],
            Callable[[Any, Any, Any], Awaitable[None]],
            Callable[[Any, Any, Any, Any], Awaitable[None]],
            Callable[[VarArg()], Awaitable[None]],
        ],
        *args: Any,
        name: object = None,
    ) -> None: ...
    @takes_callable_and_args
    async def start(
        self,
        async_fn: Union[
            # List these explicitly instead of Callable[..., Awaitable[None]]
            # so that even without the plugin we can infer the return type
            # of start(), and fail when a function is passed that doesn't
            # accept task_status.
            Callable[[NamedArg(TaskStatus[T], "task_status")], Awaitable[None]],
            Callable[[Any, NamedArg(TaskStatus[T], "task_status")], Awaitable[None]],
            Callable[
                [Any, Any, NamedArg(TaskStatus[T], "task_status")], Awaitable[None]
            ],
            Callable[
                [Any, Any, Any, NamedArg(TaskStatus[T], "task_status")], Awaitable[None]
            ],
            Callable[
                [Any, Any, Any, Any, NamedArg(TaskStatus[T], "task_status")],
                Awaitable[None],
            ],
            Callable[
                [VarArg(), NamedArg(TaskStatus[T], "task_status")], Awaitable[None]
            ],
        ],
        *args: Any,
        name: object = None,
    ) -> T: ...

if sys.version_info >= (3, 6):
    from typing import AsyncGenerator as AsyncGenerator
else:
    class AsyncGenerator(AsyncIterator[T_co], Generic[T_co, T_contra]):
        @abstractmethod
        async def __anext__(self) -> T_co: ...
        @abstractmethod
        async def asend(self, value: T_contra) -> T_co: ...
        @abstractmethod
        async def athrow(
            self,
            exc_type: Type[BaseException],
            exc_value: Optional[BaseException] = ...,
            exc_traceback: Optional[TracebackType] = ...,
        ) -> T_co: ...
        @abstractmethod
        async def aclose(self) -> None: ...
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

class CompatAsyncGenerator(
    AsyncGenerator[T_co, T_contra], Generic[T_co, T_contra, T_co2], metaclass=ABCMeta
):
    async def __anext__(self) -> T_co: ...
    async def asend(self, value: T_contra) -> T_co: ...
    async def athrow(
        self,
        exc_type: Type[BaseException],
        exc_value: Optional[BaseException] = ...,
        exc_traceback: Optional[TracebackType] = ...,
    ) -> T_co: ...
    # aclose() should return None but the stubs in typeshed for 3.6+ say
    # it returns the YieldType, so we need to use Any to be compatible
    # (https://github.com/python/typeshed/issues/2785)
    async def aclose(self) -> Any: ...
    def __aiter__(self) -> AsyncGenerator[T_co, T_contra]: ...
    @property
    def ag_await(self) -> Any: ...
    @property
    def ag_code(self) -> CodeType: ...
    @property
    def ag_frame(self) -> FrameType: ...
    @property
    def ag_running(self) -> bool: ...

class YieldType(Generic[T_co]):
    pass

class SendType(Generic[T_contra]):
    pass
