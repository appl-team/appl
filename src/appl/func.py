import copy
import functools
import inspect
import sys
import threading
from inspect import signature
from typing import overload

from langsmith import traceable

from .core import (
    BaseTool,
    Compositor,
    Conversation,
    GenArgs,
    Generation,
    PrinterPop,
    PrinterPush,
    PromptContext,
    PromptFunc,
    PromptRecords,
    Tool,
)
from .core.globals import global_vars
from .core.trace import FunctionCallEvent, FunctionReturnEvent, add_to_trace
from .servers import server_manager
from .types import *

# https://docs.python.org/3/library/typing.html#typing.ParamSpec
# https://docs.python.org/3/library/typing.html#typing.Concatenate
# https://peps.python.org/pep-0612/
# Callable[P, T] is used for static type inference (Pylance)
P = ParamSpec("P")
T = TypeVar("T")
F = TypeVar("F", bound=Callable)


def need_ctx(func: Callable[P, T]) -> Callable[P, T]:
    """Decorate a function to mark it as needing a prompt context."""
    setattr(func, "__need_ctx__", True)
    return func


def partial(func: Callable, *args: Any, **kwargs: Any) -> Any:
    """Create a new function with partial application of the given arguments and keywords."""
    new_func = functools.partial(func, *args, **kwargs)
    if getattr(func, "__need_ctx__", True):
        new_func = need_ctx(new_func)  # type: ignore
    return new_func


def wraps(func: F) -> Callable[[F], F]:
    """Replace the functools.wraps to take care of the type hint."""

    def decorator(wrapper: F) -> F:
        return functools.wraps(func)(wrapper)  # type: ignore

    return decorator


def auto_prime_gen(gen_func):
    """Decorate a generator to automatically prime the generator."""

    def wrapper(*args, **kwargs):
        gen = gen_func(*args, **kwargs)
        next(gen)  # prime the generator
        return gen

    return wrapper


@overload
def ppl(ctx: F) -> F: ...


@overload
def ppl(
    ctx: str = "new",
    comp: Optional[Compositor] = None,
    *,
    default_return: Optional[Literal["prompt"]] = None,
    include_docstring: bool = False,
    auto_prime: bool = False,
    num_extra_wrappers: int = 0,
    new_ctx_func: Callable = PromptContext,
) -> Callable[[F], F]: ...


def ppl(
    ctx: Union[str, F] = "new",
    comp: Optional[Compositor] = None,
    *,
    default_return: Optional[Literal["prompt"]] = None,
    include_docstring: bool = False,
    auto_prime: bool = False,
    num_extra_wrappers: int = 0,
    new_ctx_func: Callable = PromptContext,
) -> Union[Callable[[F], F], F]:
    """Decorate a function to mark it as an APPL function.

    The function contains a prompt context, which could be same as or
    copied from its caller function, or created from scratch, or resumed
    from the last run.

    Args:
        ctx (str):
            the method to deal with the child context, available methods includes:

            - (default) "new" or "new_ctx": create a brand new context.
            - "copy" or "copy_ctx":
                copy from the parent's context, the change will not
                affect the parent's context.
            - "same" or "same_ctx":
                use the same context as the parent's, the change will
                affect the parent's context.
            - "resume" or "resume_ctx":
                resume its own context from the last run.
                For the first run, it will use the parent's context.

        comp (Compositor, optional):
            the default compositor to be used. Defaults to None.
        default_return (str, optional):
            The default return value, "prompt" means return the prompt within
            the function. Defaults to None.
        include_docstring (bool, optional):
            set to True to include the triple-quoted docstring in the prompt.
            Defaults to False.
        auto_prime (bool, optional):
            set to True to automatically prime the generator. Defaults to False.
        num_extra_wrappers (int, optional):
            the number of extra wrappers to go back to the caller frame.
        new_ctx_func (Callable, optional):
            the function to create a new context. Defaults to PromptContext.
    """
    # The same doc string as PromptFunc (excluding the func argument)

    ctx_method: str = "new"

    def decorator(func: F) -> F:
        """Decorate a function as prompt function."""
        _is_class_method = False
        if "." in (qualname := func.__qualname__):
            # NOTE: this is a workaround for class methods, may not cover all cases
            qualnames = qualname.split(".")
            if qualnames[-2] != "<locals>":
                _is_class_method = True

        # ? should disable such usage?
        # if not _is_class_method and "<locals>" in qualname and ctx_method == "resume":
        #     raise ValueError("Cannot use 'resume' with local functions.")
        prompt_func = PromptFunc(
            func, ctx_method, comp, default_return, include_docstring, new_ctx_func
        )

        @need_ctx
        @traceable(name=func.__name__, metadata={"appl": "func"})
        @functools.wraps(func)
        def wrapper(
            *args: Any,
            _globals: Optional[Dict] = None,
            _locals: Optional[Dict] = None,
            **kwargs: Any,
        ) -> Any:
            # add to trace (function call)
            func_name = f"{prompt_func._name}_{prompt_func._run_cnt}"
            prompt_func._run_cnt += 1
            add_to_trace(
                FunctionCallEvent(
                    name=func_name,
                    args={"args": repr(args), "kwargs": repr(kwargs)},
                )
            )
            # closure variables
            freevars = prompt_func.compiled_func.freevars
            if _locals is None:
                # * Workaround for closure variables
                # Default: use the locals from the caller
                frame = inspect.currentframe()
                num_wrappers = (3 if auto_prime else 2) + num_extra_wrappers
                for _ in range(num_wrappers):
                    if frame is None:
                        raise RuntimeError("No caller frame found")
                    # back to @traceable frame, and the caller frame
                    frame = frame.f_back
                if frame is None:
                    raise RuntimeError("No caller frame found")
                _locals = frame.f_locals

                if len(freevars):
                    vars = {var: _locals.get(var, "NotFound") for var in freevars}
                    logger.debug(
                        f"For freevars of function {func.__name__}, "
                        f"automatically using locals from the caller: {vars}"
                    )
                    for var in freevars:
                        if var not in _locals:
                            logger.warning(
                                f"could not find variable {var} automatically from the caller frame."
                            )
            results = prompt_func(
                *args,
                _globals=_globals,
                _locals=_locals,
                _is_class_method=_is_class_method,
                **kwargs,
            )
            # add to trace (function return)
            add_to_trace(FunctionReturnEvent(name=func_name))  # ret=results
            return results

        if auto_prime:
            wrapper = auto_prime_gen(wrapper)
        setattr(wrapper, "_prompt_func", prompt_func)
        return wrapper  # type: ignore

    if isinstance(ctx, str):
        ctx_method = ctx
        # used as a decorator with arguments (e.g., @ppl(ctx="copy"))
        # returns a decorator that takes a function as input
        return decorator
    else:
        # used as a single decorator (i.e., @ppl)
        return decorator(func=ctx)  # returns a wrapper


