import abc as _abc
import sys as _sys
import typing as _t
import async_generator as _ag
import trio as _trio
from ._version import __version__

_T = _t.TypeVar("_T")
_T_co = _t.TypeVar("_T_co", covariant=True)
_T_co2 = _t.TypeVar("_T_co2", covariant=True)
_T_contra = _t.TypeVar("_T_contra", contravariant=True)

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

if _sys.version_info >= (3, 6):
    from typing import AsyncGenerator

else:
    class AsyncGenerator(
        _t.AsyncIterator[_T_co],
        _t.Generic[_T_co, _T_contra],
    ):
        pass

class AsyncGeneratorWithReturn(
    AsyncGenerator[_T_co, _T_contra], _t.Generic[_T_co, _T_contra, _T_co2]
):
    pass

AsyncGeneratorWithReturn.register(_ag._impl.AsyncGenerator)

class YieldType(_t.Generic[_T_co]):
    pass

class SendType(_t.Generic[_T_contra]):
    pass
