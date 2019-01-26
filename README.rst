trio-typing: static typing for Trio and related projects
========================================================

This repository provides:

* PEP 561 typing stubs packages for the Trio project packages:

  * `trio <https://github.com/python-trio/trio>`__ (``trio-stubs``)

  * `outcome <https://github.com/python-trio/outcome>`__ (``outcome-stubs``)

  * `async_generator <https://github.com/python-trio/async_generator>`__
    (``async_generator-stubs``)

* A package ``trio_typing`` containing types that Trio programs often want
  to refer to (``Nursery``, ``CancelScope``, ``TaskStatus[T]``) and a mypy
  plugin that smooths over some limitations in the basic type hints.

Quickstart
~~~~~~~~~~

Install with::

    pip install -U trio-typing

Optionally enable the plugin in your ``mypy.ini``::

    [mypy]
    plugins = trio_typing.plugin

Example
~~~~~~~

::

    from async_generator import asynccontextmanager
    from typing import AsyncIterator
    from trio_typing import CancelScope, Nursery, TaskStatus

    @asynccontextmanager
    async def open_daemon_nursery() -> AsyncIterator[Tuple[Nursery, Nursery]]:
        async with trio.open_nursery() as daemonic_part:
            async with trio.open_nursery() as regular_part:
                yield (regular_part, daemonic_part)
            daemonic_part.cancel_scope.cancel()

    async def sleep_at_most(
        seconds: float, *, task_status: TaskStatus[CancelScope] = trio.TASK_STATUS_IGNORED
    ) -> None:
        with trio.move_on_after(seconds) as cancel_scope:
            task_status.started(cancel_scope)
            await trio.sleep_forever()

    async def example() -> None:
        async with trio.open_nursery() as nursery:
            cancel_scope = await nursery.start_soon(sleep_at_most, 5)
            await trio.sleep(1)
            cancel_scope.cancel()

Limitations
~~~~~~~~~~~

[TODO]

License
~~~~~~~

Your choice of MIT or Apache 2.0.
