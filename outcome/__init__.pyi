from typing import (
    Generator, AsyncGenerator, Callable, Any, Awaitable, Generic, TypeVar,
    NoReturn, Union,
)

T = TypeVar('T')

class Value(Generic[T]):
    value: T
    def unwrap(self) -> T: ...
    def send(self, gen: Generator[Any, T, Any]) -> None: ...
    async def asend(self, gen: AsyncGenerator[T, Any]) -> None: ...

class Error:
    error: BaseException
    def unwrap(self) -> NoReturn: ...
    def send(self, gen: Generator[Any, Any, Any]) -> None: ...
    async def asend(self, gen: AsyncGenerator[Any, Any]) -> None: ...

Outcome = Union[Value[T], Error]

def capture(
    sync_fn: Callable[..., T], *args: Any, **kwargs: Any
) -> Outcome[T]: ...

async def acapture(
    async_fn: Callable[..., Awaitable[T]], *args: Any, **kwargs: Any
) -> Outcome[T]: ...
