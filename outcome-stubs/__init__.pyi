from typing import (
    Any,
    Awaitable,
    Callable,
    Generator,
    Generic,
    NoReturn,
    Optional,
    Type,
    TypeVar,
    Union,
)
from types import TracebackType
from typing_extensions import Protocol

T = TypeVar("T")
U = TypeVar("U")
T_co = TypeVar("T_co", covariant=True)
T_contra = TypeVar("T_contra", contravariant=True)

# Can't use AsyncGenerator as it creates a dependency cycle
# (outcome stubs -> trio_typing stubs -> trio.hazmat stubs -> outcome)
class _ASendable(Protocol[T_contra, T_co]):
    async def asend(self, value: T_contra) -> T_co: ...
    async def athrow(
        self,
        exc_type: Type[BaseException],
        exc_value: Optional[BaseException] = ...,
        exc_traceback: Optional[TracebackType] = ...,
    ) -> T_co: ...

class Value(Generic[T]):
    value: T
    def __init__(self, value: T): ...
    def unwrap(self) -> T: ...
    def send(self, gen: Generator[U, T, Any]) -> U: ...
    async def asend(self, gen: _ASendable[T, U]) -> U: ...

class Error:
    error: BaseException
    def __init__(self, error: BaseException): ...
    def unwrap(self) -> NoReturn: ...
    def send(self, gen: Generator[U, Any, Any]) -> U: ...
    async def asend(self, gen: _ASendable[Any, U]) -> U: ...

Outcome = Union[Value[T], Error]

# TODO: narrower typing for these (the args and kwargs should
# be acceptable to the callable)
def capture(sync_fn: Callable[..., T], *args: Any, **kwargs: Any) -> Outcome[T]: ...
async def acapture(
    async_fn: Callable[..., Awaitable[T]], *args: Any, **kwargs: Any
) -> Outcome[T]: ...
