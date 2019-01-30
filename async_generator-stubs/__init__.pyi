import sys
from typing import (
    Any,
    AsyncContextManager,
    AsyncIterable,
    AsyncIterator,
    Awaitable,
    Callable,
    Generic,
    NamedTuple,
    Optional,
    TypeVar,
    Union,
    overload,
)
from trio_typing import AsyncGenerator, AsyncGeneratorWithReturn, YieldType, SendType
from typing_extensions import Protocol

_T = TypeVar("_T")

@overload
def async_generator(
    __fn: Callable[..., Awaitable[None]]
) -> Callable[..., AsyncGenerator[Any, Any]]: ...
@overload
def async_generator(
    __fn: Callable[..., Awaitable[_T]]
) -> Callable[..., AsyncGeneratorWithReturn[Any, Any, _T]]: ...

@overload
async def yield_() -> Any: ...
@overload
async def yield_(obj: object) -> Any: ...
@overload
async def yield_from_(agen: AsyncGeneratorWithReturn[Any, Any, _T]) -> _T: ...
@overload
async def yield_from_(agen: AsyncGenerator[Any, Any]) -> None: ...
@overload
async def yield_from_(agen: AsyncIterable[Any]) -> None: ...
def isasyncgen(obj: object) -> bool: ...
def isasyncgenfunction(obj: object) -> bool: ...

def asynccontextmanager(
    fn: Callable[..., AsyncIterator[_T]]
) -> Callable[..., AsyncContextManager[_T]]: ...

class _AsyncCloseable(Protocol):
    async def aclose(self) -> None: ...

_T_closeable = TypeVar("_T_closeable", bound=_AsyncCloseable)

def aclosing(obj: _T_closeable) -> AsyncContextManager[_T_closeable]: ...

class _AsyncGenHooks(NamedTuple):
    firstiter: Optional[Callable[[AsyncGenerator[Any, Any]], None]]
    finalizer: Optional[Callable[[AsyncGenerator[Any, Any]], None]]

def get_asyncgen_hooks() -> _AsyncGenHooks: ...
def set_asyncgen_hooks(
    *,
    firstiter: Optional[Callable[[AsyncGenerator[Any, Any]], None]] = ...,
    finalizer: Optional[Callable[[AsyncGenerator[Any, Any]], None]] = ...,
) -> None: ...
