from typing import (
    Any,
    AsyncGenerator,
    Awaitable,
    Callable,
    Generator,
    Generic,
    NoReturn,
    TypeVar,
    Union,
)

T = TypeVar("T")
U = TypeVar("U")

class Value(Generic[T]):
    value: T
    def __init__(self, value: T): ...
    def unwrap(self) -> T: ...
    def send(self, gen: Generator[U, T, Any]) -> U: ...
    async def asend(self, gen: AsyncGenerator[U, T]) -> U: ...

class Error:
    error: BaseException
    def __init__(self, error: BaseException): ...
    def unwrap(self) -> NoReturn: ...
    def send(self, gen: Generator[U, Any, Any]) -> U: ...
    async def asend(self, gen: AsyncGenerator[U, Any]) -> U: ...

Outcome = Union[Value[T], Error]

# TODO: plugin
def capture(sync_fn: Callable[..., T], *args: Any, **kwargs: Any) -> Outcome[T]: ...
async def acapture(
    async_fn: Callable[..., Awaitable[T]], *args: Any, **kwargs: Any
) -> Outcome[T]: ...
