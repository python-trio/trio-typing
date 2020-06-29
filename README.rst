.. image:: https://img.shields.io/pypi/v/trio-typing.svg
   :target: https://pypi.org/project/trio-typing
   :alt: Latest PyPI version

.. image:: https://travis-ci.org/python-trio/trio-typing.svg?branch=master
   :target: https://travis-ci.org/python-trio/trio-typing
   :alt: Automated test status

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
   :target: https://github.com/ambv/black
   :alt: Code style: black

.. image:: http://www.mypy-lang.org/static/mypy_badge.svg
   :target: http://www.mypy-lang.org/
   :alt: Checked with mypy

trio-typing: static typing for Trio and related projects
========================================================

This repository provides:

* PEP 561 typing stubs packages for the Trio project packages:

  * `trio <https://github.com/python-trio/trio>`__ (``trio-stubs``)

  * `outcome <https://github.com/python-trio/outcome>`__ (``outcome-stubs``)

  * `async_generator <https://github.com/python-trio/async_generator>`__
    (``async_generator-stubs``)

* A package ``trio_typing`` containing types that Trio programs often want
  to refer to (``AsyncGenerator[Y, S]`` and ``TaskStatus[T]``) and a mypy
  plugin that smooths over some limitations in the basic type hints.
  (``Nursery`` is exported publicly by mainline Trio as of version 0.12.0.)


Supported platforms
~~~~~~~~~~~~~~~~~~~

Like Trio, we require Python 3.6 or later. Both PyPy and CPython are
supported at runtime, but type checking must occur on CPython (due to
limitations of mypy).  We test on Linux using the latest releases
from the 3.6, 3.7, and 3.8 branches, as well as 3.9-dev nightly. We're
not knowingly doing anything OS-specific, so other OSes should work
too.

Type checkers other than mypy are not supported, but might work.
Experience reports and patches to add support are welcome.


Quickstart
~~~~~~~~~~

Install with::

    pip install -U trio-typing

Enable the plugin in your ``mypy.ini`` (optional, but recommended)::

    [mypy]
    plugins = trio_typing.plugin

Start running mypy on your Trio code! You may want to import some typing
names from ``trio_typing``, like ``TaskStatus``; see below
for more details.


What's in the box?
~~~~~~~~~~~~~~~~~~

The stubs packages provide types for all public non-deprecated APIs of
``trio``, ``outcome``, and ``async_generator``, as of the release date
of the corresponding ``trio-typing`` distribution. You don't need to
explicitly configure these; just say ``import trio`` (for example)
and mypy will know to look in ``trio-stubs`` for the type information.

The ``trio_typing`` package provides:

* ``TaskStatus[T]``, the type of the object passed as the ``task_status``
  argument to a task started with ``nursery.start()``. The type parameter
  ``T`` is the type of the value the task provides to be returned from
  ``nursery.start()``. This is implemented as an ABC, and the actual
  private types inside Trio are registered as virtual subclasses
  of it. So, you can't instantiate ``trio_typing.TaskStatus``, but
  ``isinstance(task_status, trio_typing.TaskStatus)`` where ``task_status``
  is a Trio task status object does return True.

* (Previous versions of ``trio_typing`` provided an analogous ABC for
  ``Nursery``, but the actual class is available as ``trio.Nursery`` as of
  Trio 0.12.0; you should use that instead.)

* A backport of ``typing.AsyncGenerator[YieldT, SendT]`` to Python 3.5.
  (``YieldT`` is the type of values yielded by the generator, and
  ``SendT`` is the type of values it accepts as an argument to ``asend()``.)
  This is an abstract class describing the async generator interface:
  ``AsyncIterator`` plus ``asend``, ``athrow``, ``aclose``, and the
  ``ag_*`` introspection attributes. On 3.6+, ``trio_typing.AsyncGenerator``
  is just a reexport of ``typing.AsyncGenerator``.

* ``CompatAsyncGenerator[YieldT, SendT, ReturnT]``,
  a name for the otherwise-anonymous concrete async generator type
  returned by ``@async_generator`` functions. It is a subtype of
  ``AsyncGenerator[YieldT, SendT]`` and provides the same methods.
  (Native async generators don't have a ``ReturnT``; it is only relevant
  in determining the return type of ``await async_generator.yield_from_()``.)

* A few types that are only useful with the mypy plugin: ``YieldType[T]``,
  ``SendType[T]``, and the decorator ``@takes_callable_and_args``.

