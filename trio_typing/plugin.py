import sys
import itertools
from typing import Callable, List, Optional, Tuple, cast
from typing import Type as typing_Type
from collections import OrderedDict
from mypy.plugin import Plugin, FunctionContext, MethodContext, AttributeContext, MethodSigContext
from mypy.nodes import (
    ARG_POS, ARG_OPT, ARG_STAR, ARG_NAMED, ARG_STAR2, ARG_NAMED_OPT,
    TypeInfo, Context, FuncDef
)
from mypy.types import (
    Type, CallableType, NoneTyp, Overloaded, TypeVarDef, TypeVarType, Instance,
    UnionType, UninhabitedType, AnyType, TupleType, TypedDictType, TypeOfAny
)
from mypy.constraints import infer_constraints, SUPERTYPE_OF
from mypy.checker import TypeChecker
from mypy.argmap import map_actuals_to_formals


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


######################################################################
# @async_generator

def decode_agen_types_from_return_type(
    ctx: FunctionContext, original_async_return_type: Type
) -> Tuple[Optional[Type], Optional[Type], Type]:
    if isinstance(original_async_return_type, UnionType):
        arms = original_async_return_type.items
    else:
        arms = [original_async_return_type]
    yield_type: Optional[Type] = None
    send_type: Optional[Type] = None
    other_arms: List[Type] = []
    try:
        for arm in arms:
            if isinstance(arm, Instance):
                if arm.type.fullname() == "trio_typing.YieldType":
                    if len(arm.args) != 1:
                        raise ValueError("YieldType must take one argument")
                    if yield_type is not None:
                        raise ValueError("YieldType specified multiple times")
                    yield_type = arm.args[0]
                elif arm.type.fullname() == "trio_typing.SendType":
                    if len(arm.args) != 1:
                        raise ValueError("SendType must take one argument")
                    if send_type is not None:
                        raise ValueError("SendType specified multiple times")
                    send_type = arm.args[0]
                else:
                    other_arms.append(arm)
            else:
                other_arms.append(arm)
    except ValueError as ex:
        ctx.api.fail(f"invalid @async_generator return type: {ex}", ctx.context)
        return None, None, original_async_return_type

    if yield_type is None and send_type is None:
        return None, None, original_async_return_type

    if yield_type is None:
        yield_type = NoneTyp(ctx.context.line, ctx.context.column)
    if send_type is None:
        send_type = NoneTyp(ctx.context.line, ctx.context.column)
    if not other_arms:
        return yield_type, send_type, UninhabitedType(
            is_noreturn=True, line=ctx.context.line, column=ctx.context.column
        )
    else:
        return yield_type, send_type, UnionType.make_simplified_union(
            other_arms, ctx.context.line, ctx.context.column
        )


def async_generator_callback(ctx: FunctionContext) -> Type:
    """Handle @async_generator."""
    new_return_type = args_invariant_decorator_callback(ctx)
    if (
        isinstance(new_return_type, CallableType)
        and isinstance(new_return_type.ret_type, Instance)
        and new_return_type.ret_type.type.fullname() == (
            'trio_typing.AsyncGeneratorWithReturn'
        )
        and len(new_return_type.ret_type.args) == 3
    ):
        yield_type, send_type, yf_return_type = decode_agen_types_from_return_type(
            ctx, new_return_type.ret_type.args[2]
        )
        if yield_type is None or send_type is None:
            return new_return_type
        return new_return_type.copy_modified(
            ret_type=new_return_type.ret_type.copy_modified(
                args=[yield_type, send_type, yf_return_type]
            )
        )
    return new_return_type


def decode_enclosing_agen_types(
    ctx: FunctionContext
) -> Tuple[Optional[Type], Optional[Type]]:

    private_api = cast(TypeChecker, ctx.api)
    enclosing_func = private_api.scope.top_function()
    if (
        enclosing_func is None
        or not isinstance(enclosing_func, FuncDef)
        or not enclosing_func.is_coroutine
        or not enclosing_func.is_decorated
    ):
        # we can't actually detect the @async_generator decorator but
        # we'll at least notice if it couldn't possibly be present
        ctx.api.fail(
            "async_generator.yield_() outside an @async_generator func", ctx.context
        )
        return None, None

    if (
        isinstance(enclosing_func.type, CallableType)
        and isinstance(enclosing_func.type.ret_type, Instance)
        and enclosing_func.type.ret_type.type.fullname() == "typing.Coroutine"
        and len(enclosing_func.type.ret_type.args) == 3
        and isinstance(enclosing_func.type.ret_type.args[0], AnyType)
        and isinstance(enclosing_func.type.ret_type.args[1], AnyType)
        and isinstance(enclosing_func.type.ret_type.args[2], UnionType)
    ):
        yield_type, send_type, _ = decode_agen_types_from_return_type(
            ctx, enclosing_func.type.ret_type.args[2]
        )
        return yield_type, send_type

    return None, None


