import abc as _abc
import trio as _trio
import typing as _t
from ._version import __version__

_T = _t.TypeVar("_T")

class ArgsForCallable:
    pass

def takes_callable_and_args(fn):
    return fn

class Nursery(metaclass=_abc.ABCMeta):
    pass
Nursery.register(_trio._core._run.Nursery)

class CancelScope(metaclass=_abc.ABCMeta):
    pass
CancelScope.register(_trio._core._run.CancelScope)

class TaskStatus(_t.Generic[_T], metaclass=_abc.ABCMeta):
    pass
TaskStatus.register(_trio._core._run._TaskStatus)
