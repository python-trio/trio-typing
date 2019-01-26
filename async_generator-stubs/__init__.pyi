from typing import (
    Any,
    AsyncContextManager,
    AsyncGenerator,
    AsyncIterator,
    Awaitable,
    Callable,
    NamedTuple,
    Optional,
    TypeVar,
)
from typing_extensions import Protocol

# PLUGIN: ugh
def async_generator(
    fn: Callable[..., Awaitable[None]]
) -> Callable[..., AsyncIterator[Any]]: ...
def yield_(obj: object) -> Any: ...
def yield_from_(agen: AsyncIterator[Any]) -> Any: ...
def isasyncgen(obj: object) -> bool: ...
def isasyncgenfunction(obj: object) -> bool: ...

_T = TypeVar("_T")

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