def yield_callback(ctx: FunctionContext) -> Type:
    """Provide a more specific argument and return type for yield_()."""
    if len(ctx.arg_types) == 0:
        arg_type = NoneTyp(ctx.context.line, ctx.context.column)  # type: Type
    elif ctx.arg_types and len(ctx.arg_types[0]) == 1:
        arg_type = ctx.arg_types[0][0]
    else:
        return ctx.default_return_type

    private_api = cast(TypeChecker, ctx.api)
    yield_type, send_type = decode_enclosing_agen_types(ctx)
    if yield_type is not None and send_type is not None:
        private_api.check_subtype(
            subtype=arg_type,
            supertype=yield_type,
            context=ctx.context,
            subtype_label="yield_ argument",
            supertype_label="declared YieldType",
        )
        return ctx.api.named_generic_type("typing.Awaitable", [send_type])

    return ctx.default_return_type


def yield_from_callback(ctx: FunctionContext) -> Type:
    """Provide a better typecheck for yield_from_()."""
    if ctx.arg_types and len(ctx.arg_types[0]) == 1:
        arg_type = ctx.arg_types[0][0]
    else:
        return ctx.default_return_type

    private_api = cast(TypeChecker, ctx.api)
    our_yield_type, our_send_type = decode_enclosing_agen_types(ctx)
    if our_yield_type is None or our_send_type is None:
        return ctx.default_return_type

    if (
        isinstance(arg_type, Instance)
        and arg_type.type.fullname() in (
            "trio_typing.AsyncGeneratorWithReturn",
            "trio_typing.AsyncGenerator",
            "typing.AsyncGenerator",
        )
        and len(arg_type.args) >= 2
    ):
        their_yield_type, their_send_type = arg_type.args[:2]
        private_api.check_subtype(
            subtype=their_yield_type,
            supertype=our_yield_type,
            context=ctx.context,
            subtype_label="yield_from_ argument YieldType",
            supertype_label="local declared YieldType",
        )
        private_api.check_subtype(
            subtype=our_send_type,
            supertype=their_send_type,
            context=ctx.context,
            subtype_label="local declared SendType",
            supertype_label="yield_from_ argument SendType",
        )
    elif isinstance(arg_type, Instance):
        private_api.check_subtype(
            subtype=arg_type,
            supertype=ctx.api.named_generic_type(
                "typing.AsyncIterable", [our_yield_type]
            ),
            context=ctx.context,
            subtype_label="yield_from_ argument type",
            supertype_label="expected iterable type",
        )

    return ctx.default_return_type


######################################################################
# TaskStatus.started()

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


######################################################################
# functools.partial

def partial_init_callback(ctx: FunctionContext) -> Type:
    # As defined in the stub file, functools.partial has one type parameter,
    # [0] the return type of the wrapped function. We give it additional fake
    # type parameters corresponding to:
    # [1]: the type of '.args', typically a tuple
    # [2]: the type of '.keywords', typically a TypedDict
    # [3]: the type of '.func', the function passed to partial()

    if len(ctx.args) != 3 or len(ctx.arg_types[0]) != 1:
        ctx.api.fail("improper functools.partial() invocation", ctx.context)
        return ctx.default_return_type

    func_type = ctx.arg_types[0][0]

    bound_args = []  # type: List[Type]
    bound_args_starred = []  # type: List[Type]
    seen_tuple_type = set()  # type: Set[TupleType]
    for kind, ty in zip(ctx.arg_kinds[1], ctx.arg_types[1]):
        if kind == ARG_STAR:
            if isinstance(ty, TupleType):
                # An invocation that uses *some_tuple will include
                # one entry in arg_types for each type in the tuple,
                # but they will all have the overall tuple type.
                # So we splat the whole tuple the first time we
                # see it, and ignore it thereafter.
                if ty not in seen_tuple_type:
                    seen_tuple_type.add(ty)
                    bound_args.extend(ty.items)
            else:
                # Invocation that splats something other than Tuple[X, Y].
                # This could be List[T], Tuple[U, ...], and so on.
                bound_args_starred.append(ty)
        else:
            bound_args.append(ty)

    args_type = None  # type: Type
    if not bound_args_starred:
        args_type = TupleType(
            bound_args,
            ctx.api.named_generic_type(
                "builtins.tuple", [AnyType(TypeOfAny.implementation_artifact)]
            )
        )
    elif (
        len(bound_args_starred) == 1
        and len(bound_args) == 0
        and isinstance(bound_args_starred[0], Instance)
        and len(bound_args_starred[0].args) == 1
    ):
        args_type = ctx.api.named_generic_type(
            "builtins.tuple", [bound_args_starred[0].args[0]]
        )
    else:
        args_type = ctx.api.named_generic_type(
            "builtins.tuple", [AnyType(TypeOfAny.implementation_artifact)]
        )

    bound_keywords = OrderedDict()  # type: OrderedDict[str, Type]
    bound_keywords_starred = []  # type: List[Type]

    for kind, name, ty in zip(ctx.arg_kinds[2], ctx.arg_names[2], ctx.arg_types[2]):
        if kind == ARG_STAR2:
            if isinstance(ty, TypedDictType):
                bound_keywords.update(ty.items)
            else:
                bound_keywords_starred.append(ty)
        else:
            assert name is not None
            bound_keywords[name] = ty

    keywords_type = None  # type: Type
    can_use_typeddict = "mypy_extensions" in ctx.api.modules  # type: ignore
    if not bound_keywords_starred and can_use_typeddict:
        keywords_type = TypedDictType(
            bound_keywords,
            set(bound_keywords.keys()),
            ctx.api.named_generic_type("mypy_extensions._TypedDict", []),
        )
    else:
        keywords_type = ctx.api.named_generic_type(
            "builtins.dict",
            [
                ctx.api.named_generic_type("builtins.str", []),
                AnyType(TypeOfAny.implementation_artifact),
            ],
        )

    if (
        isinstance(ctx.default_return_type, Instance)
        and ctx.default_return_type.type.fullname() == "functools.partial"
        and len(ctx.default_return_type.args) == 1
    ):
        return ctx.default_return_type.copy_modified(
            args=[
                ctx.default_return_type.args[0],
                args_type,
                keywords_type,
                func_type,
            ]
        )
    else:
        ctx.api.fail(
            "unexpected default return type in functools.partial() invocation",
            ctx.context,
        )
        return ctx.default_return_type