def reset_context(func: Callable) -> None:
    """Reset the context for APPL functions with the 'resume' context method."""
    if prompt_func := getattr(func, "_prompt_func", None):
        if reset_func := getattr(prompt_func, "_reset_context_func", None):
            reset_func()
            logger.info(f"Context reset for function {func.__name__}")
        else:
            logger.warning(f"Nothing to reset for function {func.__name__}")
    else:
        logger.warning(f"Not an APPL function: {func.__name__}, cannot reset context.")


def as_func(
    func: Callable[P, T],
    _globals: Optional[Dict] = None,
    _locals: Optional[Dict] = None,
) -> Callable[P, T]:
    """Fill the globals and locals for a ppl function.

    When locals not provided, it will use the locals from the caller.
    """
    frame = inspect.currentframe()
    if _locals is None and frame is not None and frame.f_back is not None:
        _locals = frame.f_back.f_locals
    return partial(func, _globals=_globals, _locals=_locals)


def str_future(obj: Any) -> StringFuture:
    """Convert an object to a StringFuture object."""
    return StringFuture(obj)


def as_tool(func: Callable, **kwargs: Any) -> Tool:
    """Wrap a given function with additional predefined arguments into a Tool.

    This function allows converting a standard function into a 'Tool' by
    specifying the function and any additional arguments that should be
    pre-defined for it. These additional arguments are passed as keyword
    arguments and will be bound to the function within the Tool object,
    so that these arguments are not required when using this tool.

    Args:
        func (Callable):
            The function to be converted into a Tool.
        **kwargs:
            Keyword arguments that will be predefined for the function in
            the Tool object.

    Returns:
        Tool:
            An object encapsulating the given function and its predefined
            arguments, ready to be utilized as a Tool.

    Examples:
        Given a function `move_disk` that requires an environment and two
        pegs to move a disk from one peg to another in the Tower of Hanoi
        puzzle, one can create a tool with a predefined environment by:

        ```python
        def move_disk(env: HanoiEnv, from_peg: int, to_peg: int) -> str:
            pass

        env = HanoiEnv()
        tools = [as_tool(move_disk, env=env)]
        ```

        In this example, `move_disk` is encapsulated into a Tool with `env`
        predefined, so only `from_peg` and `to_peg` are required.
    """
    return Tool(func=func, **kwargs)


def as_tool_choice(obj: Union[str, Callable, BaseTool]) -> dict:
    """Build a tool choice argument for the OpenAI API from an object."""
    if isinstance(obj, BaseTool):
        name = obj.name
    else:
        name = getattr(obj, "__name__", str(obj))
    return dict(type="function", function=dict(name=name))


def call(
    func: Callable, *args: Any, use_process: bool = False, **kwargs: Any
) -> CallFuture:
    """Create a CallFuture object from a function and its arguments.

    The CallFuture object will call the function in a separate thread or process,
    therefore the function need to be thread-safe or process-safe.
    """
    return CallFuture(func, *args, use_process=use_process, **kwargs)


