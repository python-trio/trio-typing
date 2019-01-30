import sys
from typing import Callable, List, Optional, cast
from typing import Type as typing_Type
from mypy.plugin import Plugin, FunctionContext, MethodContext
from mypy.nodes import ARG_POS, ARG_STAR
from mypy.types import (
    Type, CallableType, NoneTyp, Overloaded, TypeVarDef, TypeVarType, Instance
)


class TrioPlugin(Plugin):
    def get_function_hook(
        self, fullname: str
    ) -> Optional[Callable[[FunctionContext], Type]]:
        if fullname in (
            "contextlib.asynccontextmanager", "async_generator.asynccontextmanager",
            "async_generator.async_generator", "trio_typing.async_generator"
        ):
            return args_invariant_decorator_callback
        if fullname == "trio_typing.takes_callable_and_args":
            return takes_callable_and_args_callback
        if fullname in ("__call__ of _AgenMaker1", "__call__ of _AgenMaker2"):
            return args_invariant_decorator_callback
        if fullname == "async_generator.yield_":
            return async_generator_callback
        return None

    def get_method_hook(
        self, fullname: str
    ) -> Optional[Callable[[MethodContext], Type]]:
        if fullname == "trio_typing.TaskStatus.started":
            return started_callback
        return None


def args_invariant_decorator_callback(ctx: FunctionContext) -> Type:
    """Infer a better return type for 'asynccontextmanager', 'async_generator',
    and other decorators that modify their argument callable's return type
    but not its argument types.
    """
    # (adapted from the contextmanager support in mypy's builtin plugin)
    if ctx.arg_types and len(ctx.arg_types[0]) == 1:
        arg_type = ctx.arg_types[0][0]
        if (
            isinstance(arg_type, CallableType)
            and isinstance(ctx.default_return_type, CallableType)
        ):
            # The stub signature doesn't preserve information about arguments so
            # add them back here.
            return ctx.default_return_type.copy_modified(
                arg_types=arg_type.arg_types,
                arg_kinds=arg_type.arg_kinds,
                arg_names=arg_type.arg_names,
                variables=arg_type.variables,
                is_ellipsis_args=arg_type.is_ellipsis_args,
            )
    return ctx.default_return_type


def async_generator_callback(ctx: FunctionContext) -> Type:
    """Handle @async_generato(yield_type=X) and so on.

    @async_generator(yield_type=X) def fn: ... winds up calling
    _AgenMaker1[X]().__call__(fn). If a send_type Y is also
    specified, it's _AgenMaker2[X, Y]().__call__(fn).
    This hook intercepts _AgenMaker1.__call__ and
    _AgenMaker2.__call__, fixes up the return type's arguments
    in the same manner as args_invariant_decorator_callback,
    and also tries to provide a typechecking context for
    'await yield_' and 'await yield_from_' calls inside
    the async generator.
    """
    import pdb; pdb.set_trace()
    return args_invariant_decorator_callback(ctx)


def started_callback(ctx: MethodContext) -> Type:
    """Raise an error if task_status.started() is called without an argument
    and the TaskStatus is not declared to accept a result of type None.
    """
    if (
        (not ctx.arg_types or not ctx.arg_types[0])
        and isinstance(ctx.type, Instance)
        and ctx.type.args
        and not isinstance(ctx.type.args[0], NoneTyp)
    ):
        ctx.api.fail(
            "TaskStatus.started() requires an argument for types other than "
            "TaskStatus[None]",
            ctx.context
        )
    return ctx.default_return_type