def partial_args_callback(ctx: AttributeContext) -> Type:
    if isinstance(ctx.type, Instance) and len(ctx.type.args) == 4:
        return ctx.type.args[1]
    return ctx.default_attr_type


def partial_keywords_callback(ctx: AttributeContext) -> Type:
    if isinstance(ctx.type, Instance) and len(ctx.type.args) == 4:
        return ctx.type.args[2]
    return ctx.default_attr_type


def partial_func_callback(ctx: AttributeContext) -> Type:
    if isinstance(ctx.type, Instance) and len(ctx.type.args) == 4:
        return ctx.type.args[3]
    return ctx.default_attr_type


def partial_call_callback(ctx: FunctionContext) -> Type:
    # We need to get the type of the functools.partial instance
    # we're invoking __call__ on, in order to get the bound
    # args/keywords types that we stashed in partial_init_callback.
    # But currently mypy doesn't provide that: instead of a method
    # hook for functools.partial.__call__ (which would provide the
    # self type), we get a function hook for "__call__ of partial",
    # and have to go groveling in our callstack for the self type.

    for idx in itertools.count():
        try:
            frame = sys._getframe(idx)
        except ValueError:
            ctx.api.fail(
                "hack for locating the callee type on a functools.partial "
                "invocation stopped working",
                ctx.context,
            )
            return ctx.default_return_type
        if frame.f_code.co_name == "check_call_expr_with_callee_type":
            callee_type = frame.f_locals["callee_type"]
            break

    if (
        not isinstance(callee_type, Instance)
        or callee_type.type.fullname() != "functools.partial"
        or len(callee_type.args) != 4
    ):
        return ctx.default_return_type

    

    import pdb; pdb.set_trace()


######################################################################
# plugin entry point

function_handler = {
    "contextlib.asynccontextmanager": args_invariant_decorator_callback,
    "async_generator.asynccontextmanager": args_invariant_decorator_callback,
    "trio_typing.takes_callable_and_args": takes_callable_and_args_callback,
    "async_generator.async_generator": async_generator_callback,
    "async_generator.yield_": yield_callback,
    "async_generator.yield_from_": yield_from_callback,
    "functools.partial": partial_init_callback,
    "__call__ of partial": partial_call_callback,
}

attribute_handler = {
    "functools.partial.args": partial_args_callback,
    "functools.partial.keywords": partial_keywords_callback,
    "functools.partial.func": partial_func_callback,
}

method_handler = {
    "trio_typing.TaskStatus.started": started_callback,
}


class TrioPlugin(Plugin):
    def get_function_hook(
        self, fullname: str
    ) -> Optional[Callable[[FunctionContext], Type]]:
        #if "partial" in fullname:
        #    print(fullname)
        return function_handler.get(fullname)

    def get_attribute_hook(
        self, fullname: str
    ) -> Optional[Callable[[AttributeContext], Type]]:
        if "partial" in fullname:
            print(fullname)
        return attribute_handler.get(fullname)

    def get_method_hook(
        self, fullname: str
    ) -> Optional[Callable[[MethodContext], Type]]:
        #if "partial" in fullname:
        #    print(fullname)
        return method_handler.get(fullname)


def plugin(version: str) -> typing_Type[Plugin]:
    return TrioPlugin