def openai_tool_schema(func: Callable) -> dict:
    """Build openai tool schema from a function."""
    return as_tool(func).openai_schema


@need_ctx
def get_var(name: str, _ctx: PromptContext) -> Any:
    """Get a variable by name from the prompt context."""
    return getattr(_ctx, name)


@need_ctx
def records(_ctx: Optional[PromptContext] = None) -> PromptRecords:
    """Return the prompt defined in the current function.

    Similar to locals() in Python in some sense.
    """
    # add default value for _ctx to avoid the warning of type checker
    if _ctx is None:
        raise ValueError(
            "PromptContext is required for records, "
            "this function should be called within @ppl function."
        )
    return _ctx.records


@need_ctx
def convo(_ctx: Optional[PromptContext] = None) -> Conversation:
    """Return the full conversation in the context.

    Similar to globals() in Python in some sense.
    """
    # Added default value for _ctx to avoid the warning of type checker
    if _ctx is None:
        raise ValueError(
            "PromptContext is required for convo, "
            "this function should be called within @ppl function."
        )
    return _ctx.messages


def empty_line(num_lines: int = 1) -> PromptRecords:
    """Create empty lines regardless of other compositor."""
    records = PromptRecords()
    records.record(PrinterPush(separator="\n", indexing=Indexing(), new_indent=""))
    for _ in range(num_lines):
        records.record("")
    records.record(PrinterPop())
    return records


def build_tools(tools: OneOrMany[Union[BaseTool, Callable]]) -> Sequence[BaseTool]:
    """Build a list of tools from the given tools or functions."""

    def convert_to_tool(tool: Union[BaseTool, Callable]) -> BaseTool:
        if isinstance(tool, BaseTool):
            return tool
        if callable(tool):
            return as_tool(tool)
        raise ValueError(f"Invalid tool: {tool}")

    # process tools
    if isinstance(tools, BaseTool) or callable(tools):
        return [convert_to_tool(tools)]
    if isinstance(tools, Sequence):
        return [convert_to_tool(tool) for tool in tools]
    raise ValueError(f"Invalid tools: {tools}")


@need_ctx
def gen(
    server: Optional[str] = None,
    *,
    max_tokens: Optional[int] = None,
    stop: MaybeOneOrMany[str] = None,
    temperature: Optional[float] = None,
    top_p: Optional[float] = None,
    n: Optional[int] = None,
    tools: OneOrMany[Union[BaseTool, Callable]] = [],
    tool_format: str = "auto",
    stream: Optional[bool] = None,
    mock_response: Optional[Union[CompletionResponse, str]] = None,
    _ctx: Optional[PromptContext] = None,
    **kwargs: Any,
) -> Generation:
    """Send a generation request to the LLM backend.

    Args:
        server (str, optional):
            name of the backend server. Defaults to the default server set in the configs.
        max_tokens (int, optional): maximum number of tokens to generate. Defaults to None.
        stop (str|Sequence[str], optional): stop sequence(s). Defaults to None.
        temperature (float, optional): temperature for sampling. Defaults to None.
        top_p (float, optional): nucleus sampling parameter. Defaults to None.
        n (int, optional): number of choices to generate. Defaults to 1.
        tools (BaseTool|Callable|Sequence[BaseTool|Callable], optional): tools can be used. Defaults to None.
        tool_format (str, optional): format for the tools. Defaults to "auto".
        stream (bool, optional): whether to stream the results. Defaults to False.
        mock_response (Union[CompletionResponse, str], optional): mock response for testing. Defaults to None.
        _ctx (PromptContext): prompt context, will be automatically filled.
        kwargs (Any): extra arguments for the generation.

    Returns:
        Generation: a future object representing the generation result
    """
    backend_server = server_manager.get_server(server)
    if _ctx is None:
        raise ValueError(
            "PromptContext is required for generation."
            "Normally, it should be automatically filled."
        )
    messages = _ctx.messages
    messages.materialize()  # materialize the messages
    # TODO: double check the correctness
    messages = copy.deepcopy(messages)  # freeze the prompt for the generation

    create_args = GenArgs(
        model=backend_server.model_name,
        messages=messages,
        max_tokens=max_tokens,
        stop=stop,
        temperature=temperature,
        top_p=top_p,
        n=n,
        tools=build_tools(tools),
        tool_format=tool_format,  # type: ignore
        stream=stream,
    )

    generation = Generation(
        backend_server, create_args, mock_response=mock_response, _ctx=_ctx, **kwargs
    )

    @traceable(name=generation.id, metadata={"appl": "gen"})
    def langsmith_trace(*args: Any, **kwargs: Any) -> None:
        pass

    langsmith_trace(backend_server, create_args, _ctx=_ctx, **kwargs)
    return generation


# def serialize(obj: Any) -> Any:
#     if hasattr(obj, "serialize"):
#         return obj.serialize()
#     else:
#         raise TypeError("Object of type '%s' is not serializable" % type(obj).__name__)