def takes_callable_and_args_callback(ctx: FunctionContext) -> Type:
    """Automate the boilerplate for writing functions that accept
    arbitrary positional arguments of the same type accepted by
    a callable.

    For example, this supports writing::

        @trio_typing.takes_callable_and_args
        def start_soon(
            self,
            async_fn: Callable[[trio_typing.ArgsForCallable], None],
            *args: trio_typing.ArgsForCallable,
        ) -> None: ...

    instead of::

        T1 = TypeVar("T1")
        T2 = TypeVar("T2")
        T3 = TypeVar("T3")
        T4 = TypeVar("T4")

        @overload
        def start_soon(
            self,
            async_fn: Callable[[], None],
        ) -> None: ...

        @overload
        def start_soon(
            self,
            async_fn: Callable[[T1], None],
            __arg1: T1,
        ) -> None: ...

        @overload
        def start_soon(
            self,
            async_fn: Callable[[T1, T2], None],
            __arg1: T1,
            __arg2: T2
        ) -> None: ...

        # etc

    """
    try:
        if (
            not ctx.arg_types
            or len(ctx.arg_types[0]) != 1
            or not isinstance(ctx.arg_types[0][0], CallableType)
            or not isinstance(ctx.default_return_type, CallableType)
        ):
            raise ValueError("must be used as a decorator")

        fn_type: CallableType = ctx.arg_types[0][0]
        callable_idx: int = -1  # index in function arguments of the callable
        callable_args_idx: int = -1  # index in callable arguments of the StarArgs
        args_idx: int = -1  # index in function arguments of the StarArgs

        for idx, (kind, ty) in enumerate(zip(fn_type.arg_kinds, fn_type.arg_types)):
            if (
                isinstance(ty, Instance)
                and ty.type.fullname() == "trio_typing.ArgsForCallable"
            ):
                if kind != ARG_STAR:
                    raise ValueError(
                        "ArgsForCallable must be used with a *args argument "
                        "in the decorated function"
                    )
                assert args_idx == -1
                args_idx = idx
            elif isinstance(ty, CallableType) and kind == ARG_POS:
                for idx_, (kind_, ty_) in enumerate(zip(ty.arg_kinds, ty.arg_types)):
                    if (
                        isinstance(ty_, Instance)
                        and ty_.type.fullname() == "trio_typing.ArgsForCallable"
                    ):
                        if kind != ARG_POS:
                            raise ValueError(
                                "ArgsForCallable must be used with a positional "
                                "argument in the callable type that the decorated "
                                "function takes"
                            )
                        if callable_idx != -1:
                            raise ValueError(
                                "ArgsForCallable may only be used once as the type "
                                "of an argument to a callable type that the "
                                "decorated function takes"
                            )
                        callable_idx = idx
                        callable_args_idx = idx_
        if args_idx == -1:
            raise ValueError(
                "decorated function must take *args with type "
                "trio_typing.ArgsForCallable"
            )
        if callable_idx == -1:
            raise ValueError(
                "decorated function must take a callable that has an "
                "argument of type trio_typing.ArgsForCallable"
            )

        expanded_fns: List[CallableType] = []
        type_var_defs: List[TypeVarDef] = []
        type_var_types: List[Type] = []
        for arg_idx in range(1, 5):
            callable_ty = cast(CallableType, fn_type.arg_types[callable_idx])
            arg_types = list(fn_type.arg_types)
            arg_types[callable_idx] = callable_ty.copy_modified(
                arg_types=(
                    callable_ty.arg_types[:callable_args_idx]
                    + type_var_types
                    + callable_ty.arg_types[callable_args_idx + 1 :]
                ),
                arg_kinds=(
                    callable_ty.arg_kinds[:callable_args_idx]
                    + ([ARG_POS] * len(type_var_types))
                    + callable_ty.arg_kinds[callable_args_idx + 1 :]
                ),
                arg_names=(
                    callable_ty.arg_names[:callable_args_idx]
                    + ([None] * len(type_var_types))
                    + callable_ty.arg_names[callable_args_idx + 1 :]
                ),
                variables=(
                    callable_ty.variables + type_var_defs
                ),
            )
            expanded_fns.append(
                fn_type.copy_modified(
                    arg_types=(
                        arg_types[:args_idx]
                        + type_var_types
                        + arg_types[args_idx + 1 :]
                    ),
                    arg_kinds=(
                        fn_type.arg_kinds[:args_idx]
                        + ([ARG_POS] * len(type_var_types))
                        + fn_type.arg_kinds[args_idx + 1 :]
                    ),
                    arg_names=(
                        fn_type.arg_names[:args_idx]
                        + ([None] * len(type_var_types))
                        + fn_type.arg_names[args_idx + 1 :]
                    ),
                    variables=(
                        fn_type.variables + type_var_defs
                    ),
                )
            )
            type_var_defs.append(
                TypeVarDef(
                    f"__T{arg_idx}",
                    f"__T{arg_idx}",
                    -len(fn_type.variables) - arg_idx - 1,
                    [],
                    ctx.api.named_generic_type("builtins.object", []),
                )
            )
            type_var_types.append(
                TypeVarType(type_var_defs[-1], ctx.context.line, ctx.context.column)
            )
        return Overloaded(expanded_fns)

    except ValueError as ex:
        ctx.api.fail(f"invalid use of @takes_callable_and_args: {ex}", ctx.context)
        return ctx.default_return_type


def plugin(version: str) -> typing_Type[Plugin]:
    return TrioPlugin
