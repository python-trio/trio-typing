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
from trio_typing import AsyncGenerator, CompatAsyncGenerator, YieldType, SendType
from typing_extensions import Protocol

_T = TypeVar("_T")

# The returned async generator's YieldType and SendType and the
# argument types of the decorated function get inferred by
# trio_typing.plugin
def async_generator(
    __fn: Callable[..., Awaitable[_T]]
) -> Callable[..., CompatAsyncGenerator[Any, Any, _T]]: ...

# The return type and a more specific argument type can be
# inferred by trio_typing.plugin, based on the enclosing
# @async_generator's YieldType and SendType
@overload
async def yield_() -> Any: ...
@overload
async def yield_(obj: object) -> Any: ...
@overload
async def yield_from_(agen: CompatAsyncGenerator[Any, Any, _T]) -> _T: ...
@overload
async def yield_from_(agen: AsyncGenerator[Any, Any]) -> None: ...
@overload
async def yield_from_(agen: AsyncIterable[Any]) -> None: ...
def isasyncgen(obj: object) -> bool: ...
def isasyncgenfunction(obj: object) -> bool: ...

# Argument types of the decorated function get inferred by
# trio_typing.plugin
def asynccontextmanager(
    fn: Callable[..., AsyncIterator[_T]]
) -> Callable[..., AsyncContextManager[_T]]: ...

class _AsyncCloseable(Protocol):
    async def aclose(self) -> None: ...

_T_closeable = TypeVar("_T_closeable", bound=_AsyncCloseable)

def aclosing(obj: _T_closeable) -> AsyncContextManager[_T_closeable]: ...

_AsyncGenHooks = NamedTuple(
    "AsyncGenHooks",
    [
        ("firstiter", Optional[Callable[[AsyncGenerator[Any, Any]], Any]]),
        ("finalizer", Optional[Callable[[AsyncGenerator[Any, Any]], Any]]),
    ],
)

def get_asyncgen_hooks() -> _AsyncGenHooks: ...
def set_asyncgen_hooks(
    firstiter: Optional[Callable[[AsyncGenerator[Any, Any]], Any]] = ...,
    finalizer: Optional[Callable[[AsyncGenerator[Any, Any]], Any]] = ...,
) -> None: ...
