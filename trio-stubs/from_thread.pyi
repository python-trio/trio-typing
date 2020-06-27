import trio
from typing import Any, Awaitable, Callable, Optional, TypeVar, Union
from trio_typing import takes_callable_and_args
from mypy_extensions import VarArg

T = TypeVar("T")
@takes_callable_and_args
def run(
    afn: Union[Callable[..., Awaitable[T]], Callable[[VarArg()], Awaitable[T]]],
    *args: Any,
    trio_token: Optional[trio.lowlevel.TrioToken] = ...,
) -> T: ...
@takes_callable_and_args
def run_sync(
    fn: Union[Callable[..., T], Callable[[VarArg()], T]],
    *args: Any,
    trio_token: Optional[trio.lowlevel.TrioToken] = ...,
) -> T: ...