The ``trio_typing.plugin`` mypy plugin provides:

* Argument type checking for functions decorated with
  ``@asynccontextmanager`` (either the one in ``async_generator`` or the
  one in 3.7+ ``contextlib``) and ``@async_generator``

* Inference of more specific ``trio.open_file()`` and ``trio.Path.open()``
  return types based on constant ``mode`` and ``buffering`` arguments, so
  ``await trio.open_file("foo", "rb", 0)`` returns an unbuffered async
  file object in binary mode and ``await trio.open_file("bar")`` returns
  an async file object in text mode

* Signature checking for ``task_status.started()`` with no arguments,
  so it raises an error if the ``task_status`` object is not of type
  ``TaskStatus[None]``

* Boilerplate reduction for functions that take parameters ``(fn, *args)``
  and ultimately invoke ``fn(*args)``: just write::

      from mypy_extensions import VarArg

      @trio_typing.takes_callable_and_args
      def start_soon(
          async_fn: Callable[[VarArg()], Awaitable[T]],
          *args: Any,
          other_keywords: str = are_ok_too,
      ):
          # your implementation here

  ``start_soon(async_fn, *args)`` will raise an error if ``async_fn(*args)``
  would do so. You can also make the callable take some non-splatted
  arguments; the ``*args`` get inserted at whatever position in the
  argument list you write ``VarArg()``.

  The above example will always fail when the plugin is not being
  used. If you want to always pass in such cases, you can use a union::

      @trio_typing.takes_callable_and_args
      def start_soon(
          async_fn: Union[
              Callable[..., Awaitable[T]],
              Callable[[VarArg()], Awaitable[T]],
          ],
          *args: Any,
          other_keywords: str = are_ok_too,
      ):
          # your implementation here

  Without the plugin, this type-checks fine (and allows inference of
  ``T``), since any callable will match the ``Callable[...,
  Awaitable[T]]`` option. With the plugin, the entire union will be
  replaced with specific argument types.

  Note: due to mypy limitations, we only support a maximum of 5
  positional arguments, and keyword arguments can't be passed in this way;
  ``nursery.start_soon(functools.partial(...))`` will pass the type checker
  but won't be able to actually check the argument types.

* Mostly-full support for type checking ``@async_generator`` functions.
  You write the decorated function as if it returned a union of its actual
  return type, its yield type wrapped in ``YieldType[]``, and its send
  type wrapped in ``SendType[]``::

      from trio_typing import YieldType, SendType
      @async_generator
      async def sleep_and_sqrt() -> Union[None, SendType[int], YieldType[float]]:
          next_yield = 0.0
          while True:
              amount = await yield_(next_yield)  # amount is an int
              if amount < 0:
                  return None
              await trio.sleep(amount)
              next_yield = math.sqrt(amount)

      # prints: CompatAsyncGenerator[float, int, None]
      reveal_type(sleep_and_sqrt())

  Calls to ``yield_`` and ``yield_from_`` inside an ``@async_generator``
  function are type-checked based on these declarations. If you leave
  off *either* the yield type or send type, the missing one is assumed
  to be ``None``; if you leave off *both* (writing just
  ``async def sleep_and_sqrt() -> None:``, like you would if you weren't
  using the plugin), they're both assumed to be ``Any``.

  Note the explicit ``return None``; mypy won't accept ``return`` or
  falling off the end of the function, unless you run it with
  ``--no-warn-no-return``.


Limitations
~~~~~~~~~~~

* Calls to variadic Trio functions like ``trio.run()``,
  ``nursery.start_soon()``, and so on, only can type-check up to five
  positional arguments. (This number could be increased easily, but
  only at the cost of slower typechecking for everyone; mypy's current
  architecture requires that we generate overload sets initially for
  every arity we want to be able to use.) You can work around this with
  a ``# type: ignore`` comment.

* ``outcome.capture()`` and ``outcome.acapture()`` currently don't typecheck
  their arguments at all.


Running the tests
~~~~~~~~~~~~~~~~~

``trio-typing`` comes with a fairly extensive testsuite; it doesn't test all
the mechanical parts of the stubs, but does exercise most of the interesting
plugin behavior. You can run it after installing, with::

    pytest -p trio_typing._tests.datadriven --pyargs trio_typing


License
~~~~~~~

Your choice of MIT or Apache 2.0.
